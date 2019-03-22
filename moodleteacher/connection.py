'''
Functionality dealing with connecting to Moodle.
'''

import os
import pickle


class MoodleConnection():
    '''
        A connection to a Moodle installation.
    '''
    token = None
    ws_url = None
    ws_params = {}
    moodle_host = None

    def __init__(self, moodle_host=None, token=None, interactive=False, is_fake=False):
        '''
            Establishes a connection to a Moodle installation.

            Parameters:
                moodle_host: The base URL of the Moodle installation.
                token: The client security token for the user.
                interactive: Prompt user for parameters, if needed.
        '''
        self.is_fake = is_fake
        if is_fake:
            return
        if not moodle_host and not token:
            try:
                with open(os.path.expanduser("~/.moodleteacher"), "rb") as f:
                    moodle_host, token = pickle.load(f)
            except Exception:
                if not interactive:
                    raise AttributeError(
                        "Please provide moodle_host + token, or set interactive=True")
                else:
                    print("Seems like this your first connection attempt ...")
                    moodle_host = input("URL of the Moodle host: ")
                    token = input("Moodle web service client security token: ")
                    print(
                        "I will store these credentials in ~/.moodleteacher for the next time.")
                    with open(os.path.expanduser("~/.moodleteacher"), "xb") as f:
                        pickle.dump([moodle_host, token], f)
        self.token = token
        self.moodle_host = moodle_host
        self.ws_params['wstoken'] = token
        self.ws_params['moodlewsrestformat'] = 'json'
        self.ws_url = moodle_host + "/webservice/rest/server.php"

    def __str__(self):
        if self.is_fake:
            return "Faked Moodle connection"
        else:
            return "Connection to " + self.moodle_host
