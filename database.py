import sqlite3


def get_connection():
    return sqlite3.connect('timepad.db')


class Connector:
    def __init__(self):
        self.connection = get_connection()

    def add_user(self, id, chat_id, tg_username, email, token, introspect_timestamp):
        # TODO: catch exceptions
        c = self.connection.cursor()
        c.execute('INSERT INTO users(id, chatId, telegramName, email, token, introspectTimestamp) VALUES ' +
                  '(?, ?, ?, ?, ?)', (id, chat_id, tg_username, email, token, introspect_timestamp))

    def get_user_for_crawl(self):
        c = self.connection.cursor()
        c.execute('SELECT id, token FROM users ORDER BY introspectTimestamp LIMIT 1')
        result = c.fetchone()
        if result is not None:
            return {
                'id': result[0],
                'token': result[1]
            }
        return None

    def get_subscribers(self, user_id):
        c = self.connection.cursor()
        c.execute('SELECT subscriberId FROM subscription WHERE userId = ?', user_id)
        result = map(lambda row: row[0], c.fetchall())
        return result

    def get_user_events(self, user_id):
        c = self.connection.cursor()
        c.execute('SELECT eventId FROM users_events WHERE userId = ?', user_id)
        events = map(lambda row: row[0], c.fetchall())
        return events

    def get_user_by_chat_id(self, chat_id):
        c = self.connection.cursor()
        c.execute('SELECT id FROM users WHERE chatId = ?', chat_id)
        result = c.fetchone()
        if result is not None:
            return result[0]
        return None

    def get_user_by_telegram(self, login):
        return None
        c = self.connection.cursor()
        c.execute('SELECT id FROM users WHERE telegramName = ?', login)
        result = c.fetchone()
        if result is not None:
            return result[0]
        return None

    def add_subscription(self, user_id, subscriber_id):
        c = self.connection.cursor()
        c.execute('INSERT INTO subscriptions(userId, subscriberId) ' +
                  'VALUES(?, ?)', (user_id, subscriber_id))

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('DROP TABLE IF EXISTS subscriptions')
    c.execute('DROP TABLE IF EXISTS users_events')
    c.execute('DROP TABLE IF EXISTS users')

    c.execute('CREATE TABLE users ' +
              '(id INTEGER PRIMARY KEY, chatId TEXT, telegramName TEXT,' +
              'email TEXT, token TEXT, introspectTimestamp TIMESTAMP)')
    c.execute('CREATE TABLE users_events ' +
              '(userId INTEGER, eventId INTEGER, PRIMARY KEY(userId, eventId))')
    c.execute('CREATE TABLE subscriptions ' +
              '(userId INTEGER, subscriberId INTEGER, PRIMARY KEY(userId, subscriberId))')


if __name__ == '__main__':
    init_db()
