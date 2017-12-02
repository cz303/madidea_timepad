import requests
import logging
import json
import datetime

API_URL = 'https://api.timepad.ru'


def introspect(token):
    response = requests.get(API_URL + '/introspect', params={
        'token': token
    })
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return None
    return json.loads(response.text)


def get_events_by_date(date=datetime.datetime.today().strftime('%Y-%m-%d')):
    response = requests.get(API_URL + '/v1/events', params={
        'starts_at_min': date + "T00:00:00+0300",
        'starts_at_max': date + "T23:59:59+0300",
        'access_statuses': "public",
        'limit': 2
    })
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return None
    return json.loads(response.text)