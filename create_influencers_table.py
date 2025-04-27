import sqlite3

# Connect to your database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create the influencers table
c.execute('''
    CREATE TABLE influencers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        niche TEXT NOT NULL,
        platform TEXT,
        followers INTEGER,
        description TEXT
    )
''')

# Save and close
conn.commit()
conn.close()

print("Influencers table created successfully!")
