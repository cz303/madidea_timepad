import sqlite3


def get_connection():
    return sqlite3.connect('timepad.db')


class Connector:
    def __init__(self):
        self.connection = get_connection()

    def add_user(self, id, chat_id, email, token, introspect_timestamp):
        # TODO: catch exceptions
        c = self.connection.cursor()
        c.execute('INSERT INTO users(id, chatId, email, token, introspectTimestamp) VALUES ' +
                  '(?, ?, ?, ?, ?)', (id, chat_id, email, token, introspect_timestamp))


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('DROP TABLE IF EXISTS users_events')
    c.execute('DROP TABLE IF EXISTS users')

    c.execute('CREATE TABLE users ' +
              '(id INTEGER PRIMARY KEY, chatId TEXT, email TEXT, token TEXT, introspectTimestamp TIMESTAMP)')
    c.execute('CREATE TABLE users_events ' +
              '(userId INTEGER, eventId INTEGER, PRIMARY KEY(userId, eventId))')


if __name__ == '__main__':
    init_db()
