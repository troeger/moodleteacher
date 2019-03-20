'''
Implementation of validation jobs.
'''

import os.path
import os
import sys
import importlib
import re
import shutil
import tempfile
import logging

from .exceptions import *
from .compiler import GCC, compiler_cmdline
from .runnable import RunningProgram

logger = logging.getLogger('moodleteacher')


VALIDATOR_IMPORT_NAME = 'validator'


class ValidationJob():
    '''
    A validation job checks a single student submission, based on a validator script written by the tutor.

    Check the validation section in the moodleteacher documentation for more details.
    '''
    result_sent = False
    working_dir = None                   # The temporary working directory with all the content
    get_files_called = False
    prepared_student_files = False

    def __init__(self, submission, validator_file):
        '''
        Prepares a validation job by putting all relevant files into a temporary
        directory.

        Attributes:
            submission (MoodleSubmission):            The student submission object.
            validator_file (MoodleFile):              The validator file object.
        '''
        self.submission = submission
        self.validator_file = validator_file

    def __str__(self):
        return str(vars(self))

    @property
    # The file name of the validation / full test script
    # on disk, after unpacking / renaming.
    def validator_script_name(self):
        return self.working_dir + VALIDATOR_IMPORT_NAME + '.py'

    def start(self, log_level=logging.INFO):
        '''
        Execute the validate() method in the validator script belonging to this job.
        '''
        logger.setLevel(log_level)

        # Create temporary directory for validation
        self.working_dir = tempfile.mkdtemp(prefix='moodleteacher_')
        if not self.working_dir.endswith(os.sep):
            self.working_dir += os.sep
        logger.debug("Created fresh working directory at {0}.".format(self.working_dir))

        # Store validator file in temporary directory
        if self.validator_file.is_archive:
            # We assume that a validator file with the correct name
            # exists inside the archive
            logger.debug("Validator is an archive, assuming {0}.py to be inside.".format(VALIDATOR_IMPORT_NAME))
            self.validator_file.unpack_to(self.working_dir, remove_directories=False)
        else:
            # The file is the validator, so we can rename it to match
            logger.debug("Moving validator content to {0}.".format(self.validator_script_name))
            self.validator_file.save_as(self.working_dir, VALIDATOR_IMPORT_NAME + '.py')

        # Load validator to be called
        if not os.path.exists(self.validator_script_name):
            logger.error("Missing validator file at {0}.".format(self.validator_script_name))
            return
        old_path = sys.path
        sys.path = [self.working_dir] + old_path

        try:
            logger.debug("Loading validator.")
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
            if type(e) is TerminationException:
                text_student = "The execution of '{0}' terminated unexpectely.".format(
                    e.instance.name)
                text_student += "\n\nOutput so far:\n" + e.output
            elif type(e) is TimeoutException:
                text_student = "The execution of '{0}' was cancelled, since it took too long.".format(
                    e.instance.name)
                text_student += "\n\nOutput so far:\n" + e.output
            elif type(e) is NoFilesException:
                text_student = "Your submission contains no files."
            elif type(e) is NestedException:
                text_student = "Unexpected problem during the execution of '{0}'. {1}".format(
                    e.instance.name,
                    str(e.real_exception))
                text_student += "\n\nOutput so far:\n" + e.output
            elif type(e) is WrongExitStatusException:
                text_student = "The execution of '{0}' resulted in the unexpected exit status {1}.".format(
                    e.instance.name,
                    e.got)
                text_student += "\n\nOutput so far:\n" + e.output
            elif type(e) is JobException:
                # Some problem with our own code
                text_student = e.info_student
            elif type(e) is FileNotFoundError:
                text_student = "A file is missing: {0}".format(
                    str(e))
            elif type(e) is AssertionError:
                # This is a library bug, crash for stack trace
                raise(e)
            else:
                # Something really unexpected, crash for stack trace
                raise(e)
            # We got the text. Report the problem.
            logger.info("A problem occured, message sent to the student: '{0}'".format(text_student))
            self._send_result(text_student)
            # roll back
            sys.path = old_path
            # keep temporary directory for debugging
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
        logger.info('Sending result to Moodle ...')
        self.submission.save_feedback(info_student)
        self.result_sent = True

    def prepare_student_files(self, remove_directories=True):
        """Unarchive student files in temporary directory.
        """
        if not self.submission.files:
            logger.warn("prepare_student_files() not successful, submission has no files.")
            raise NoFilesException()

        assert(self.working_dir)
        for f in self.submission.files:
            f.unpack_to(self.working_dir, remove_directories)
        self.prepared_student_files = True

    def send_fail_result(self, info_student, info_tutor="Test failed."):
        """Reports a negative result for this validation job.

        Args:
            info_student (str): Information for the student(s)
            info_tutor   (str): Information for the tutor(s)

        """
        logger.info("Fail result sent for the tutor: '{0}'".format(info_tutor))
        logger.info("Fail result sent for the student: '{0}'".format(info_student))
        self._send_result(info_student)

    def send_pass_result(self,
                         info_student="All tests passed. Awesome!",
                         info_tutor="All tests passed."):
        """Reports a positive result for this validation job.

        Args:
            info_student (str): Information for the student(s)
            info_tutor   (str): Information for the tutor(s)

        """
        logger.info("Pass result sent for the tutor: '{0}'".format(info_tutor))
        logger.info("Pass result sent for the student: '{0}'".format(info_student))
        self._send_result(info_student)

    def run_configure(self, mandatory=True, timeout=30):
        """Runs the 'configure' program in the working directory.

        Args:
            mandatory (bool): Throw exception if 'configure' fails or a
                              'configure' file is missing.

        """
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        if not os.path.exists(self.working_dir + os.sep + 'configure'):
            if mandatory:
                raise FileNotFoundError(
                    "Could not find a configure script for execution.")
            else:
                return
        try:
            prog = RunningProgram('configure', [], self.working_dir, timeout)
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
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        if not os.path.exists(self.working_dir + os.sep + 'Makefile'):
            if mandatory:
                raise FileNotFoundError("Could not find a Makefile.")
            else:
                return
        try:
            prog = RunningProgram('make', [], self.working_dir, timeout)
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
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        # Let exceptions travel through
        compiler_cmd, compiler_args = compiler_cmdline(compiler=compiler,
                                                       inputs=inputs,
                                                       output=output)

        prog = RunningProgram(compiler_cmd, compiler_args, self.working_dir, timeout)
        prog.expect_exitstatus(0)

    def run_build(self, compiler=GCC, inputs=None, output=None, timeout=30):
        """Combined call of 'configure', 'make' and the compiler.

        The success of 'configure' and 'make' is optional.
        The arguments are the same as for run_compiler.

        """
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        logger.info("Running build steps ...")
        self.run_configure(mandatory=False, timeout=timeout)
        self.run_make(mandatory=False, timeout=timeout)
        self.run_compiler(compiler, inputs, output, timeout=timeout)

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
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        logger.debug("Spawning program for interaction ...")
        return RunningProgram(name, arguments, self.working_dir, timeout)

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
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        logger.debug("Running program ...")

        prog = RunningProgram(name, arguments, self.working_dir, timeout)
        return prog.expect_end()

    def grep(self, regex):
        """Scans the student files for text patterns.

        Args:
            regex (str):       Regular expression used for scanning inside the files.

        Returns:
            tuple:     Names of the matching files in the working directory.
        """
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        matches = []
        logger.debug("Searching student files for '{0}'".format(regex))
        for student_file in self.submission.files:
            fspath = self.working_dir + student_file.name
            if os.path.isfile(fspath):
                for line in open(fspath, 'br'):
                    if re.search(regex.encode(), line):
                        logger.debug("{0} contains '{1}'".format(fspath, regex))
                        matches.append(student_file.relative_path + student_file.name)
        return matches

    def ensure_files(self, filenames):
        """Checks the student submission for specific files.

        Args:
            filenames (tuple): The list of file names to be checked for.

        Returns:
            bool: Indicator if all files are found in the student archive.
        """
        if not self.prepared_student_files:
            raise ValidatorBrokenException("prepare_student_files() was not called before.")

        logger.debug("Testing {0} for the following files: {1}".format(
            self.working_dir, filenames))
        dircontent = os.listdir(self.working_dir)
        for fname in filenames:
            if fname not in dircontent:
                return False
        return True
