from .requests import MoodleRequest


class MoodleUser():
    '''
        A Moodle user account.
    '''
    fullname = None
    email = None
    id = None

    @classmethod
    def from_json(cls, raw_json):
        obj = cls()
        obj.id_ = raw_json['id']
        obj.fullname = raw_json.get('fullname', '')
        obj.email = raw_json.get('email', '')
        obj.groups = raw_json.get('email', [])
        return obj

    @classmethod
    def from_userid(cls, conn, user_id):
        '''
            Fetch information about a user, based in the user id.

            Parameters:
                conn: The MoodleConnection object.
                user_id: The numerical user id.
        '''
        obj = cls()
        obj.id_ = user_id
        params = {'field': 'id', 'values[0]': str(user_id)}
        response = MoodleRequest(
            conn, 'core_user_get_users_by_field').post(params).json()
        if response != []:
            assert(response[0]['id'] == user_id)
            obj.fullname = response[0]['fullname']
            obj.email = response[0]['email']
        else:
            obj.fullname = "<Unknown>"
            obj.email = "<Unknown>"
        return obj

    def __str__(self):
        return "{0.fullname} ({0.id_})".format(self)


class MoodleGroup():
    '''
        A Moodle user group.
    '''
    fullname = None
    id = None
    members = {}
    course = None

    @classmethod
    def from_json(cls, course, raw_json):
        obj = cls()
        obj.id_ = raw_json['id']
        obj.course = course
        obj.fullname = raw_json.get('name', '')
        return obj

    def __str__(self):
        return "{0.fullname} ({0.id_})".format(self)
