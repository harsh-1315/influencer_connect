import re
import sqlite3
from flask import Flask, request, render_template, jsonify
import json

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS influencers 
                 (id INTEGER PRIMARY KEY, name TEXT, niche TEXT, followers INTEGER, platform TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS companies 
                 (id INTEGER PRIMARY KEY, name TEXT, niche TEXT, budget INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns 
                 (id INTEGER PRIMARY KEY, company_id INTEGER, title TEXT, budget INTEGER, status TEXT)''')
    conn.commit()
    conn.close()

# Chatbot logic
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def chatbot_response(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",   # Model name
            messages=[
                {"role": "system", "content": "You are an AI assistant helping brands connect with influencers."},
                {"role": "user", "content": message}
            ]
        )
        reply = response['choices'][0]['message']['content']
        return reply
    except Exception as e:
        print(e)
        return "Sorry, I couldn't connect to the AI server."

# Database functions
def save_influencer(name, niche, followers, platform):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO influencers (name, niche, followers, platform) VALUES (?, ?, ?, ?)", 
              (name, niche, followers, platform))
    conn.commit()
    conn.close()

def save_company(name, niche, budget):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO companies (name, niche, budget) VALUES (?, ?, ?)", 
              (name, niche, budget))
    conn.commit()
    conn.close()

def find_company_matches(influencer_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT niche, followers FROM influencers WHERE id = ?", (influencer_id,))
    influencer = c.fetchone()
    if not influencer:
        return []
    niche, followers = influencer
    # Simple matching: same niche, budget proportional to followers
    c.execute("SELECT id, name, budget FROM companies WHERE niche = ? AND budget >= ?", 
              (niche, followers // 100))
    matches = [{"id": row[0], "name": row[1], "budget": row[2]} for row in c.fetchall()]
    conn.close()
    return matches

def find_influencer_matches(company_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT niche, budget FROM companies WHERE id = ?", (company_id,))
    company = c.fetchone()
    if not company:
        return []
    niche, budget = company
    # Simple matching: same niche, followers proportional to budget
    c.execute("SELECT id, name, followers FROM influencers WHERE niche = ? AND followers <= ?", 
              (niche, budget * 100))
    matches = [{"id": row[0], "name": row[1], "followers": row[2]} for row in c.fetchall()]
    conn.close()
    return matches

# Flask routes
@app.route('/')
def home():
    return render_template('home.html')   # This will show your new home.html

@app.route('/chatbot')
def chatbot():
    return render_template('index.html')  # This will show your old chatbot (index.html)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')

    response = chatbot_response(message)   # ✅ correct

    return jsonify({'response': response})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_type = data.get('user_type')
    name = data.get('name')
    niche = data.get('niche')
    followers_or_budget = data.get('followers_or_budget')
    platform = data.get('platform', None)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if user_type == 'influencer':
        c.execute("INSERT INTO influencers (name, niche, followers, platform) VALUES (?, ?, ?, ?)", 
                  (name, niche, followers_or_budget, platform))
    elif user_type == 'company':
        c.execute("INSERT INTO companies (name, niche, budget) VALUES (?, ?, ?)", 
                  (name, niche, followers_or_budget))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'user_id': user_id, 'message': f'{user_type.capitalize()} registered!'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)