import sqlite3

class db:
    def __init__(self, db_name: str = "data.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        print(f"Connected to database: {db_name}")

    def execute(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            print(f"Error executing query: {e}")
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()
        print("Database connection closed.")