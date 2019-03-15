from collections import defaultdict

from .requests import MoodleRequest
from .users import MoodleUser, MoodleGroup


class MoodleCourse():
    '''
        A single Moodle course.
    '''
    assignments = []
    id = None
    fullname = None
    shortname = None
    can_grade = None
    users = {}          # key is user id, value is MoodleUser object
    groups = {}         # key is group id, value is MoodleGroup object
    group_members = defaultdict(set)  # key is group ID, value id user ID

    def __init__(self, conn, raw_json):
        self.id = raw_json['id']
        self.fullname = raw_json['fullname']
        self.shortname = raw_json['shortname']
        self.get_admin_options(conn)
        # fetch list of users and groups in this course
        params = {'courseid': self.id}
        raw_json = MoodleRequest(
            conn, 'core_enrol_get_enrolled_users').post(params).json()
        for raw_json_user in raw_json:
            moodle_user = MoodleUser.from_json(raw_json_user)
            # Django get_or_create ... in ugly.
            self.users[moodle_user.id] = moodle_user
            if 'groups' in raw_json_user.keys():
                for raw_json_group in raw_json_user['groups']:
                    moodle_group = MoodleGroup.from_json(self, raw_json_group)
                    self.groups[moodle_group.id] = moodle_group
                    self.group_members[moodle_group.id].add(moodle_user.id)

    def get_group(self, group_id):
        if group_id in self.groups.keys():
            return self.groups[group_id]
        else:
            return None

    def get_user(self, user_id):
        return self.users[user_id]

    def get_group_members(self, group_id):
        return [self.users[user_id] for user_id in self.group_members[group_id]]

    def __str__(self):
        return(self.fullname)

    def get_admin_options(self, conn):
        params = {'courseids[0]': self.id}
        response = MoodleRequest(
            conn, 'core_course_get_user_administration_options').post(params).json()
        for option in response['courses'][0]['options']:
            if option['name'] == 'gradebook':
                if option['available'] is True:
                    self.can_grade = True
                else:
                    self.can_grade = False
