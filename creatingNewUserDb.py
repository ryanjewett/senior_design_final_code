import sqlite3
from CreatingUserListDb import MainDatabase

class creatingNewUser():

    def __init__(self):
        self.name = None
        self.password = None
        self.linkeddb = None
        
    def setInfo(self,name,password):
        self.name = name
        self.password = password

    def createDB(self):
        try:
            self.conn = sqlite3.connect(f"{self.name}.db")
            self.cur = self.conn.cursor()
            self.cur.execute('PRAGMA foreign_keys = ON')
        except sqlite3.Error as e:
            print(f"Error creating database: {str(e)}")
            raise
    
    def loadDB(self):
        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Date (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            date_id INTEGER,
            FOREIGN KEY (date_id) REFERENCES Date(id)
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Left_Elbow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_id INTEGER,
            x_value REAL NOT NULL,
            y_value REAL NOT NULL,
            z_value REAL NOT NULL,
            FOREIGN KEY (time_id) REFERENCES Time(id)
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Left_Shoulder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_id INTEGER,
            x_value REAL NOT NULL,
            y_value REAL NOT NULL,
            z_value REAL NOT NULL,
            FOREIGN KEY (time_id) REFERENCES Time(id)
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Middle_Back (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_id INTEGER,
            x_value REAL NOT NULL,
            y_value REAL NOT NULL,
            z_value REAL NOT NULL,
            FOREIGN KEY (time_id) REFERENCES Time(id)
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Right_Shoulder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_id INTEGER,
            x_value REAL NOT NULL,
            y_value REAL NOT NULL,
            z_value REAL NOT NULL,
            FOREIGN KEY (time_id) REFERENCES Time(id)
        )
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS Right_Elbow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_id INTEGER,
            x_value REAL NOT NULL,
            y_value REAL NOT NULL,
            z_value REAL NOT NULL,
            FOREIGN KEY (time_id) REFERENCES Time(id)
        )
        ''')
        self.conn.commit()

    def loadIntoMain(self):
        mainUser = MainDatabase()
        mainUser.add_user(self.name,self.password)
        mainUser.close()

    def newuser(self,name,password):
        self.setInfo(name,password)
        self.loadIntoMain()
        self.createDB()
        self.loadDB()
        self.closeConnection()

    def closeConnection(self):
        if self.conn:
            self.conn.close()  
        

