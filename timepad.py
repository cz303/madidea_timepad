import requests
import logging
import json
import datetime

TIMEPAD_TOKEN = '97dabe0642c19a62ace6b2321a3725cc2b71a183'
API_URL = 'https://api.timepad.ru'


def get_all_user_events(user_token):
    response = requests.get(API_URL + '/introspect?token={0}'.format(user_token))
    user_info = json.loads(response.text)
    # user_id = user_info['user_id']
    event_ids = [order['event']['id'] for order in user_info['orders']]
    for event_id in event_ids:
        response = requests.get(API_URL + '/v1/events/{0}?fields=name&token={1}'.format(event_id, user_token))
        if response.status_code != requests.codes.ok:
            logging.warning('Private event: {0}'.format(event_id))
            continue
        event_info = json.loads(response.text)
        print(event_info['name'])
    return event_ids


def get_user_events(user_token):
    response = requests.get(API_URL + '/introspect?token={0}'.format(user_token))
    user_info = json.loads(response.text)
    event_ids = [order['event']['id'] for order in user_info['orders']]
    # print(requests.get(API_URL + '/v1/events/?event_ids={0}&access_statuses=public&starts_at_min=now'.format(
    #    ','.join(str(id) for id in event_ids))).text)
    return event_ids


def get_events_by_token(token):
    response = requests.get(API_URL + '/introspect?token={0}'.format(token))
    user_info = json.loads(response.text)
    event_ids = [order['event']['id'] for order in user_info['orders']]

    response = requests.get(API_URL + '/v1/events', params={
        'event_ids': ','.join(str(id) for id in event_ids),
        'starts_at_min': 'now',
        'limit': 5
    })
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return []

    events = []
    for event in json.loads(response.text)["values"]:
        event_repr = "Что? {}\n Что-что? {}\n Когда? {}\n Подробнее: {}".format(event["name"],
                                                                                event["categories"][0]["name"],
                                                                                ", ".join(
                                                                                    event["starts_at"].split("T")),
                                                                                event["url"])
        events.append(event_repr)

    return events


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


def get_events_by_date(date=datetime.datetime.today().strftime('%Y-%m-%d')):
    response = requests.get(API_URL + '/v1/events', params={
        'starts_at_min': date + "T00:00:00+0300",
        'starts_at_max': date + "T23:59:59+0300",
        'access_statuses': "public",
        'limit': 5
    })
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return []

    events = []
    for event in json.loads(response.text)["values"]:
        event_repr = "Что? {}\n Что-что? {}\n Когда? {}\n Подробнее: {}".format(event["name"],
                                                                                event["categories"][0]["name"],
                                                                                ", ".join(
                                                                                    event["starts_at"].split("T")),
                                                                                event["url"])
        events.append(event_repr)

    return events


if __name__ == '__main__':
    print(get_events_by_token(TIMEPAD_TOKEN))
