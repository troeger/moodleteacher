import unittest
from moodleteacher.connection import MoodleConnection
from moodleteacher.assignments import MoodleAssignments
from moodleteacher.courses import MoodleCourse

# Note: We assume that Moodleteacher was started in interactive mode
#       before, so that credentials and URL are cached, and that we can
#       use the resources defined below for testing.

TEST_COURSE_ID = 5787
TEST_FOLDER_ID = 432300   # should contain at least one file


class Test(unittest.TestCase):

    def setUp(self):
        self.conn = MoodleConnection(interactive=True)

    def test_assignment_list(self):
        assignments = MoodleAssignments(self.conn, course_filter=[TEST_COURSE_ID, ])
        assert(len(assignments) > 0)

    def test_course_folders(self):
        course = MoodleCourse.from_course_id(self.conn, TEST_COURSE_ID)
        folders = course.get_folders()
        for folder in folders:
            for file in folder.files:
                file.download()
