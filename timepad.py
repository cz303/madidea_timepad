import requests
import logging
import json

API_URL = 'https://api.timepad.ru'

def get_user_events(user_token):
	user_response = requests.get(API_URL + '/introspect?token={0}'.format(user_token))
	user_info = json.loads(user_response.text)
	# user_id = user_info['user_id']
	event_ids = [order['event']['id'] for order in user_info['orders']]
	for event_id in event_ids:
		event_info = json.loads(requests.get(API_URL + '/v1/events/{0}?fields=name'.format(event_id)).text)
		if 'name' in event_info.keys():
			print(event_info['name'])	
	return event_ids

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
	print(get_user_events('9a9bc7b393f50a06297e80e6b5bf9d9fba23b351')) # aq token