import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import timepad
import database
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Please, use /token command to set up your token")


def has_token(func):
    def func_wrapper(bot, update, *args, **kwargs):
        connector = database.Connector()
        user = connector.get_user_by_chat_id(update.message.chat_id)
        if user is None:
            bot.send_message(chat_id=update.message.chat_id, text='Set up your token first')
            return
        func(bot, update, *args, **kwargs)

    return func_wrapper


def set_token(bot, update, args):
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id, text="Use /token <your TimePad token>")
        return
    token = args[0]

    data = timepad.introspect(token)
    if data is None:
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, could not get your data. Try again later')
        return
    active = data.get('active', False)
    if not active:
        bot.send_message(chat_id=update.message.chat_id, text='Token is invalid')
        logging.info(repr(data))
        return

    connector = database.Connector()
    last_timestamp = 0
    city = 'Без города'
    connector.add_user(data['user_id'], update.message.chat_id, update.message.from_user.username,
                       data['user_email'], token, city, last_timestamp)
    bot.send_message(chat_id=update.message.chat_id, text='Connected!')


def get_today_events(bot, update):
    connector = database.Connector()
    city = connector.get_user_city(timepad.TIMEPAD_TOKEN)
    events = timepad.get_events_by_date(city)
    bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events))

def get_events_by_token(bot, update):
    connector = database.Connector()
    city = connector.get_user_city(timepad.TIMEPAD_TOKEN)
    events = timepad.get_events_by_token(timepad.TIMEPAD_TOKEN, city)
    bot.send_message(chat_id=update.message.chat_id, text="\n\n".join(events), parse_mode='Markdown')

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def error_callback(bot, update, error):
    logging.warning(repr(error))


def notify_subscribers(bot, user, new_events):
    connector = database.Connector()
    subscribers = connector.get_subscribers(user['id'])
    events = timepad.get_events_data(new_events)

    names = list(map(lambda event: event['name'], events))
    for subscriber_id in subscribers:
        subscriber = connector.get_user_by_id(subscriber_id)
        logging.info('Notifying {}'.format(str(subscriber)))
        bot.send_message(chat_id=subscriber['chat_id'],
                         text='Yoba-Boba, your friend {} just joined this shit: {}'.format(
                             str(user['tg_name']), str(names)))


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

@has_token
def get_top_events(bot, update, args):
    keywords = ','.join(args)
    # top_events = timepad.get_top_events(keywords)
    top_events = []
    bot.send_message(chat_id=update.message.chat_id,
                     text='Here is your top: {}'.format('. '.join(top_events)))


@has_token
def subscribe(bot, update, args):
    connector = database.Connector()
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Use /subscribe <Telegram login>')
        return
    subscribed_to = args[0]
    user_id = connector.get_user_by_chat_id(update.message.chat_id)
    subscribed_id = connector.get_user_by_telegram(subscribed_to)
    if subscribed_id is None:
        bot.send_message(chat_id=update.message.chat_id, text='Unknown user! Ask him to add this bot')
        return
    connector.add_subscription(subscribed_id, user_id)
    bot.send_message(chat_id=update.message.chat_id, text='Subscribed!')



if __name__ == '__main__':
    updater = Updater(token='474743017:AAGBMDsYi0LciJFLT2HB9YOVABV1atOoboM')
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

    top_events_handler = CommandHandler('top', get_top_events, pass_args=True)
    dispatcher.add_handler(top_events_handler)

    subscribe_handler = CommandHandler('subscribe', subscribe, pass_args=True)
    dispatcher.add_handler(subscribe_handler)

    job_queue.run_repeating(crawl_new_events, interval=3, first=0)

    updater.start_polling()
