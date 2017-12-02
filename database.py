import sqlite3


def get_connection():
    return sqlite3.connect('timepad.db')


class Connector:
    def __init__(self):
        self.connection = get_connection()

    def add_user(self, id, email, token):
        # TODO: catch exceptions
        c = self.connection.cursor()
        c.execute('INSERT INTO users(id, email, token) VALUES ' +
                  '(?, ?, ?)', (id, email, token))


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE users ' +
              '(id INTEGER PRIMARY KEY, email TEXT, token TEXT)')


if __name__ == '__main__':
    init_db()
