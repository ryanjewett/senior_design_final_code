import sqlite3

def insert_user(username, password):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('main.db')
        cur = conn.cursor()

        # Create the Users table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                linkeddb TEXT NOT NULL
            )
        ''')

        # Insert the new user into the Users table
        linkeddb = f"{username}.db"  # Assuming linkeddb is based on the username
        cur.execute('''
            INSERT INTO Users (username, password, linkeddb) VALUES (?, ?, ?)
        ''', (username, password, linkeddb))

        # Commit the transaction
        conn.commit()
        print(f"User '{username}' added successfully.")

    except sqlite3.IntegrityError:
        print("Error: Username already exists.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Close the connection
        conn.close()

# Call the function to insert the user
insert_user('test1', 'test1')
