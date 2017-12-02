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

    def get_user_events(self):
        c = self.connection.cursor()
        c.execute('SELECT eventId FROM users_events WHERE userId = ?')
        events = map(lambda row: row[0], c.fetchall())
        return events


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('DROP TABLE IF EXISTS subscriptions')
    c.execute('DROP TABLE IF EXISTS users_events')
    c.execute('DROP TABLE IF EXISTS users')

    c.execute('CREATE TABLE users ' +
              '(id INTEGER PRIMARY KEY, chatId TEXT, email TEXT, token TEXT, introspectTimestamp TIMESTAMP)')
    c.execute('CREATE TABLE users_events ' +
              '(userId INTEGER, eventId INTEGER, PRIMARY KEY(userId, eventId))')
    c.execute('CREATE TABLE subscriptions ' +
              '(userId INTEGER, subscriberId INTEGER, PRIMARY KEY(userId, subscriberId))')


if __name__ == '__main__':
    init_db()
