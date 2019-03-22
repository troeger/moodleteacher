from moodleteacher.connection import MoodleConnection
from moodleteacher.assignments import MoodleAssignments
from moodleteacher.courses import MoodleCourse
from moodleteacher.submissions import MoodleSubmissions


conn = MoodleConnection(interactive=True, is_fake=True)

TEST_COURSE_ID = 5787


def test_assignment_list():
    assignments = MoodleAssignments(conn)
    assert(assignments is not None)


def test_course_folders():
    course = MoodleCourse.from_course_id(conn, TEST_COURSE_ID)
    folders = course.get_folders()
    for folder in folders:
        for file in folder.files:
            assert(file is not None)


def test_submission_list():
    assignments = MoodleAssignments(conn)
    for assignment in assignments:
        submissions = MoodleSubmissions.from_assignment(assignment)
        assert(submissions is not None)
