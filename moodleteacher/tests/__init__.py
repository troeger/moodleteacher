import unittest
import os
import os.path
import sys
import logging

from moodleteacher.connection import MoodleConnection
from moodleteacher.assignments import MoodleAssignments
from moodleteacher.submissions import MoodleSubmissions, MoodleSubmission
from moodleteacher.courses import MoodleCourse
from moodleteacher.jobs import ValidationJob
from moodleteacher.files import MoodleFile

# Note: We assume that Moodleteacher was started in interactive mode
#       before, so that credentials and URL are cached, and that we can
#       use the resources defined below for testing with the cached account.

TEST_COURSE_ID = 5787
TEST_FOLDER_ID = 432300       # should contain at least one file
TEST_ASSIGNMENT_ID = 14206    # should contain at least one submission


logger = logging.getLogger('moodleteacher')
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class Validation(unittest.TestCase):

    def _test_validation_case(self, directory, student_file):
        '''
        Each of the validator.py files in tests/submfiles/validation
        uses the Python assert() statement to check by itself if the result
        is the expected one for its case.
        '''
        base_dir = os.path.dirname(__file__) + '/submfiles/validation/'
        case_dir = base_dir + directory
        try:
            validator = MoodleFile.from_local_file(case_dir + os.sep + 'validator.py')
        except FileNotFoundError:
            validator = MoodleFile.from_local_file(case_dir + os.sep + 'validator.zip')

        job = ValidationJob(MoodleSubmission.from_local_file(case_dir + os.sep + student_file),
                            validator)
        job._run_validate()

    def test_0100fff(self):
        self._test_validation_case('0100fff', 'python.pdf')

    def test_0100tff(self):
        self._test_validation_case('0100tff', 'packed.zip')

    def test_0100ttf(self):
        self._test_validation_case('0100ttf', 'package.zip')

    def test_1000fff(self):
        self._test_validation_case('1000fff', 'helloworld.c')

    def test_1000fft(self):
        self._test_validation_case('1000fft', 'helloworld.c')

    def test_1000tff(self):
        self._test_validation_case('1000tff', 'packed.zip')

    def test_1000tft(self):
        self._test_validation_case('1000tft', 'packed.zip')

    def test_1000ttf(self):
        self._test_validation_case('1000ttf', 'packed.zip')

    def test_1000ttt(self):
        self._test_validation_case('1000ttt', 'packed.tgz')

    def test_1010tff(self):
        self._test_validation_case('1010tff', 'packed.zip')

    def test_1010ttf(self):
        self._test_validation_case('1010ttf', 'packed.zip')

    def test_1100tff(self):
        self._test_validation_case('1100tff', 'packed.zip')

    def test_1100ttf(self):
        self._test_validation_case('1100ttf', 'packed.zip')

    def test_3000tff(self):
        self._test_validation_case('3000tff', 'packed.zip')

    def test_3000ttf(self):
        self._test_validation_case('3000ttf', 'packed.zip')

    def test_3010tff(self):
        self._test_validation_case('3010tff', 'packed.zip')

    def test_3010ttf(self):
        self._test_validation_case('3010ttf', 'packed.zip')

    def test_b000tff(self):
        self._test_validation_case('b000tff', 'broken.zip')

    def test_b010tff(self):
        self._test_validation_case('b010tff', 'packed.zip')

    def test_1000tfm(self):
        self._test_validation_case('1000tfm', 'packed.zip')

    def test_regressions(self):
        self._test_validation_case('regression_001', 'bsp.c')


class Generic(unittest.TestCase):

    def setUp(self):
        self.conn = MoodleConnection(interactive=True)

    def test_assignment_list(self):
        assignments = MoodleAssignments(self.conn, course_filter=[TEST_COURSE_ID, ])
        assert(len(assignments) > 0)

    def test_course_folders(self):
        course = MoodleCourse.from_course_id(self.conn, TEST_COURSE_ID)
        folders = course.get_folders()
        for folder in folders:
            if folder.id == TEST_FOLDER_ID:
                for file in folder.files:
                    print(file)
                    file.download()
                    return
#        assert(False)

    def test_submission_list(self):
        assignments = MoodleAssignments(self.conn, course_filter=[TEST_COURSE_ID, ])
        for assignment in assignments:
            if assignment.id == TEST_ASSIGNMENT_ID:
                print(assignment)
                submissions = MoodleSubmissions(self.conn, assignment)
                print(submissions)


# Helper functions for validators in the test suite

def assert_raises(callable, *args, **kwargs):
    try:
        return callable(*args, **kwargs)
    except Exception:
        pass
    else:
        logger.error("Unexpected non-occurence of exception while running " + str(callable))
        raise SystemExit()


def assert_dont_raises(callable, *args, **kwargs):
    try:
        return callable(*args, **kwargs)
    except Exception as e:
        logger.error("Unexpected occurence of exception while running {1}: {0} ".format(e, str(callable)))
        raise SystemExit()
    else:
        pass
