import re
import sqlite3
from flask import Flask, request, render_template, jsonify, redirect
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

app = Flask(__name__)

session_state = {}  # <<< ✅ ADD IT RIGHT HERE!

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, email TEXT, password TEXT, user_type TEXT)''')
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
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": message}]
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
@app.route('/register-brand', methods=['GET', 'POST'])
def register_brand():
    if request.method == 'POST':
        name = request.form['name']
        niche = request.form['niche']
        budget = request.form['budget']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (email, password, user_type) VALUES (?, ?, ?)', 
                  (email, hashed_password, 'brand'))
        conn.commit()

        # Store brand data in the 'companies' table
        c.execute('INSERT INTO companies (name, niche, budget) VALUES (?, ?, ?)', 
                  (name, niche, budget))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register_brand.html')

@app.route('/register-influencer', methods=['GET', 'POST'])
def register_influencer():
    if request.method == 'POST':
        name = request.form['name']
        niche = request.form['niche']
        followers = request.form['followers']
        platform = request.form['platform']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (email, password, user_type) VALUES (?, ?, ?)', 
                  (email, hashed_password, 'influencer'))
        conn.commit()

        # Store influencer data in the 'influencers' table
        c.execute('INSERT INTO influencers (name, niche, followers, platform) VALUES (?, ?, ?, ?)', 
                  (name, niche, followers, platform))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register_influencer.html')


@app.route('/')
def home():
    return render_template('home.html')   # This will show your new home.html

@app.route('/chatbot')
def chatbot():
    return render_template('index.html')  # This will show your old chatbot (index.html)

# Add this at the top of your app.py

# At top of app.py

@app.route('/chat', methods=['POST'])
def chat():
    global session_state
    data = request.get_json()
    message = data.get('message')

    greetings = ["hi", "hello", "hey", "good morning", "good afternoon"]
    if message.lower().strip() in greetings:
        session_state.clear()
        return jsonify({'response': "👋 Hello! Welcome to BrandConnect! Are you a Brand or an Influencer?"})

    influencer_keywords = ["followers", "following", "stats", "audience", "about"]
    influencer_name = None

    for keyword in influencer_keywords:
        if keyword in message.lower():
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

    if 'user_type' not in session_state:
        if message.lower() in ["brand", "influencer"]:
            session_state['user_type'] = message.lower()
            return jsonify({'response': "Great! What niche are you targeting? (Fitness, Beauty, Tech, Fashion)"})
        else:
            return jsonify({'response': "Please reply 'Brand' or 'Influencer' to continue."})

    if 'niche' not in session_state:
        session_state['niche'] = message
        if session_state['user_type'] == 'brand':
            return jsonify({'response': "Awesome! Which platform are you looking for? (Instagram, YouTube, TikTok)"})
        else:
            return jsonify({'response': "Awesome! What's your follower count on your main platform?"})

    if session_state['user_type'] == 'brand' and 'platform' not in session_state:
        session_state['platform'] = message
        return jsonify({'response': "What's your estimated budget in dollars?"})

    if session_state['user_type'] == 'brand' and 'budget' not in session_state:
        try:
            session_state['budget'] = int(message)
        except ValueError:
            return jsonify({'response': "Please enter your budget as a number (e.g., 5000)."})

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        niche = session_state['niche']
        platform = session_state['platform']
        budget = session_state['budget']

        expected_followers_low = budget * 8
        expected_followers_high = budget * 12

        c.execute(""" 
            SELECT name, followers, platform 
            FROM influencers 
            WHERE LOWER(niche) = LOWER(?) 
              AND LOWER(platform) = LOWER(?) 
              AND followers BETWEEN ? AND ?
        """, (niche.lower(), platform.lower(), expected_followers_low, expected_followers_high))

        matches = c.fetchall()
        conn.close()

        if matches:
            reply = "🎯 Here are some influencers matching your brand's needs:\n"
            for match in matches:
                reply += f"- {match[0]} ({match[1]} followers on {match[2]})\n"
        else:
            reply = "😔 Sorry, no perfect influencer matches found."

        session_state.clear()
        return jsonify({'response': reply})

    if session_state['user_type'] == 'influencer' and 'followers' not in session_state:
        try:
            session_state['followers'] = int(message)
        except ValueError:
            return jsonify({'response': "Please enter your follower count as a number (e.g., 10000)."})

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        niche = session_state['niche']
        followers = session_state['followers']
        min_budget = followers // 100

        c.execute("""
            SELECT name, budget 
            FROM companies 
            WHERE LOWER(niche) = LOWER(?) 
              AND budget >= ?
        """, (niche.lower(), min_budget))

        matches = c.fetchall()
        conn.close()

        if matches:
            reply = "🎯 Here are some brands you could work with:\n"
            for match in matches:
                reply += f"- {match[0]} (Budget: ${match[1]})\n"
        else:
            reply = "😔 Sorry, no brands match your profile yet."

        session_state.clear()
        return jsonify({'response': reply})

    response = "👋 Hello! Let's start again — are you a Brand or an Influencer?"
    session_state.clear()
    return jsonify({'response': response})

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id, password, user_type FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['user_type'] = user[2]
            return redirect('/dashboard')  # Create this later
        else:
            return "Invalid credentials. Try again."

    return render_template('login.html')

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    user_type = session['user_type']

    if user_type == 'brand':
        # Show the brand's dashboard (e.g., campaigns, matches with influencers)
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT title, budget, status FROM campaigns WHERE company_id = ?", (user_id,))
        campaigns = c.fetchall()
        conn.close()
        return render_template('brand_dashboard.html', campaigns=campaigns)

    elif user_type == 'influencer':
        # Show the influencer's dashboard (e.g., their profile, matches with brands)
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT name, niche, followers, platform FROM influencers WHERE id = ?", (user_id,))
        influencer = c.fetchone()
        conn.close()
        return render_template('influencer_dashboard.html', influencer=influencer)

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Success Function
if __name__ == '__main__':
    init_db()
    app.secret_key = os.urandom(24)
    app.run(debug=True)
