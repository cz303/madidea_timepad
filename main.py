import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def set_token(bot, update, args):
    logging.info('Got args {} from {}'.format(repr(args), update.message.chat_id))
    if len(args) != 1:
        bot.send_message(chat_id=update.message.chat_id, text="Use /token <your TimePad token>")
        return
    token = args[0]


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


if __name__ == '__main__':
    updater = Updater(token='474743017:AAGBMDsYi0LciJFLT2HB9YOVABV1atOoboM')
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    dispatcher.add_handler(echo_handler)

    token_handler = CommandHandler('token', set_token, pass_args=True)
    dispatcher.add_handler(token_handler)

    updater.start_polling()
