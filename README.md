# The moodleteacher library

This Python library is intended for teachers with courses in the Moodle learning management system.
They can easily automate their grading or course management procedures, so that clicking around
on the web page is no longer neccessary.

## Getting Started

These instructions will get you the library up and running on your local machine.

### Installation

The library demands at least Python 3.6. Install the software with 

```
pip3.6 install moodleteacher
```

Start an interactive Python session and load the library:

```
(venv) shaw:moodleteacher ptroeger$ python
Python 3.6.5 (default, Apr 25 2018, 14:23:58) 
[GCC 4.2.1 Compatible Apple LLVM 9.1.0 (clang-902.0.39.1)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import moodleteacher as mt
```

First, you need to provide the neccessary connection information. The host name is the web server where your Moodle installation lives. The token can be retrieved from your Moodle user settings (Preferences -> User account -> Security keys -> Service "Moodle mobile web service"):

```
>>> conn=mt.MoodleConnection(moodle_host="https://lms.beuth-hochschule.de", token="aaaaabbbbbcccccdddddeeeee12345")
```

You can now fetch the list of assignments that are accesssible for you:

```
>>> assignments=mt.MoodleAssignments(conn)
>>> for assign in assignments:
...     print(assign)
... 
```

Assignment objects provide a list of submissions. Each submission object provides the files (or text) submitted by the student:

```
>>> for assignment in assignments:
...     for submission in assignment.submissions:
...         print("User {0} submitted {1} files.".format(submission.userid, len(submission.files)))
```

Submissions can be trivially graded:

```
>>> for assignment in assignments:
...     for submission in assignment.submissions:
...         submission.save_grade(0.0, "Everybody fails in this assignment. You too.")
```

There is also support for:

  - Previewing textfield submissions, PDF files, and text files.
  - Running submitted files locally as shell script, for testing purposes.
  - Running submitted files remotely on another machine, for testing purposes.
  

Check [the implementation](moodleteacher/__init__.py) for what you can do with the different parts of the library. Real documentation is planned.

You can also take a look at the complex usage example in the [grader.py](grader.py) script, which shows nearly all featurs of the library in action.

## License

This project is licensed under the GPL3 License - see the [LICENSE](LICENSE) file for details.
