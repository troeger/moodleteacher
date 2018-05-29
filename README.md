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
...     for submission in assignment.submissions():
...         print("User {0} submitted {1} files.".format(submission.userid, len(submission.files)))
```

Student file uploads can be downloaded with the [MoodleSubmissionFile](https://github.com/troeger/moodleteacher/blob/f5914a82743928c4fe9b4cb6da95938bcbda4689/moodleteacher/__init__.py#L173) class and previewed with a small integrated GUI application. The preview supports:

- HTML text
- PDF files
- Images
- Any other content, just shown in text form 
- ZIP files of any of the above

```
>>> for assignment in assignments:
...     for submission in assignment.submissions():
...             for file_url in submission.files:
...                     print(file_url)
... 
https://lms.beuth-hochschule.de/webservice/pluginfile.php/725647/assignsubmission_file/submission_files/32245/task03_ft.pdf
https://lms.beuth-hochschule.de/webservice/pluginfile.php/725647/assignsubmission_file/submission_files/75356/Fehlerbaum.jpg
https://lms.beuth-hochschule.de/webservice/pluginfile.php/725647/assignsubmission_file/submission_files/23454/Faultchar%2B-fertig.png
```

```
>>> stud_upload=mt.MoodleSubmissionFile(conn=conn, url="https://lms.beuth-hochschule.de/webservice/pluginfile.php/725647/assignsubmission_file/submission_files/75356/Fehlerbaum.jpg")
>>> stud_upload.is_pdf
False
>>> stud_upload.is_image
True
>>> from moodleteacher import preview
>>> mt.preview.show_preview("Preview Window", [stud_upload])
```

Submissions can be trivially graded:

```
>>> for assignment in assignments:
...     for submission in assignment.submissions:
...         submission.save_grade(0.0, "Everybody fails in this assignment. You too.")
```

There is also support for:

  - Running submitted files locally as shell script, for testing purposes.
  - Running submitted files remotely on another machine, for testing purposes.
  
Take a look at the complex usage example in the [grader.py](grader.py) script, which shows nearly all features of the library in action.

Real documentation is planned.

## License

This project is licensed under the GPL3 License - see the [LICENSE](LICENSE) file for details.
