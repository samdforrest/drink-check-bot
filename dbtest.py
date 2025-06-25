import sqlite3

try:
    # Connect to database
    conn = sqlite3.connect('drink_check.db')

    # Create a cursor object
    cursor = conn.cursor()

    # Use parameterized query to safely insert data
    user_data = (11343438333, 'test_user_8', 12, 2)
    cursor.execute('''
        INSERT INTO users 
            (user_id, username, total_credits, longest_chain_streak) 
        VALUES 
            (?, ?, ?, ?)
    ''', user_data)

    # Commit the transaction
    conn.commit()

    # Query and print all users
    cursor.execute('SELECT * FROM users')
    results = cursor.fetchall()
    print("Users in database:", results)

except sqlite3.Error as e:
    print(f"Database error occurred: {e}")

finally:
    # Ensure the connection is closed even if an error occurs
    if conn:
        conn.close()

