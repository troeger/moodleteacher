Validation tutorial
###################

MoodleTeacher supports the automated validation of student submissions through a custom Python3 script, called a **validator**, which is written by the teacher.

A validator can come in two flavours:

- As single Python file named `validator.py`.
- As ZIP / TGZ archive with an arbitrary name, which must contain a file named `validator.py`.

The second option allows you to use additional files during the validation, such as profiling tools, libraries, or simply code not written by students.

The validation functionality of MoodleTeacher performs the following activities for you:

- Creation of a temporary working directory.
- Download (and unpacking) of the student submission in this directory.
- Download (and unpacking) of the validator in this directory.
- Execution of the validator.
- Reporting of results to Moodle, explicitely from the validator or implicitly.
- Cleanup of the temporary directory.

A validator script can use special functionality from the :class:`moodleteacher.validation.Job` class, which includes:

- Test for mandatory files in the student package.
- Compilation of student code.
- Execution of student code, including input simulation and output parsing.
- Reporting of validation results as teacher feedback in Moodle.

Examples for validators can be found `online <https://github.com/troeger/moodleteacher/tree/master/examples>`_.

Our companion project `MoodleRunner <https://github.com/troeger/moodleteacher>`_ wraps the validation functionality in a Docker image that is directly usable with your existing Moodle installation.

How to write a validator
=========================

We illustrate the idea with the following walk-through example:

Students get the assignment to create a C program that prints 'Hello World' on the terminal. The assignment description demands that they submit the C-file and a *Makefile* that creates a program called *hello*. The assignment description also explains that the students have to submit a ZIP archive containing both files.

Your job, as the assignment creator, is now to develop the ``validator.py`` file that checks an arbitrary student submission. Create a fresh directory that only contains an example student upload and the validator file:

.. literalinclude:: files/validators/helloworld/validator.py
   :linenos:

The ``validator.py`` file must contain a function ``validate(job)`` that is called by MoodleTeacher when a student submission should be validated. In the example above, this function performs the following steps for testing:

- Line 1: The validator function is called when all student files (and all files from the validator archive) are unpacked in a temporary working directory on the test machine. In case of name conflicts, the validator files always overwrite the student files.
- Line 3: The *make* tool is executed in the working directory with :meth:`~moodleteacher.validation.Job.run_make`. This step is declared to be mandatory, so the method will throw an exception if *make* fails.
- Line 4: A binary called *hello* is executed in the working directory with the helper function :meth:`~moodleteacher.validation.Job.run_program`. The result is the exit code and the output of the running program.
- Line 5: The generated output of the student program is checked for some expected text.
- Line 6: A positive validation result is sent back to Moodle with :meth:`~moodleteacher.validation.Job.send_pass_result`. 
- Line 7: A negative validation result is sent back to Moodle with :meth:`~moodleteacher.validation.Job.send_fail_result`.

Validators are ordinary Python code, so beside the functionalities provided by the job object, you can use any Python functionality. The example shows that in Line 4. 

If any part of the code leads to an exception that is not catched inside ``validate(job)``, than this is automatically interpreted as negative validation result. The MoodleTeacher code forwards the exception as generic information to the student. If you want to customize the error reporting, catch all potential exceptions and use your own call of :meth:`~moodleteacher.validation.Job.send_fail_result` instead.

Validator examples
==================

The following example shows a validator for a program in C that prints the sum of two integer values. The values are given as command line arguments. If the wrong number of arguments is given, the student code is expected to print `"Wrong number of arguments!"`. The student only has to submit the C file.

.. literalinclude:: files/validators/program_params/validator.py
    :linenos:

- Line 1: The `GCC` tuple constant is predefined in :mod:`moodleteacher.compiler` and refers to the well-known GNU C compiler. You can also define your own set of command-line arguments for another compiler.
- Line 3-10: The variable `test_cases` consists of the lists of inputs and the corresponding expected outputs.
- Line 14: The C file can be compiled directly by using :meth:`~moodleteacher.validation.Job.run_compiler`. You can specify the used compiler as well as the names of the input and output files.
- Line 15: The for-loop is used for traversing the `test_cases`-list. It consists of tuples which are composed of the arguments and the expected output.
- Line 16: The arguments can be handed over to the program through the second parameter of the :meth:`~moodleteacher.validation.Job.run_program` method. The former method returns the exit code as well as the output of the program.
- Line 17: It is checked if the created output equals the expected output.
- Line 18: If this is not the case an appropriate negative result is sent to the student and teacher with :meth:`~moodleteacher.validation.Job.send_fail_result`
- Line 19: After a negative result is sent there is no need for traversing the rest of the test cases, so the `validate(job)` function can be left.
- Line 20: After the traversal of all test cases, the student and teacher are informed that everything went well with :meth:`~moodleteacher.validation.Job.send_pass_result` 

The following example shows a validator for a C program that reads an positive integer from standard input und prints the corresponding binary number.

.. literalinclude:: files/validators/std_input/validator.py
    :linenos:

- Line 1: A `TimeoutException` is thrown when a program does not respond in the given time. The exception is needed for checking if the student program calculates fast enough.
- Line 3-9: In this case the test cases consist of the input strings and the corresponding output strings.
- Line 13: The method :meth:`~moodleteacher.validation.Job.run_build` is a combined call of `configure`, `make` and the compiler. The success of `make` and `configure` is optional. The default value for the compiler is GCC.
- Line 14: The test cases are traversed like in the previous example.
- Line 15: This time a program is spawned with :meth:`~moodleteacher.validation.Job.spawn_program`. This allows the interaction with the running program.
- Line 16: Standard input resp. keyboard input can be provided through the :meth:`~moodleteacher.runnable.RunningProgram.sendline` method of the returned object from line 14.
- Line 18-21: The validator waits for the expected output with :meth:`~moodleteacher.runnable.RunningProgram.expect`. If the program terminates without producing this output, a `TerminationException` exception is thrown. 
- Line 23: After the program successfully produced the output, it is expected to terminate. The test script waits for this with :meth:`~moodleteacher.runnable.RunningProgram.expect_end`
- Line 24: When the loop finishes, a positive result is sent to the student and teacher with :meth:`~moodleteacher.validation.Job.send_pass_result`.

.. warning::

   When using :meth:`~moodleteacher.runnable.RunningProgram.expect`, it is important to explicitely catch a  `TerminationException` and make an explicit fail report in your validation script. Otherwise, the student is only informed about an unexpected termination without further explanation.

The following example shows a validator for a C program that reads a string from standard input and prints it reversed. The students have to use for-loops for solving the task. Only the C file has to be submitted.

.. literalinclude:: files/validators/grep/validator.py
    :linenos:

- Line 1: A `TimeoutException` is thrown when a program does not respond in the given time. The exception is needed for checking if the student program calculates fast enough.
- Line 2: A `TerminationException` is thrown when a program terminates before delivering the expected output.
- Line 4-8: The test cases consist of the input strings and the corresponding reversed output strings.
- Line 12: The :meth:`~moodleteacher.validation.Job.grep` method searches the student files for the given pattern (e.g. a for-loop) and returns a list of the files containing it.
- Line 13-15: If there are not enough elements in the list, a negative result is sent with :meth:`~moodleteacher.validation.Job.send_fail_result` and the validation is ended.
- Line 17-25: For every test case a new program is spawned with :meth:`~moodleteacher.validation.Job.spawn_program`. The test script provides the neccessary input with :meth:`~moodleteacher.runnable.RunningProgram.sendline` and waits for the expected output with :meth:`~moodleteacher.runnable.RunningProgram.expect`. If the program is calculating for too long, a negative result is sent with :meth:`~moodleteacher.validation.Job.send_fail_result`.
- Line 26: If the result is different from the expected output a `TerminationException` is raised.
- Line 27-28: The corresponding negative result for a different output is sent with :meth:`~moodleteacher.validation.Job.send_fail_result` and the validation is cancelled.
- Line 29-30: If the program produced the expected output the validator waits  with :meth:`~moodleteacher.runnable.RunningProgram.expect_end` until the spawned program ends.
- Line 31: If every test case was solved correctly, a positive result is sent with :meth:`~moodleteacher.validation.Job.send_pass_result`. 

