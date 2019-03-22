from moodleteacher.submissions import MoodleSubmission
from moodleteacher.assignments import MoodleAssignment
from moodleteacher.courses import MoodleCourse
from moodleteacher.validation import Job
from moodleteacher.files import MoodleFile
from moodleteacher.connection import MoodleConnection
import os
import logging
import responses
import re


@responses.activate
def _test_validation_case(directory, student_file):
    '''
    Each of the validator.py files in tests/submfiles/validation
    uses the Python assert() statement to check by itself if the result
    is the expected one for its case.
    '''
    base_dir = os.path.dirname(__file__) + '/submfiles/validation/'
    case_dir = base_dir + directory
    try:
        validator = MoodleFile.from_local_file(
            case_dir + os.sep + 'validator.py')
    except FileNotFoundError:
        validator = MoodleFile.from_local_file(
            case_dir + os.sep + 'validator.zip')

    # Prepare faked answers for moodle WS API calls performed during validator execution
    answer = {"courses": [{"id": 1, "options": [{"name": "update", "available": True},
                                                {"name": "editcompletion",
                                                    "available": False},
                                                {"name": "filters",
                                                    "available": True},
                                                {"name": "reports",
                                                    "available": True},
                                                {"name": "backup",
                                                    "available": True},
                                                {"name": "restore",
                                                    "available": True},
                                                {"name": "files",
                                                    "available": False},
                                                {"name": "tags", "available": True},
                                                {"name": "gradebook",
                                                    "available": True},
                                                {"name": "outcomes",
                                                    "available": True},
                                                {"name": "badges",
                                                    "available": True},
                                                {"name": "import",
                                                    "available": True},
                                                {"name": "publish",
                                                    "available": False},
                                                {"name": "reset",
                                                    "available": True},
                                                {"name": "roles", "available": True}]}],
              "warnings": []}
    responses.add(responses.POST, re.compile('(.*)core_course_get_user_administration_options(.*)'), json=answer)

    answer = [{"id": 64465,
               "username": "ptroeger",
               "firstname": "Peter",
               "lastname": "Tröger",
               "fullname": "Peter Tröger",
               "email": "peter@troeger.eu",
               "idnumber": "8098",
               "firstaccess": 1519124480,
               "lastaccess": 1553091117,
               "groups": [],
               "roles": [],
               "enrolledcourses": []
               }]
    responses.add(responses.POST, re.compile('(.*)core_enrol_get_enrolled_users(.*)'), json=answer)

    responses.add(responses.POST, re.compile('(.*)mod_assign_save_grade(.*)'), json=answer)

    # test with simulated server responses
    conn = MoodleConnection("https://simulated_host", "simulatedtoken", interactive=False)
    course = MoodleCourse(conn=conn, course_id=1,
                          shortname='Test Course', fullname='Test Course')
    assignment = MoodleAssignment(course=course, assignment_id=1, allows_feedback_comment=True)
    submission = MoodleSubmission.from_local_file(assignment=assignment, fpath=case_dir + os.sep + student_file)
    job = Job(submission,
              validator,
              "Test suite validator run: \n\n")
    job.start(log_level=logging.DEBUG)

    # test with fake mode
    fake_conn = MoodleConnection(is_fake=True)
    course = MoodleCourse(conn=fake_conn, course_id=2)
    assignment = MoodleAssignment(course=course, assignment_id=2, allows_feedback_comment=True)
    submission = MoodleSubmission.from_local_file(assignment=assignment, fpath=case_dir + os.sep + student_file)
    job = Job(submission,
              validator,
              "Test suite validator run (fake mode): \n\n")
    job.start(log_level=logging.DEBUG)


def test_0100fff():
    _test_validation_case('0100fff', 'python.pdf')


def test_0100tff():
    _test_validation_case('0100tff', 'packed.zip')


def test_0100ttf():
    _test_validation_case('0100ttf', 'package.zip')


def test_1000fff():
    _test_validation_case('1000fff', 'helloworld.c')


def test_1000fft():
    _test_validation_case('1000fft', 'helloworld.c')


def test_1000tff():
    _test_validation_case('1000tff', 'packed.zip')


def test_1000tft():
    _test_validation_case('1000tft', 'packed.zip')


def test_1000ttf():
    _test_validation_case('1000ttf', 'packed.zip')


def test_1000ttt():
    _test_validation_case('1000ttt', 'packed.tgz')


def test_1010tff():
    _test_validation_case('1010tff', 'packed.zip')


def test_1010ttf():
    _test_validation_case('1010ttf', 'packed.zip')


def test_1100tff():
    _test_validation_case('1100tff', 'packed.zip')


def test_1100ttf():
    _test_validation_case('1100ttf', 'packed.zip')


def test_3000tff():
    _test_validation_case('3000tff', 'packed.zip')


def test_3000ttf():
    _test_validation_case('3000ttf', 'packed.zip')


def test_3010tff():
    _test_validation_case('3010tff', 'packed.zip')


def test_3010ttf():
    _test_validation_case('3010ttf', 'packed.zip')


def test_b000tff():
    _test_validation_case('b000tff', 'broken.zip')


def test_b010tff():
    _test_validation_case('b010tff', 'packed.zip')


def test_1000tfm():
    _test_validation_case('1000tfm', 'packed.zip')


def test_regressions():
    _test_validation_case('regression_001', 'bsp.c')
    _test_validation_case('regression_002', 'möhre.java')
