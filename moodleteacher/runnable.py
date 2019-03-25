import pexpect
import os
import tempfile

from .exceptions import *

import logging
logger = logging.getLogger('moodleteacher')


class RunningProgram():
    """A running program that you can interact with.

    This class is a thin wrapper around the functionality
    of pexpect (http://pexpect.readthedocs.io/en/stable/overview.html).

    Attributes:
        name (str):           The name of the binary that is executed.
        working_dir (str):    The working directory to be used during execution.
        arguments (tuple):    The command-line arguments being used for execution.
    """
    name = None
    arguments = None
    working_dir = None
    _logfile = None
    _spawn = None

    def get_output(self):
        """Get the program output produced so far.

        Returns:
            str: Program output as text. May be incomplete.
        """
        # Open temporary file for reading, in text mode
        # This makes sure that the file pointer for writing
        # is not touched
        with open(self._logfile.name) as logfile:
            return '<pre>' + ''.join(logfile.readlines()) + '</pre>'

    def get_exitstatus(self):
        """Get the exit status of the program execution.

        Returns:
            int: Exit status as reported by the operating system,
                 or None if it is not available.
        """
        logger.debug("Exit status is {0}".format(self._spawn.exitstatus))
        return self._spawn.exitstatus

    def __init__(self, name, arguments=[], working_dir='.', timeout=30, encoding=None):
        """Initialize a running program.

        Args:
            name:  The file path for the executable.
            arguments:  The command-line arguments for the executable.
            working_dir:  The current working directory when running the program.
            timeout:  The timeout for program execution.
            encoding: The text encoding for the program output, e.g. 'utf-8'. If this parameter
                    is not set, then the output is interpreted as bytes.
        """
        self.name = name
        self.arguments = arguments
        self.working_dir = working_dir
        self.encoding = encoding

        # Allow code to load its own libraries
        os.environ["LD_LIBRARY_PATH"] = working_dir

        logger.debug("Spawning '{0}' in {1} with the following arguments:{2}".format(
            name,
            working_dir,
            str(arguments)))

        if name.startswith('./'):
            name = name.replace('./', working_dir)

        self._logfile = tempfile.NamedTemporaryFile(encoding=encoding, mode='w+' if encoding else 'w+b')
        logger.debug("Keeping console I/O in " + self._logfile.name)
        try:
            self._spawn = pexpect.spawn(name, arguments,
                                        logfile=self._logfile,
                                        timeout=timeout,
                                        cwd=working_dir,
                                        echo=False,
                                        encoding=encoding)
        except Exception as e:
            logger.debug("Spawning failed: " + str(e))
            raise NestedException(instance=self, real_exception=e, output=self.get_output())

    def expect(self, pattern, timeout=-1, searchwindowsize=-1, async_=False, **kw):
        return self._spawn.expect(pattern, timeout, searchwindowsize, async_, **kw)

    def expect_output(self, pattern, timeout=-1):
        """Wait until the running program performs some given output, or terminates.

        Args:
            pattern:  The pattern the output should be checked for.
            timeout (int):  How many seconds should be waited for the output.

        The pattern argument may be a string, a compiled regular expression,
        or a list of any of those types. Strings will be compiled into regular expressions.

        Returns:
            int: The index into the pattern list. If the pattern was not a list, it returns 0 on a successful match.

        Raises:
            TimeoutException: The output did not match within the given time frame.
            TerminationException: The program terminated before producing the output.
            NestedException: An internal problem occured while waiting for the output.
        """
        logger.debug("Expecting output '{0}' from '{1}'".format(pattern, self.name))
        try:
            return self._spawn.expect(pattern, timeout)
        except pexpect.exceptions.EOF as e:
            logger.debug("Raising termination exception.")
            raise TerminationException(instance=self, real_exception=e, output=self.get_output())
        except pexpect.exceptions.TIMEOUT as e:
            logger.debug("Raising timeout exception.")
            raise TimeoutException(instance=self, real_exception=e, output=self.get_output())
        except Exception as e:
            logger.exception("Expecting output failed: ")
            raise NestedException(instance=self, real_exception=e, output=self.get_output())

    def sendline(self, text):
        """Sends an input line to the running program, including os.linesep.

        Args:
            text (str): The input text to be send.

        Raises:
            TerminationException: The program terminated before / while / after sending the input.
            NestedException: An internal problem occured while waiting for the output.
        """
        logger.debug("Sending input '{0}' to '{1}'".format(text, self.name))
        try:
            return self._spawn.sendline(text)
        except pexpect.exceptions.EOF as e:
            logger.debug("Raising termination exception.")
            raise TerminationException(instance=self, real_exception=e, output=self.get_output())
        except pexpect.exceptions.TIMEOUT as e:
            logger.debug("Raising timeout exception.")
            raise TimeoutException(instance=self, real_exception=e, output=self.get_output())
        except Exception as e:
            logger.debug("Sending input failed: " + str(e))
            raise NestedException(instance=self, real_exception=e, output=self.get_output())

    def expect_end(self):
        """Wait for the running program to finish.

        Returns:
            A tuple with the exit code, as reported by the operating system, and the output produced.
        """
        logger.debug("Waiting for termination of '{0}'".format(self.name))
        try:
            # Make sure we fetch the last output bytes.
            # Recommendation from the pexpect docs.
            self._spawn.expect(pexpect.EOF)
            self._spawn.wait()
            dircontent = str(os.listdir(self.working_dir))
            logger.debug("Working directory after execution: " + dircontent)
            return self.get_exitstatus(), self.get_output()
        except pexpect.exceptions.EOF as e:
            logger.debug("Raising termination exception.")
            raise TerminationException(instance=self, real_exception=e, output=self.get_output())
        except pexpect.exceptions.TIMEOUT as e:
            logger.debug("Raising timeout exception.")
            raise TimeoutException(instance=self, real_exception=e, output=self.get_output())
        except Exception as e:
            logger.debug("Waiting for expected program end failed.")
            raise NestedException(instance=self, real_exception=e, output=self.get_output())

    def expect_exitstatus(self, exit_status):
        """Wait for the running program to finish and expect some exit status.

        Args:
            exit_status (int):  The expected exit status.

        Raises:
            WrongExitStatusException: The produced exit status is not the expected one.
        """
        self.expect_end()
        logger.debug("Checking exit status of '{0}', output so far: {1}".format(
            self.name, self.get_output()))
        if self._spawn.exitstatus is None:
            raise WrongExitStatusException(
                instance=self, expected=exit_status, output=self.get_output())

        if self._spawn.exitstatus is not exit_status:
            raise WrongExitStatusException(
                instance=self,
                expected=exit_status,
                got=self._spawn.exitstatus,
                output=self.get_output())
