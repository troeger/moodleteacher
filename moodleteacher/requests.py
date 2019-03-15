import collections
import requests

import logging
logger = logging.getLogger('moodleteacher')


class MoodleRequest():
    '''
        A Moodle web service request.
    '''

    def __init__(self, conn, funcname):
        '''
            Prepares a Moodle web service request.

            Parameters:
                conn: The MoodleConnection object.
                funcname: The name of the Moodle web service function.
        '''
        self.conn = conn
        self.ws_params = conn.ws_params.copy()
        self.ws_params['wsfunction'] = funcname

    def _encode_param(self, params, key, value):
        if isinstance(value, collections.Sequence):
            for i, v in enumerate(value):
                self._encode_param(params, "{}[{}]".format(key, i), v)
            return
        if isinstance(value, int):
            value = str(value)
        params[key] = value

    def get(self, **get_params):
        '''
            Perform a GET request to the Moodle web service.
        '''
        params = self.ws_params.copy()
        for key, value in get_params.items():
            self._encode_param(params, key, value)
        logger.debug("Performing web service GET call for " +
                     repr(params))
        result = requests.get(self.conn.ws_url, params=params)
        logger.debug("Result: " + str(result))
        result.raise_for_status()
        data = result.json()
        if isinstance(data, dict) and "exception" in data:
            raise Exception(
                "Error response for Moodle web service GET request ('{message}')".format(**result.json()))
        return result

    def post(self, post_params):
        '''
            Perform a POST request to the Moodle web service
            with the given parameters.
        '''
        post_data = {**self.ws_params, **post_params}
        logger.debug("Performing web service POST call for " +
                     self.ws_params['wsfunction'])
        result = requests.post(self.conn.ws_url, params=post_data)
        logger.debug("Result: " + str(result))
        result.raise_for_status()
        data = result.json()
        if isinstance(data, dict):
            if "exception" in data:
                raise Exception(
                    "Error response for Moodle web service POST request ('{message}')".format(**result.json()))
        return result
