import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
import timepad
import database
from datetime import datetime
import telegram

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

MAX_EVENTS_IN_MSG = 4

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


def get_today_events(bot, update):
    try:
        min_index, date = user_last_queries[update.message.chat_id]
    except KeyError:
        min_index, date = 0, datetime.today().strftime('%Y-%m-%d')
        user_last_queries[update.message.chat_id] = (min_index, date)

    connector = database.Connector()
    city = connector.get_city(timepad.TIMEPAD_TOKEN)  # FIXIT
    events = timepad.get_events_by_date(min_index, date, city)
    if len(events) - min_index > MAX_EVENTS_IN_MSG:
        kb = [[ telegram.InlineKeyboardButton("Да, ещё!", callback_data="ещё") ]]
        kb_markup = telegram.InlineKeyboardMarkup(kb)
        bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events[:MAX_EVENTS_IN_MSG]), parse_mode='Markdown')
        left = len(events) - MAX_EVENTS_IN_MSG - min_index
        text = "Мы показали не все события по этому запросу. Осталось {}. Показать ещё {}?".format(left, min(left, MAX_EVENTS_IN_MSG))
        bot.send_message(chat_id=update.message.chat_id,
                         text=text,
                         reply_markup=kb_markup)
        user_last_queries[update.message.chat_id] = (min_index + MAX_EVENTS_IN_MSG, date)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events[min_index:]), parse_mode='Markdown')
        user_last_queries.pop(update.message.chat_id, None)


@has_token
def get_events_by_token(bot, update):
    connector = database.Connector()
    events = timepad.get_events_by_token(timepad.TIMEPAD_TOKEN, '') 
    bot.send_message(chat_id=update.message.chat_id, text='Твои события:\n' + "\n\n".join(events), parse_mode='Markdown')

@has_token
def get_events_by_city(bot, update):
    connector = database.Connector()
    city = connector.get_city(timepad.TIMEPAD_TOKEN)  # FIXIT
    events = []# timepad.get_events_by_token(timepad.TIMEPAD_TOKEN, city)  
    bot.send_message(chat_id=update.message.chat_id, text='Все события в {0}:\n Нихуя пока что'.format(city) + "\n\n".join(events), parse_mode='Markdown')

@has_token
def get_events_by_city_and_token(bot, update):
    connector = database.Connector()
    city = connector.get_city(timepad.TIMEPAD_TOKEN)  # FIXIT
    events = timepad.get_events_by_token(timepad.TIMEPAD_TOKEN, city)  
    bot.send_message(chat_id=update.message.chat_id, text='Твои события в {0}:\n'.format(city) + "\n\n".join(events), parse_mode='Markdown')


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
    if "ещё" not in query.data:
        pass
        print(query.data)
    else:
        update.message = query.message
        get_today_events(bot, update)

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


if __name__ == '__main__':
    with open('telegram.token', 'r') as tg:
        token = tg.read()

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

    today_events_handler = CommandHandler('today', get_today_events, pass_args=False)
    dispatcher.add_handler(today_events_handler)

    events_by_token_handler = CommandHandler('my_events', get_events_by_token, pass_args=False)
    dispatcher.add_handler(events_by_token_handler)

    events_by_city_handler = CommandHandler('local_events', get_events_by_city, pass_args=False)
    dispatcher.add_handler(events_by_city_handler)

    events_by_city_and_token_handler = CommandHandler('my_local_events', get_events_by_city_and_token, pass_args=False)
    dispatcher.add_handler(events_by_city_and_token_handler)

    top_events_handler = CommandHandler('top', get_top_events, pass_args=True)
    dispatcher.add_handler(top_events_handler)

    set_city_handler = CommandHandler('city', set_city, pass_args=True)
    dispatcher.add_handler(set_city_handler)

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
