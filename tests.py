import unittest
from moodleteacher.connection import MoodleConnection
from moodleteacher.assignments import MoodleAssignments
from moodleteacher.courses import MoodleCourse

TEST_COURSE_ID = 14711


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
            print(folder)
            for file in folder.files:
                print(file)
