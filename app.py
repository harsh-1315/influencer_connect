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
def chatbot_response(message, user_type=None, user_id=None):
    message = message.lower().strip()
    
    # Onboarding responses
    if re.search(r"hi|hello|start", message):
        return "Welcome! Are you an influencer or a company? Type 'influencer' or 'company' to begin."
    
    if re.search(r"influencer", message):
        return "Great! What's your name, niche (e.g., fitness, beauty), platform (e.g., Instagram), and follower count?"
    
    if re.search(r"company", message):
        return "Awesome! What's your company name, niche (e.g., fitness, beauty), and campaign budget?"
    
    # Profile creation (basic parsing)
    if re.search(r"name|niche|followers|platform|budget", message) and user_type:
        if user_type == "influencer":
            try:
                parts = message.split(",")
                name = parts[0].split("name")[-1].strip()
                niche = parts[1].split("niche")[-1].strip()
                platform = parts[2].split("platform")[-1].strip()
                followers = int(parts[3].split("followers")[-1].strip())
                save_influencer(name, niche, followers, platform)
                return f"Profile created for {name}! Want to find brand matches? Type 'match'."
            except:
                return "Please provide: name, niche, platform, followers (e.g., 'name: Alex, niche: fitness, platform: Instagram, followers: 10000')."
        elif user_type == "company":
            try:
                parts = message.split(",")
                name = parts[0].split("name")[-1].strip()
                niche = parts[1].split("niche")[-1].strip()
                budget = int(parts[2].split("budget")[-1].strip())
                save_company(name, niche, budget)
                return f"Profile created for {name}! Want to find influencers? Type 'match'."
            except:
                return "Please provide: name, niche, budget (e.g., 'name: BrandX, niche: fitness, budget: 1000')."
    
    # Matching logic
    if re.search(r"match", message) and user_id:
        if user_type == "influencer":
            matches = find_company_matches(user_id)
            if matches:
                return f"Found matches: {', '.join([m['name'] + ' ($' + str(m['budget']) + ')' for m in matches])}. Want to contact one? Type 'contact [name]'."
            return "No matches yet. Try updating your profile or check back later!"
        elif user_type == "company":
            matches = find_influencer_matches(user_id)
            if matches:
                return f"Found matches: {', '.join([m['name'] + ' (' + str(m['followers']) + ' followers)' for m in matches])}. Want to contact one? Type 'contact [name]'."
            return "No matches yet. Try updating your profile or check back later!"
    
    # Contact initiation
    if re.search(r"contact", message):
        contact_name = message.split("contact")[-1].strip()
        return f"Connecting you with {contact_name}. Proposed deal: $500 for a post. Reply 'accept' or 'counter [amount]' to proceed."
    
    # Negotiation
    if re.search(r"accept", message):
        return "Deal accepted! Campaign started. Check your dashboard for details."
    if re.search(r"counter", message):
        try:
            amount = re.search(r"\d+", message).group()
            return f"Countered with ${amount}. Waiting for response from the other party."
        except:
            return "Please specify an amount (e.g., 'counter 600')."
    
    return "Sorry, I didn't understand. Try 'start', 'match', or 'contact [name]'."

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
    data = request.json
    message = data.get('message', '')
    user_type = data.get('user_type', None)
    user_id = data.get('user_id', None)
    response = chatbot_response(message, user_type, user_id)
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