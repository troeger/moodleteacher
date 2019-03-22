# Test Unicode handling

from moodleteacher.compiler import JAVAC
from moodleteacher.tests import assert_dont_raises, assert_raises


def validate(job):
    job.prepare_student_files(remove_directories=False)

    if not job.ensure_files(['möhre.java']):
        job.send_fail_result("Ihre Abgabe muss den Dateinamen 'möhre.java' haben.", "FEHLER: Falscher Dateiname.")
        return

    job.run_compiler(compiler=JAVAC, inputs=['möhre.java'])
    assert_dont_raises(job.run_program, 'java möhre')
    prog = job.spawn_program('java möhre')
    assert_raises(prog.expect_output, 'möhre möhre möhre')
    prog = job.spawn_program('java möhre', encoding="utf-8")
    assert_dont_raises(prog.expect_output, 'möhre möhre möhre')
