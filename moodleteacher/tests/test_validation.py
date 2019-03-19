from moodleteacher.submissions import MoodleSubmission
from moodleteacher.jobs import ValidationJob
from moodleteacher.files import MoodleFile
import os


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

    job = ValidationJob(MoodleSubmission.from_local_file(case_dir + os.sep + student_file),
                        validator)
    job._run_validate()


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
