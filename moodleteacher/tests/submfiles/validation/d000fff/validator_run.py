def validate(job):
    assert_dont_raises(job.prepare_student_files)
    student_files = ['helloworld.c']
    job.run_build(inputs=student_files, output='helloworld')
    job.run_program('./helloworld', timeout=2)
