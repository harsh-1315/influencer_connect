import re
import sqlite3
from flask import Flask, request, render_template, jsonify, redirect, session
import json
from werkzeug.security import generate_password_hash, check_password_hash
import os
import openai

# Initialize Flask app
app = Flask(__name__)

# Session management - storing session data
session_state = {}

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, email TEXT, password TEXT, user_type TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS influencers 
                 (id INTEGER PRIMARY KEY, name TEXT, niche TEXT, followers INTEGER, platform TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS companies 
                 (id INTEGER PRIMARY KEY, name TEXT, niche TEXT, budget INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns 
                 (id INTEGER PRIMARY KEY, company_id INTEGER, title TEXT, budget INTEGER, status TEXT)''')
    conn.commit()
    conn.close()

# Chatbot logic
openai.api_key = os.getenv("TOGETHER_API_KEY")
openai.api_base = "https://api.together.xyz"

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

# Database functions for saving users and brand/influencer data
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

# Flask Routes for Registration and Login
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
        c.execute('INSERT INTO users (email, password, user_type, name) VALUES (?, ?, ?, ?)', 
                  (email, hashed_password, 'brand', name))
        conn.commit()

        # Store brand data in the 'companies' table
        c.execute('INSERT INTO companies (name, niche, budget) VALUES (?, ?, ?)', 
                  (name, niche, budget))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register_brand.html')
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect('/login')

    user_type = session['user_type']

    if user_type == 'brand':
        return render_template('home_brand.html')  # Create this file for Brand homepage

    elif user_type == 'influencer':
        return render_template('home_influencer.html')  # Create this file for Influencer homepage

    return redirect('/')

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
        c.execute('INSERT INTO users (email, password, user_type, name) VALUES (?, ?, ?, ?)', 
                  (email, hashed_password, 'influencer', name))
        conn.commit()

        # Store influencer data in the 'influencers' table
        c.execute('INSERT INTO influencers (name, niche, followers, platform) VALUES (?, ?, ?, ?)', 
                  (name, niche, followers, platform))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register_influencer.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id, password, user_type, name FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['user_type'] = user[2]
            session['user_name'] = user[3]  # Store user's name in session
            return redirect('/dashboard')

        else:
            return "Invalid credentials. Try again."

    return render_template('login.html')

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

# Campaign Routes
@app.route('/create-campaign', methods=['GET', 'POST'])
def create_campaign():
    if 'user_id' not in session or session['user_type'] != 'brand':
        return redirect('/login')
    
    if request.method == 'POST':
        title = request.form['title']
        budget = request.form['budget']
        status = request.form['status']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO campaigns (company_id, title, budget, status) VALUES (?, ?, ?, ?)",
                  (session['user_id'], title, budget, status))
        conn.commit()
        conn.close()
        
        return redirect('/dashboard')
    
    return render_template('create_campaign.html')

# Initialize and run the Flask application
if __name__ == '__main__':
    init_db()
    app.secret_key = os.urandom(24)
    app.run(debug=True)
