import logging
import requests


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
        self.ws_params = conn.ws_params
        self.ws_params['wsfunction'] = funcname

    def get(self):
        '''
            Perform a GET request to the Moodle web service.
        '''
        logging.debug("Performing web service GET call for " +
                      self.ws_params['wsfunction'])
        result = requests.get(self.conn.ws_url, params=self.ws_params)
        logging.debug("Result: " + str(result))
        result.raise_for_status()
        if "exception" in result.json().keys():
            raise Exception("Error response for Moodle web service GET request ('{message}')".format(**result.json()))
        return result

    def post(self, post_params):
        '''
            Perform a POST request to the Moodle web service
            with the given parameters.
        '''
        post_data = {**self.ws_params, **post_params}
        logging.debug("Performing web service POST call for " +
                      self.ws_params['wsfunction'])
        result = requests.post(self.conn.ws_url, params=post_data)
        logging.debug("Result: " + str(result))
        result.raise_for_status()
        data = result.json()
        if isinstance(data, dict):
            if "exception" in data.keys():
                raise Exception("Error response for Moodle web service POST request ('{message}')".format(**result.json()))
        return result
