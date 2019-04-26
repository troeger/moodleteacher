import collections
import requests
from unittest.mock import Mock

import logging
logger = logging.getLogger('moodleteacher')


class BaseRequest():
    """
    A HTTP(S) request that considers :class:`MoodleConnection` settings.
    """
    def __init__(self, conn, url):
        self.conn = conn
        self.url = url

    def get_absolute(self, params=None):
        if self.conn.is_fake:
            logger.info("Fake connection, not performing web service GET call.")
            the_response = Mock(spec=requests.models.Response)
            the_response.json.return_value = {}
            the_response.status_code = 200
            return the_response
        logger.debug("Performing web service GET call ...")
        while (True):
            try:
                result = requests.get(self.url, params=params, timeout=self.conn.timeout)
            except requests.exceptions.Timeout:
                logger.error("Timeout for GET request to {0} after {1} seconds, trying again.".format(self.url, self.conn.timeout))
                continue
            break
        logger.debug("Result status code: {0}".format(result.status_code))
        result.raise_for_status()
        return result

    def post_absolute(self, params=None, data=None):
        if self.conn.is_fake:
            logger.info("Fake connection, not performing web service POST call.")
            the_response = Mock(spec=requests.models.Response)
            the_response.json.return_value = {}
            the_response.status_code = 200
            return the_response
        logger.debug("Performing web service POST call ...")
        while (True):
            try:
                result = requests.post(self.url, params=params, data=data, timeout=self.conn.timeout)
            except requests.exceptions.Timeout:
                logger.error("Timeout for POST request to {0} after {1} seconds, trying again.".format(self.url, self.conn.timeout))
                continue
            break
        logger.debug("Result status code: {0}".format(result.status_code))
        result.raise_for_status()
        return result


class MoodleRequest(BaseRequest):
    """
    A Moodle web service API request.
    """

    def __init__(self, conn, funcname):
        """
        Prepares a Moodle web service API request that considers :class:`MoodleConnection` settings.

        Parameters:
            conn: The MoodleConnection object.
            funcname: The name of the Moodle web service function.
        """
        super().__init__(conn, conn.ws_url)
        self.base_params = {'wsfunction': funcname,
                            'moodlewsrestformat': 'json',
                            'wstoken': conn.token}

    def _encode_param(self, params, key, value):
        """
        Convert Python sequences to numbered JSON list,
        and Python numbers to strings.
        """
        if isinstance(value, collections.Sequence) and not isinstance(value, str):
            for i, v in enumerate(value):
                self._encode_param(params, "{}[{}]".format(key, i), v)
            return
        if isinstance(value, int):
            value = str(value)
        params[key] = value

    def get(self, params=None):
        """
        Perform a GET request to the Moodle web service API.
        """
        real_params = self.base_params.copy()
        # Convert addtional parameters into correct format
        # Base parameters are already fine
        if params:
            for k, v in params.items():
                self._encode_param(real_params, k, v)
        result = self.get_absolute(params=real_params)
        data = result.json()
        # logger.debug("Result: {0}".format(data))           # massive data amount, also security sensitive
        logger.debug("Result: {0}".format(result))
        if isinstance(data, dict) and "exception" in data:
            raise Exception(
                "Error response for Moodle web service GET request ('{message}')".format(**result.json()))
        return result

    def post(self, params=None, data=None):
        """
        Perform a POST request to the Moodle web service API.
        """
        # Convert addtional parameters into correct format
        # Base parameters are already fine
        real_params = self.base_params.copy()
        if params:
            for k, v in params.items():
                self._encode_param(real_params, k, v)
        result = self.post_absolute(params=real_params, data=data)
        data = result.json()
        # logger.debug("Result: {0}".format(data))          # massive data amount, also security sensitive
        logger.debug("Result: {0}".format(result))
        if isinstance(data, dict):
            if "exception" in data:
                raise Exception(
                    "Error response for Moodle web service POST request ('{message}')".format(**result.json()))
        return result
