from moodleteacher.compiler import JAVAC
from moodleteacher.tests import assert_dont_raises


def output_test(job, wuerfel_zahlen, summe, ist_kniffel):
    command = "java Kniffel " + " ".join(wuerfel_zahlen)
    exit_code, output = job.run_program(command)
    for wuerfel in wuerfel_zahlen:
        if wuerfel not in output:
            job.send_fail_result("Fehler: Nach dem Aufruf '{0}' wurde der Würfelwert {1} nicht ausgegeben.".format(command, wuerfel),
                                 "Fehlender Würfelwert")
            return False

    if summe not in output:
        job.send_fail_result("Fehler: Nach dem Aufruf '{0}' wurde die Summe nicht ausgegeben.".format(command, wuerfel),
                             "Fehlende Summe")
        return False

    if ist_kniffel:
        if "ja" not in output.lower():
            job.send_fail_result("Fehler: Nach dem Aufruf '{0}' fehlt die Ausgabe 'Ja' beim Test auf Kniffel.".format(command, wuerfel),
                                 "Fehlendes Ergebnis bei Kniffel-Test.")
            return False
    else:
        if "nein" not in output.lower():
            job.send_fail_result("Fehler: Nach dem Aufruf '{0}' fehlt die Ausgabe 'Nein' beim Test auf Kniffel.".format(command, wuerfel),
                                 "Fehlendes Ergebnis bei Kniffel-Test.")
            return False
    return True


def validate(job):
    job.prepare_student_files(remove_directories=True, recode=True)

    if not job.ensure_files(['Kniffel.java']):
        job.send_fail_result("Ihre Abgabe muss die Datei 'Kniffel.java' enthalten.", "FEHLER: Datei Kniffel.java fehlt.")
        return

    assert_dont_raises(job.run_compiler, compiler=JAVAC, inputs=['Kniffel.java'])

    if not output_test(job, ["5", "4", "3", "2", "1"], "15", False):
        return
    if not output_test(job, ["5", "5", "5", "5", "5"], "25", True):
        return
    if not output_test(job, ["1", "1", "1", "1", "1"], "5", True):
        return
    if not output_test(job, ["3", "4", "3", "4", "3"], "17", False):
        return

    command = "java Kniffel 9 0 7 2 9"
    exit_code, output = job.run_program(command)
    if "1" not in output:
        job.send_fail_result("Fehler: Nach dem Aufruf '{0}' wurde nicht der fehlerhafte Würfel 1 gemeldet.".format(command),
                             "Fehlende Meldung zum falschen Würfel")
        return

    command = "java Kniffel 1 1 1 1 9"
    exit_code, output = job.run_program(command)
    if "5" not in output:
        job.send_fail_result("Fehler: Nach dem Aufruf '{0}' wurde nicht der fehlerhafte Würfel 5 gemeldet.".format(command),
                             "Fehlende Meldung zum falschen Würfel")
        return

    job.send_pass_result("Alle Prüfungen erfolgreich, die Abgabe erfüllt die minimalen Anforderungen. Super!", "KORREKT.")
