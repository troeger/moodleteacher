'''
Implementation of validation jobs.

Check the documentation for more details.
'''

import os.path
import os
import sys
import importlib
import re
import shutil

from .exceptions import *
from .compiler import GCC, compiler_cmdline
from .runnable import RunningProgram

import logging
logger = logging.getLogger('moodleteacher')

VALIDATOR_IMPORT_NAME = 'validator'


class ValidationJob():
    '''
    A validation job represent the act of validating a single student submission.
    It relies on a script written by the tutor that contains a method *validate(job)*.
    The method can use the functions of this class to check what the student did.
    '''
    result_sent = False
    submission_file = None               # The original student upload (MoodleSubmissionFile)
    submission_content = None            # The unarchived list of files of the student submission
    validator_file = None                # The original validator (MoodleFile)
    working_dir = None                   # The temporary working directory with all the content

    def __init__(self, submission_file, validator_file):
        '''
        Attributes:
            submission_file (MoodleSubmissionFile):   The student submission.
            validator_file (MoodleFile):              The validator written by the student.
        '''
        self.submission_file = submission_file
        self.validator_file = validator_file

        # Create working directory
        self.working_dir = tempfile.mkdtemp(prefix='moodleteacher_')
        if not self.working_dir.endswith(os.sep):
            self.working_dir += os.sep
        logger.debug("Created fresh working directory at {0}.".format(self.working_dir))
        self.student_files = self.submission_file.unpack(self.working_dir)

    def __str__(self):
        return str(vars(self))

    @property
    # The file name of the validation / full test script
    # on disk, after unpacking / renaming.
    def validator_script_name(self):
        return self.working_dir + VALIDATOR_IMPORT_NAME + '.py'

    def _run_validate(self):
        '''
        Execute the validate() method in the validator belonging to this job.
        '''
        assert(os.path.exists(self.validator_script_name))
        old_path = sys.path
        sys.path = [self.working_dir] + old_path

        try:
            module = importlib.import_module(VALIDATOR_IMPORT_NAME)
        except Exception as e:
            logger.error("Exception while loading the validator: " + str(e))
            return

        # Demanded by looped validator loading in the test suite
        importlib.reload(module)

        # make the call
        try:
            module.validate(self)
        except Exception as e:
            # get more info
            text_student = None
            text_tutor = None
            if type(e) is TerminationException:
                text_student = "The execution of '{0}' terminated unexpectely.".format(
                    e.instance.name)
                text_tutor = "The execution of '{0}' terminated unexpectely.".format(
                    e.instance.name)
                text_student += "\n\nOutput so far:\n" + e.output
                text_tutor += "\n\nOutput so far:\n" + e.output
            elif type(e) is TimeoutException:
                text_student = "The execution of '{0}' was cancelled, since it took too long.".format(
                    e.instance.name)
                text_tutor = "The execution of '{0}' was cancelled due to timeout.".format(
                    e.instance.name)
                text_student += "\n\nOutput so far:\n" + e.output
                text_tutor += "\n\nOutput so far:\n" + e.output
            elif type(e) is NestedException:
                text_student = "Unexpected problem during the execution of '{0}'. {1}".format(
                    e.instance.name,
                    str(e.real_exception))
                text_tutor = "Unkown exception during the execution of '{0}'. {1}".format(
                    e.instance.name,
                    str(e.real_exception))
                text_student += "\n\nOutput so far:\n" + e.output
                text_tutor += "\n\nOutput so far:\n" + e.output
            elif type(e) is WrongExitStatusException:
                text_student = "The execution of '{0}' resulted in the unexpected exit status {1}.".format(
                    e.instance.name,
                    e.got)
                text_tutor = "The execution of '{0}' resulted in the unexpected exit status {1}.".format(
                    e.instance.name,
                    e.got)
                text_student += "\n\nOutput so far:\n" + e.output
                text_tutor += "\n\nOutput so far:\n" + e.output
            elif type(e) is JobException:
                # Some problem with our own code
                text_student = e.info_student
                text_tutor = e.info_tutor
            elif type(e) is FileNotFoundError:
                text_student = "A file is missing: {0}".format(
                    str(e))
                text_tutor = "Missing file: {0}".format(
                    str(e))
            elif type(e) is AssertionError:
                # Need this harsh approach to kill the
                # test suite execution at this point
                # Otherwise, the problem gets lost in
                # the log storm
                logger.error(
                    "Failed assertion in validation script. Should not happen in production.")
                exit(-1)
            else:
                # Something really unexpected
                text_student = "Internal problem while validating your submission. Please contact the course responsible."
                text_tutor = "Unknown exception while running the validator: {0}".format(
                    str(e))
            # We got the text. Report the problem.
            self._send_result(text_student)
            logger.error(text_tutor)
            return
        # no unhandled exception during the execution of the validator
        if not self.result_sent:
            logger.debug(
                "Validation script forgot result sending, assuming success.")
            self.send_pass_result()
        # roll back
        sys.path = old_path
        # Test script was executed, result was somehow sent
        # Clean the file system, since we can't do anything else
        shutil.rmtree(self.working_dir, ignore_errors=True)

    def _send_result(self, info_student):
        # TODO: Send as Moodle comment
        logger.info(
            'Sending result to Moodle: ' + str(post_data))
        self.result_sent = True

    def send_fail_result(self, info_student, info_tutor="Test failed."):
        """Reports a negative result for this validation job.

        Args:
            info_student (str): Information for the student(s)
            info_tutor   (str): Information for the tutor(s)

        """
        logger.info(info_tutor)
        self._send_result(info_student)

    def send_pass_result(self,
                         info_student="All tests passed. Awesome!",
                         info_tutor="All tests passed."):
        """Reports a positive result for this validation job.

        Args:
            info_student (str): Information for the student(s)
            info_tutor   (str): Information for the tutor(s)

        """
        logger.info(info_tutor)
        self._send_result(info_student)

    def run_configure(self, mandatory=True, timeout=30):
        """Runs the 'configure' program in the working directory.

        Args:
            mandatory (bool): Throw exception if 'configure' fails or a
                              'configure' file is missing.

        """
        if not os.path.exists(self.working_dir + os.sep + 'configure'):
            if mandatory:
                raise FileNotFoundError(
                    "Could not find a configure script for execution.")
            else:
                return
        try:
            prog = RunningProgram(self, 'configure', [], self.working_dir, timeout)
            prog.expect_exitstatus(0)
        except Exception:
            if mandatory:
                raise

    def run_make(self, mandatory=True, timeout=30):
        """Runs the 'make' program in the working directory.

        Args:
            mandatory (bool): Throw exception if 'make' fails or a
                              'Makefile' file is missing.

        """
        if not os.path.exists(self.working_dir + os.sep + 'Makefile'):
            if mandatory:
                raise FileNotFoundError("Could not find a Makefile.")
            else:
                return
        try:
            prog = RunningProgram(self, 'make', [], self.working_dir, timeout)
            prog.expect_exitstatus(0)
        except Exception:
            if mandatory:
                raise

    def run_compiler(self, compiler=GCC, inputs=None, output=None, timeout=30):
        """Runs a compiler in the working directory.

        Args:
            compiler (tuple): The compiler program and its command-line arguments,
                              including placeholders for output and input files.
            inputs (tuple):   The list of input files for the compiler.
            output (str):     The name of the output file.

        """
        # Let exceptions travel through
        compiler_cmd, compiler_args = compiler_cmdline(compiler=compiler,
                                                       inputs=inputs,
                                                       output=output)

        prog = RunningProgram(self, compiler_cmd, compiler_args, self.working_dir, timeout)
        prog.expect_exitstatus(0)

    def run_build(self, compiler=GCC, inputs=None, output=None, timeout=30):
        """Combined call of 'configure', 'make' and the compiler.

        The success of 'configure' and 'make' is optional.
        The arguments are the same as for run_compiler.

        """
        logger.info("Running build steps ...")
        self.run_configure(mandatory=False, timeout)
        self.run_make(mandatory=False, timeout)
        self.run_compiler(compiler, inputs, output, timeout)

    def spawn_program(self, name, arguments=[], timeout=30):
        """Spawns a program in the working directory.

        This method allows the interaction with the running program,
        based on the returned RunningProgram object.

        Args:
            name (str):        The name of the program to be executed.
            arguments (tuple): Command-line arguments for the program.
            timeout (int):     The timeout for execution.

        Returns:
            RunningProgram: An object representing the running program.

        """
        logger.debug("Spawning program for interaction ...")
        return RunningProgram(self, name, arguments, timeout)

    def run_program(self, name, arguments=[], timeout=30):
        """Runs a program in the working directory to completion.

        Args:
            name (str):        The name of the program to be executed.
            arguments (tuple): Command-line arguments for the program.
            timeout (int):     The timeout for execution.

        Returns:
            tuple: A tuple of the exit code, as reported by the operating system,
            and the output produced during the execution.
        """
        logger.debug("Running program ...")
        if exclusive:
            kill_longrunning(self.config)

        prog = RunningProgram(self, name, arguments, self.working_dir, timeout)
        return prog.expect_end()

    def grep(self, regex):
        """Scans the student files for text patterns.

        Args:
            regex (str):       Regular expression used for scanning inside the files.

        Returns:
            tuple:     Names of the matching files in the working directory.
        """
        matches = []
        logger.debug("Searching student files for '{0}'".format(regex))
        for fname in self.student_files:
            if os.path.isfile(self.working_dir + fname):
                for line in open(self.working_dir + fname, 'br'):
                    if re.search(regex.encode(), line):
                        logger.debug("{0} contains '{1}'".format(fname, regex))
                        matches.append(fname)
        return matches

    def ensure_files(self, filenames):
        """Checks the student submission for specific files.

        Args:
            filenames (tuple): The list of file names to be checked for.

        Returns:
            bool: Indicator if all files are found in the student archive.
        """
        logger.debug("Testing {0} for the following files: {1}".format(
            self.working_dir, filenames))
        dircontent = os.listdir(self.working_dir)
        for fname in filenames:
            if fname not in dircontent:
                return False
        return True
