from datetime import datetime
import json
import sqlite3
import utils.logger as logger

class database:
    def __init__(self, db_name: str = "data.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        logger.database_log(f"Connected to database: {db_name}")

    def initialize(self):
        self.execute("DROP TABLE IF EXISTS career;")
        self.execute('''
            CREATE TABLE IF NOT EXISTS voters (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                nick TEXT NOT NULL,
                id INTEGER NOT NULL UNIQUE,
                passphrase TEXT NOT NULL
            );
        ''')
        self.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                nick TEXT NOT NULL,
                avatar_url TEXT,
                id INTEGER NOT NULL UNIQUE,
                number INTEGER DEFAULT 0,
                display_nick TEXT DEFAULT '',
                pledge TEXT DEFAULT '',
                signed_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                joined_time DATETIME NOT NULL,
                resign INTEGER DEFAULT 0
            );
        ''')
        self.execute('''
            CREATE TABLE IF NOT EXISTS secure (
                id INTEGER PRIMARY KEY NOT NULL,
                passphrase TEXT NOT NULL,
                securephrase_pre TEXT NOT NULL,
                securephrase_main TEXT NOT NULL,
                voted INTEGER DEFAULT 0,
                votetime DATETIME DEFAULT NULL,
                used_securephrase TEXT DEFAULT NULL
            );
        ''')
        self.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                valid INTEGER DEFAULT 1
            );
        ''')
        self.execute('''
            CREATE TABLE IF NOT EXISTS career (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                start DATETIME NOT NULL,
                end DATETIME NOT NULL,
                type TEXT NOT NULL
            );
        ''')
        with open("career.json", "r") as fd:
            data = json.load(fd)
        for career in data:
            start = datetime.strptime(career["start"], "%Y-%m-%dT%H:%M:%S+09:00")
            end = datetime.strptime(career["end"], "%Y-%m-%dT%H:%M:%S+09:00")
            self.execute("INSERT INTO career (name, user_id, start, end, type) VALUES (?, ?, ?, ?, ?);",
                         (career["name"], career["user_id"], start, end, career["type"]))
        logger.database_log("Database initialized.")

    def execute(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            logger.error_log(f"Error executing query: {e}")

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()
        logger.database_log("Database connection closed.")

db = database()
db.initialize()