import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
import timepad
import database
from datetime import datetime
import telegram
import requests
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

MAX_EVENTS_IN_MSG = 5

user_last_queries = {}

def start(bot, update):
    connector = database.Connector()
    user = connector.get_user_by_chat_id(update.message.chat_id)
    if user is None:
        connector.add_user(update.message.chat_id, update.message.from_user.username)
    bot.send_message(chat_id=update.message.chat_id,
                     text="Великолепный бот\n Список всех команд: /help")


def has_token(func):
    def func_wrapper(bot, update, *args, **kwargs):
        connector = database.Connector()
        user = connector.get_user_by_chat_id(update.message.chat_id)
        if user['timepadId'] is None:
            bot.send_message(chat_id=update.message.chat_id, text='Сначала установи токен')
            return
        func(bot, update, *args, **kwargs)

    return func_wrapper


def set_token(bot, update, args):
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id, text='Используй /token <ваш TimePad токен>')
        return
    token = args[0]

    data = timepad.introspect(token)
    if data is None:
        bot.send_message(chat_id=update.message.chat_id, text='Не получилось получить данные, попробуй позже')
        return
    active = data.get('active', False)
    if not active:
        bot.send_message(chat_id=update.message.chat_id, text='Некорректный токен')
        logging.info(repr(data))
        return

    connector = database.Connector()
    last_timestamp = 0
    city = ''

    connector.set_timepad_data_for_chat_id(update.message.chat_id, data['user_id'],
                                           data['user_email'], token, city, last_timestamp)
    events = timepad.get_user_events(token)
    user = connector.get_user_by_chat_id(update.message.chat_id)
    connector.add_user_events(user['id'], events)
    bot.send_message(chat_id=update.message.chat_id, text='Успех\n Список всех команд: /help')


def get_events_by_params(bot, update, parameters_input=None):
    print(parameters_input)
    try:
        min_index, parameters = user_last_queries[update.message.chat_id]
    except KeyError:
        min_index, parameters = 0, parameters_input
        user_last_queries[update.message.chat_id] = (min_index, parameters_input)

    if parameters_input is not None and (parameters != parameters_input):
        min_index, parameters = 0, parameters_input
        user_last_queries[update.message.chat_id] = (min_index, parameters_input)

    parameters["skip"] = min_index
    events = timepad.get_events(parameters)
    if len(events) - min_index > MAX_EVENTS_IN_MSG:
        kb = [[ telegram.InlineKeyboardButton("Да, ещё!", callback_data="ещё") ]]
        kb_markup = telegram.InlineKeyboardMarkup(kb)
        bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events[:MAX_EVENTS_IN_MSG]), parse_mode='Markdown')
        left = len(events) - MAX_EVENTS_IN_MSG - min_index
        text = "Мы показали не все события по этому запросу. Осталось {}. Показать ещё {}?".format(left, min(left, MAX_EVENTS_IN_MSG))
        bot.send_message(chat_id=update.message.chat_id,
                         text=text,
                         reply_markup=kb_markup)
        user_last_queries[update.message.chat_id] = (min_index + MAX_EVENTS_IN_MSG, parameters)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events[min_index:]), parse_mode='Markdown')
        user_last_queries.pop(update.message.chat_id, None)


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def error_callback(bot, update, error):
    logging.warning(repr(error))


def set_city(bot, update, args):
    if len(args) == 0:
        connector = database.Connector()
        city = connector.get_city(timepad.TIMEPAD_TOKEN)  # FIXIT
        bot.send_message(chat_id=update.message.chat_id,
                         text='Ты в городе {}'.format(city))
    else:
        city = str(*args)
        connector = database.Connector()
        connector.set_city(timepad.TIMEPAD_TOKEN, city)  # FIXIT
        bot.send_message(chat_id=update.message.chat_id,
                         text='Теперь ты в городе {}'.format(city))


def notify_subscribers(bot, user, new_events):
    connector = database.Connector()
    subscribers = connector.get_subscribers(user['id'])
    events = timepad.get_events_data(new_events)

    if len(events) == 0:
        return
    for event in events:
        for subscriber_id in subscribers:
            subscriber = connector.get_user_by_id(subscriber_id)
            logging.info('Notifying {}'.format(str(subscriber)))
            bot.send_message(chat_id=subscriber['chat_id'],
                             text='Твой друг @{} хочет посетить событие:\n{}'.format(
                                 user['tg_name'], event['url']))
            photo = event['poster_image']['uploadcare_url']
            if photo.startswith('//'):
                photo = 'https:' + photo
            bot.send_photo(chat_id=subscriber['chat_id'], photo=photo)


def crawl_new_events(bot, job):
    connector = database.Connector()
    user = connector.get_user_for_crawl()
    if user is None:
        return
    events = set(timepad.get_user_events(user['token']))
    old_events = set(connector.get_user_events(user['id']))
    new_events = events - old_events
    if len(new_events) > 0:
        logging.info('Notifying subscribers of {}'.format(str(user['id'])))
        notify_subscribers(bot, user, new_events)
        connector.add_user_events(user['id'], new_events)
    connector.set_introspect_timestamp(user['id'], datetime.now().timestamp())


def get_top_events(bot, update, args):
    top_events = timepad.get_top_events(args)
    message = '\n'.join(['Топ:'] + list(map(lambda event: event['url'], top_events)))
    bot.send_message(chat_id=update.message.chat_id,
                     text=message)


def subscribe(bot, update, args):
    connector = database.Connector()
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Use /subscribe <Telegram login>')
        return
    subscribed_to = args[0]
    if subscribed_to.startswith('@'):
        subscribed_to = subscribed_to[1:]
    user = connector.get_user_by_chat_id(update.message.chat_id)
    subscribed_id = connector.get_user_by_telegram(subscribed_to)
    if subscribed_id is None:
        bot.send_message(chat_id=update.message.chat_id, text='Неизвестный пользователь. Попросите его добавить бота')
        return
    connector.add_subscription(subscribed_id, user['id'])
    bot.send_message(chat_id=update.message.chat_id, text='Подписано')


def button_more_callback(bot, update):
    query = update.callback_query
    parameters = { 'access_statuses': "public" }
    update.message = query.message

    if "ещё" in query.data:
        get_events_by_params(bot, update)
        return
    if "local" in query.data:
        connector = database.Connector()
        city = connector.get_city(timepad.TIMEPAD_TOKEN)  # FIXIT
        if len(city) > 0:
            parameters['cities'] = city
    if "today" in query.data:
        date = datetime.today().strftime('%Y-%m-%d')
        parameters['starts_at_min'] = date + "T00:00:00+0300"
        parameters['starts_at_max'] = date + "T23:59:59+0300"
    if "my" in query.data:
        my_token = timepad.TIMEPAD_TOKEN # FIX!!!
        response = requests.get(timepad.API_URL + '/introspect?token={0}'.format(my_token))
        user_info = json.loads(response.text)
        event_ids = [order['event']['id'] for order in user_info['orders']]
        parameters['event_ids'] = ','.join(str(id) for id in event_ids)

    get_events_by_params(bot, update, parameters)


def unsubscribe(bot, update, args):
    connector = database.Connector()
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Use /unsubscribe <Telegram login>')
        return
    subscribed_to = args[0]
    if subscribed_to.startswith('@'):
        subscribed_to = subscribed_to[1:]
    user = connector.get_user_by_chat_id(update.message.chat_id)
    subscribed_id = connector.get_user_by_telegram(subscribed_to)
    if subscribed_id is None:
        bot.send_message(chat_id=update.message.chat_id, text='Неизвестный пользователь')
        return
    connector.remove_subscription(subscribed_id, user['id'])
    bot.send_message(chat_id=update.message.chat_id, text='Подписка удалена')


def show_subscriptions_handler(bot, update):
    connector = database.Connector()
    user = connector.get_user_by_chat_id(update.message.chat_id)
    subscriptions = connector.get_subscriptions(user['id'])
    message = '\n'.join(['Подписки:'] + list('@' + subscribed['tg_name'] for subscribed in subscriptions))
    bot.send_message(chat_id=update.message.chat_id, text=message)

def show_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Иди на хуй пока что')

def events_handler(bot, update):
    kb = [[ telegram.InlineKeyboardButton("Мои в этом городе", callback_data="my_local"),  telegram.InlineKeyboardButton("Мои в мире", callback_data="my_global") ],
          [ telegram.InlineKeyboardButton("Все в этом городе", callback_data="all_local"), telegram.InlineKeyboardButton("Все в мире", callback_data="all_global") ],
          [ telegram.InlineKeyboardButton("Сегодня в этом городе", callback_data="today_local"), telegram.InlineKeyboardButton("Сегодня в мире", callback_data="today_global") ]
          ]
    kb_markup = telegram.InlineKeyboardMarkup(kb)
    bot.send_message(chat_id=update.message.chat_id,
                     text="Выберите фильтр по событиям:",
                     reply_markup=kb_markup)


if __name__ == '__main__':
    with open('telegram.token', 'r') as tg:
        token = tg.read().strip()

    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_error_handler(error_callback)

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    dispatcher.add_handler(echo_handler)

    token_handler = CommandHandler('token', set_token, pass_args=True)
    dispatcher.add_handler(token_handler)

    top_events_handler = CommandHandler('top', get_top_events, pass_args=True)
    dispatcher.add_handler(top_events_handler)

    set_city_handler = CommandHandler('city', set_city, pass_args=True)
    dispatcher.add_handler(set_city_handler)

    universal_events_handler = CommandHandler("events", events_handler, pass_args=False)
    dispatcher.add_handler(universal_events_handler)

    help_handler = CommandHandler('help', show_help, pass_args=False)
    dispatcher.add_handler(help_handler)

    subscribe_handler = CommandHandler('subscribe', subscribe, pass_args=True)
    dispatcher.add_handler(subscribe_handler)

    dispatcher.add_handler(CallbackQueryHandler(button_more_callback))

    unsubscribe_handler = CommandHandler('unsubscribe', unsubscribe, pass_args=True)
    dispatcher.add_handler(unsubscribe_handler)

    show_subscriptions_handler = CommandHandler('subscriptions', show_subscriptions_handler)
    dispatcher.add_handler(show_subscriptions_handler)

    job_queue.run_repeating(crawl_new_events, interval=3, first=0)

    updater.start_polling()
