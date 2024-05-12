"""
A connection to a chosen Moodle server.
"""

import os
import pickle

from getpass import getpass

from moodleteacher.requests import get_tokens


class MoodleConnection():
    """
    A connection to a Moodle installation.
    """
    token = None
    ws_url = None
    ws_params = {}
    moodle_host = None

    def __init__(self, moodle_host=None, token=None, interactive=False, is_fake=False, timeout=5):
        """
        Configures a connection to a Moodle server.

        Args:
            moodle_host:        The base URL of the Moodle installation.
            token:              The client security token for the Moodle API access.
            interactive (bool): Prompt interactively for parameters, if needed.
            is_fake (bool):     Create fake connection for testing purposes.
            timeout (int):      Timeout for HTTP requests.
        """
        self.is_fake = is_fake
        if is_fake:
            return
        if not moodle_host and not token:
            try:
                with open(os.path.expanduser("~/.moodleteacher"), "rb") as f:
                    moodle_host, token, privatetoken = pickle.load(f)
            except Exception:
                if not interactive:
                    raise AttributeError(
                        "Please provide moodle_host + token, or set interactive=True")
                else:
                    print("Seems like this your first connection attempt ...")
                    moodle_host = input("URL of the Moodle host: ")
                    moodle_username = input("User name on Moodle host: ")
                    moodle_password = getpass("User password on Moodle host: ")
                    tokens = get_tokens(moodle_host, moodle_username, moodle_password, timeout)
                    print(
                        "I will store these credentials in ~/.moodleteacher for the next time.")
                    with open(os.path.expanduser("~/.moodleteacher"), "xb") as f:
                        pickle.dump([moodle_host, tokens['token'], tokens['privatetoken']], f)
        self.token = token
        self.moodle_host = moodle_host
        self.timeout = timeout
        self.ws_params['wstoken'] = token
        self.ws_params['moodlewsrestformat'] = 'json'
        self.ws_url = moodle_host + "/webservice/rest/server.php"

    def __str__(self):
        if self.is_fake:
            return "Faked Moodle connection"
        else:
            return "Connection to " + self.moodle_host
