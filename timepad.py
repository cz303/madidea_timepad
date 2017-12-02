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


def get_events_data(ids):
    response = requests.get(API_URL + '/v1/events/?event_ids={0}&access_statuses=public'.format(
        ','.join(map(str, ids))))
    data = json.loads(response.text)
    return data['values']


def find_events(events, keywords):
    payload = {
        'fields': 'registration_data',
        'keywords': ','.join(keywords),
        'limit': 100
    }
    if len(events) > 0:
        payload['event_ids'] = ','.join(map(str, events))

    response = requests.get(API_URL + '/v1/events/', params=payload)
    events = json.loads(response.text)['values']
    events.sort(key=lambda event: -event['registration_data']['tickets_total'])
    return events[:3]

def format_event_descr(event):
    event_repr = ("_Что?_  *{0}*\n"
                  "_А глобально?_  {1}\n"
                  "_Когда?_  {2}\n"
                  "[Подробнее]({3})\n"
                  "[Регистрация]({3}#register)\n---").format(event["name"],
                                                        ', '.join(cat["name"] for cat in event["categories"]),
                                                        ", ".join(event["starts_at"].split('+')[0].split("T")),
                                                        event["url"])
    return event_repr

def get_events(params):
    response = requests.get(API_URL + '/v1/events', params=params)
    if response.status_code != requests.codes.ok:
        logging.warning('Got non-200 response from API: {}'.format(str(response.status_code)))
        logging.warning(response.text)
        return []

    events = []
    for event in json.loads(response.text)["values"]:
        events.append(format_event_descr(event))

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


if __name__ == '__main__':
    print(get_events_by_token(TIMEPAD_TOKEN, 'Санкт-Петербург'))
