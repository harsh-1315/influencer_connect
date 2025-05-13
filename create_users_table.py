import sqlite3

# Connect to your database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create the users table
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL  -- 'brand' or 'influencer'
    )
''')

# Save and close
conn.commit()
conn.close()

print("✅ Users table created successfully!")
