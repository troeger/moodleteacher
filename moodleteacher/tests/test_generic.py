from moodleteacher.connection import MoodleConnection
from moodleteacher.assignments import MoodleAssignments, MoodleAssignment
from moodleteacher.submissions import MoodleSubmissions
from moodleteacher.courses import MoodleCourse

# Note: We assume that Moodleteacher was started in interactive mode
#       before, so that credentials and URL are cached, and that we can
#       use the resources defined below for testing with the cached account.

TEST_COURSE_ID = 5787
TEST_FOLDER_ID = 432312            # should contain at least one file
TEST_ASSIGNMENT_CMID = 432313      # should contain at least one submission
TEST_SUBMISSION_USER_ID = 64465    # should be gradable


conn = MoodleConnection(interactive=True)


def test_assignment_list():
    assignments = MoodleAssignments(conn, course_filter=[TEST_COURSE_ID, ])
    assert(len(assignments) > 0)


def test_course_folders():
    course = MoodleCourse.from_course_id(conn, TEST_COURSE_ID)
    folders = course.get_folders()
    for folder in folders:
        if folder.id_ == TEST_FOLDER_ID:
            for file in folder.files:
                assert(len(file.content) > 0)


def test_submission_list():
    assignments = MoodleAssignments(conn, course_filter=[TEST_COURSE_ID, ])
    found_one = False
    for assignment in assignments:
        if assignment.cmid == TEST_ASSIGNMENT_CMID:
            submissions = MoodleSubmissions.from_assignment(assignment)
            assert(len(submissions) > 0)
            found_one = True
    assert(found_one)


def test_grading():
    course = MoodleCourse.from_course_id(conn, TEST_COURSE_ID)
    assignment = MoodleAssignment.from_course_module_id(course, TEST_ASSIGNMENT_CMID)
    submissions = MoodleSubmissions.from_assignment(assignment)
    assert(len(submissions) > 0)
    found_one = False
    for sub in submissions:
        if sub.userid == TEST_SUBMISSION_USER_ID:
            found_one = True
            sub.save_grade(grade=5, feedback="Test feedback comment 1")
            sub.save_feedback("Test feedback comment 2")
    assert(found_one)
