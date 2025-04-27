import re
import sqlite3
from flask import Flask, request, render_template, jsonify, redirect
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

# Set Together API key and API base
openai.api_key = os.getenv("TOGETHER_API_KEY")
openai.api_base = "https://api.together.xyz"    # THIS is important!

def chatbot_response(message):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        niche = None

        if "fitness" in message.lower():
            niche = "Fitness"
        elif "beauty" in message.lower():
            niche = "Beauty"
        elif "tech" in message.lower() or "technology" in message.lower():
            niche = "Tech"
        elif "fashion" in message.lower():
            niche = "Fashion"

        if niche:
            if "brand" not in message.lower():
                c.execute('SELECT name FROM companies WHERE niche = ?', (niche,))
                results = c.fetchall()
                brands = [r[0] for r in results]
                if brands:
                    brand_list = ", ".join(brands)
                    prompt = f"""You are an AI chatbot helping influencers find brands for partnerships.
ONLY recommend from these available brands: {brand_list}.
DO NOT invent any other brands outside this list.
Be friendly, short, and professional."""
                else:
                    prompt = "There are currently no brands available in this niche. Please apologize politely."
            else:
                c.execute('SELECT name FROM influencers WHERE niche = ?', (niche,))
                results = c.fetchall()
                influencers = [r[0] for r in results]
                if influencers:
                    influencer_list = ", ".join(influencers)
                    prompt = f"""You are an AI chatbot helping brands find influencers.
ONLY recommend from these available influencers: {influencer_list}.
DO NOT invent any other influencers outside this list.
Be friendly, short, and professional."""
                else:
                    prompt = "There are currently no influencers available in this niche. Please apologize politely."
        else:
            prompt = "You are an AI chatbot connecting brands and influencers. Greet the user and ask if they are a brand or an influencer."

        conn.close()

        response = openai.ChatCompletion.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ]
        )
        reply = response['choices'][0]['message']['content']
        return reply

    except Exception as e:
        print(e)
        return f"Error: {e}"


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

    influencer_keywords = ["followers", "following", "stats", "audience", "about"]
    influencer_name = None

    # Improved detection
    for keyword in influencer_keywords:
        if keyword in message.lower():
            # Try to extract name near the keyword
            pattern = fr'{keyword}\s*(?:does)?\s*(?P<name>\w+)|(?P<name2>\w+)\s*{keyword}'
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                influencer_name = match.group('name') or match.group('name2')
                break

    if influencer_name:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT name, followers, platform FROM influencers WHERE LOWER(name) = LOWER(?)", (influencer_name.lower(),))
        influencer = c.fetchone()
        conn.close()

        if influencer:
            influencer_name_db, followers, platform = influencer
            response = f"{influencer_name_db} has {followers} followers on {platform}."
            return jsonify({'response': response})
        else:
            fallback_message = f"Sorry, I couldn't find {influencer_name} in my database."
            return jsonify({'response': fallback_message})

    # If not about an influencer, continue with normal chatbot
    response = chatbot_response(message)
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

@app.route('/register-brand', methods=['GET', 'POST'])
def register_brand():
    if request.method == 'POST':
        name = request.form['name']
        niche = request.form['niche']
        budget = int(request.form['budget'])   # 🔥 Force integer

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO companies (name, niche, budget) VALUES (?, ?, ?)', 
                  (name, niche, budget))
        conn.commit()
        conn.close()

        return redirect('/')
    return render_template('register_brand.html')

@app.route('/register-influencer', methods=['GET', 'POST'])
def register_influencer():
    if request.method == 'POST':
        name = request.form['name']
        niche = request.form['niche']
        platform = request.form['platform']
        followers = request.form['followers']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO influencers (name, niche, followers, platform) VALUES (?, ?, ?, ?)', 
                  (name, niche, followers, platform))
        conn.commit()
        conn.close()

        return redirect('/')
    return render_template('register_influencer.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)