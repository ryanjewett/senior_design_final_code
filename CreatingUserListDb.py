import sqlite3

class MainDatabase:
    def __init__(self, db_name="main.db"):
        self.db_name = db_name
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cur = self.conn.cursor()
        
    def create_user_table(self):
        self.connect()
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                linkeddb TEXT NOT NULL
            )
        ''')
        self.conn.commit()
        self.close()

    def add_user(self, username, password):
        linkeddb = f"{username}.db"
        self.connect()
        try:
            self.cur.execute('INSERT INTO Users (username, password, linkeddb) VALUES (?, ?, ?)', 
                             (username, password, linkeddb))
            self.conn.commit()
        except sqlite3.IntegrityError:
            print("Username already exists.")
        finally:
            self.close()

    def close(self):
        if self.conn:
            self.conn.close()


