from moodleteacher.tests import assert_raises, assert_dont_raises
from moodleteacher import compiler


def validate(job):
    student_files = ['helloworld.c']
    assert_dont_raises(job.run_build, inputs=student_files, output='helloworld')
