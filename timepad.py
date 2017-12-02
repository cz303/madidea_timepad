import requests
import logging
import json

API_URL = 'https://api.timepad.ru'


def introspect(token):
    payload = {
        'token': token
    }
    response = requests.get(API_URL + '/introspect', params=payload)
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return None
    return json.loads(response.text)
