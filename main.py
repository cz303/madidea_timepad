import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import timepad
import database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Please, use /token command to set up your token")


def set_token(bot, update, args):
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id, text="Use /token <your TimePad token>")
        return
    token = args[0]

    data = timepad.introspect(token)
    if data is None:
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, could not get your data. Try again later')
        return

    if not data['active']:
        bot.send_message(chat_id=update.message.chat_id, text='Token is invalid')
        logging.info(repr(data))
        return

    connector = database.Connector()
    connector.add_user(data['user_id'], data['user_email'], token)
    bot.send_message(chat_id=update.message.chat_id, text="Here's your data: {}".format(repr(data)))


def get_today_events(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Got it!")
    data = timepad.get_events_by_date()
    bot.send_message(chat_id=update.message.chat_id, text=str(data))

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)

def error_callback(bot, update, error):
    logging.warning(repr(error))

if __name__ == '__main__':
    updater = Updater(token='474743017:AAGBMDsYi0LciJFLT2HB9YOVABV1atOoboM')
    dispatcher = updater.dispatcher

    dispatcher.add_error_handler(error_callback)

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    dispatcher.add_handler(echo_handler)

    token_handler = CommandHandler('token', set_token, pass_args=True)
    dispatcher.add_handler(token_handler)

    today_events_handler = CommandHandler('today', get_today_events, pass_args=False)
    dispatcher.add_handler(today_events_handler)

    updater.start_polling()
