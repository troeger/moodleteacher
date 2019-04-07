"""
Functionality dealing with Moodle assignments.
"""

import datetime

from .submissions import MoodleSubmission
from .requests import MoodleRequest
from .courses import MoodleCourse

import logging
logger = logging.getLogger('moodleteacher')


class MoodleAssignment():
    """
        A single Moodle assignment.
    """

    def __init__(self, course, assignment_id, course_module_id=None, duedate=None, cutoffdate=None, deadline=None, name=None, allows_feedback_comment=None):
        self.conn = course.conn
        self.course = course
        self.id_ = assignment_id
        self.cmid = course_module_id
        self.duedate = duedate
        self.cutoffdate = cutoffdate
        self.deadline = deadline
        self.name = name
        self.allows_feedback_comment = allows_feedback_comment

    @classmethod
    def from_raw_json(cls, course, raw_json):
        """
        Create a :class:`MoodleAssignment` object from raw JSON information.
        """
        duedate = datetime.datetime.fromtimestamp(raw_json['duedate'])
        cutoffdate = datetime.datetime.fromtimestamp(raw_json['cutoffdate'])
        allows_feedback_comment = False
        for config in raw_json['configs']:
            if config['plugin'] == 'comments' and \
               config['subtype'] == 'assignfeedback' and \
               config['name'] == 'enabled' and \
               config['value'] == '1':
                allows_feedback_comment = True

        return cls(course=course,
                   assignment_id=raw_json['id'],
                   course_module_id=raw_json['cmid'],
                   duedate=duedate,
                   cutoffdate=cutoffdate,
                   deadline=cutoffdate if duedate < cutoffdate else duedate,
                   name=raw_json['name'],
                   allows_feedback_comment=allows_feedback_comment)

    @classmethod
    def from_assignment_id(cls, course, assignment_id):
        """
        Create a :class:`MoodleAssignment` object just from an assignment ID.
        """
        # This approach is overkill, but
        # there seems to be no API call to fetch single assignment
        # detail information.
        assignments = course.assignments()
        for assignment in assignments:
            if assignment.id_ == assignment_id:
                return assignment
        return None

    @classmethod
    def from_course_module_id(cls, course, course_module_id):
        """
        Create a :class:`MoodleAssignment` object just from a course module ID.
        """
        params = {}
        params['cmid'] = course_module_id
        response = MoodleRequest(
            course.conn, 'core_course_get_course_module').get(params).json()
        if response['cm']['modname'] == 'assign':
            # Determine missing information.
            # This approach is overkill, but
            # there seems to be no API call to fetch single assignment
            # detail information.
            assignments = course.assignments()
            for assignment in assignments:
                if assignment.id_ == response['cm']['instance']:
                    return assignment
        return None

    def __str__(self):
        if self.name:
            return("{0.name} (Fällig: {0.deadline})".format(self))
        else:
            return self.id_

    def deadline_over(self):
        return datetime.datetime.now() > self.deadline

    def get_user_submission(self, user_id):
        """
        Create a new :class:`MoodleSubmission` object with the submission of
        the given user in this assignment, or None.
        """
        params = {}
        params['assignid'] = self.id_
        params['userid'] = user_id
        logger.debug("Fetching submission information for user {userid} in assignment {assignid}".format(**params))
        try:
            response = MoodleRequest(
                self.conn, 'mod_assign_get_submission_status').get(params).json()
        except Exception as e:
            logger.error("Could not fetch submission information:")
            logger.exception(e)
            return None
        if 'lastattempt' in response:
            if 'submission' in response['lastattempt']:
                submission = MoodleSubmission(
                    conn=self.conn,
                    submission_id=response['lastattempt']['submission']['id'],
                    assignment=self,
                    user_id=response['lastattempt']['submission']['userid'],
                    status=response['lastattempt']['submission']['status'])
                if 'teamsubmission' in response['lastattempt']:
                    logger.debug("Identified team submission.")
                    submission.group_id = response['lastattempt']['teamsubmission']['groupid']
                    submission.parse_plugin_json(response['lastattempt']['teamsubmission']['plugins'])
                else:
                    logger.debug("Identified single submission.")
                    submission.parse_plugin_json(response['lastattempt']['submission']['plugins'])
                return submission
        return None

    def submissions(self):
        """
        Get a list of :class:`MoodleSubmission` objects for this assignment.
        """
        result = []
        # First, fetch the overview list of submissions for this assignment.
        params = {'assignmentids[0]': self.id_}
        response = MoodleRequest(
            self.conn, 'mod_assign_get_submissions').post(params).json()
        if 'assignments' in response:
            for response_assignment in response['assignments']:
                assert(response_assignment['assignmentid'] == self.id_)
                for subm_data in response_assignment['submissions']:
                    # On group submissions, the submission details fetch with the
                    # first API call are incomplete.
                    # We therefore query each identified
                    # submission with a separate API call.
                    sub = self.get_user_submission(subm_data['userid'])
                    if sub is not None:
                        result.append(sub)
        return result


class MoodleAssignments(list):
    """
    A list of :class:`MoodleAssignment` instances.
    """

    def __init__(self, conn, course_filter=None, assignment_filter=None):
        params = {}
        if course_filter:
            params['courseids'] = course_filter
        response = MoodleRequest(
            conn, 'mod_assign_get_assignments').get(params).json()
        if 'courses' in response:
            for course_data in response['courses']:
                course = MoodleCourse.from_raw_json(conn, course_data)
                if (course_filter and course.id_ in course_filter) or not course_filter:
                    for ass_data in course_data['assignments']:
                        assignment = MoodleAssignment.from_raw_json(
                            course, ass_data)
                        if (assignment_filter and assignment.cmid in assignment_filter) or not assignment_filter:
                            self.append(assignment)
