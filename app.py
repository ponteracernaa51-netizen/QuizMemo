import os
import pandas as pd
import random
import string
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import supabase
from sm2 import calculate_sm2
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET")

@app.route('/')
def index():
    if session.get('user'): return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    password = request.form.get('password')
    action = request.form.get('action')

    if action == 'register':
        hp = generate_password_hash(password)
        res = supabase.table('users').insert({"email": email, "password_hash": hp}).execute()
        if not res.data: return "Registration Error", 400
        user = res.data[0]
    else:
        res = supabase.table('users').select("*").eq("email", email).execute()
        if not res.data or not check_password_hash(res.data[0]['password_hash'], password):
            return "Invalid email or password", 401
        user = res.data[0]

    session['user'] = user
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user'): return redirect('/')
    user_id = session['user']['id']
    now = datetime.now()

    # 1. Get all decks
    my_decks_raw = supabase.table('decks').select("*").eq("created_by", user_id).execute().data or []
    joined_res = supabase.table('deck_access').select("decks(*)").eq("user_id", user_id).execute().data or []
    
    # Merge decks
    decks_dict = {d['id']: d for d in my_decks_raw}
    for item in joined_res:
        if item.get('decks'):
            d = item['decks']
            if d['id'] not in decks_dict:
                decks_dict[d['id']] = d

    all_decks = list(decks_dict.values())

    # 2. Calculate stats
    for deck in all_decks:
        questions = supabase.table('questions').select("id").eq("deck_id", deck['id']).execute().data or []
        q_ids = [q['id'] for q in questions]
        
        if not q_ids:
            deck['stats'] = {'new': 0, 'red': 0, 'green': 0}
            continue

        progress = supabase.table('user_progress').select("*").eq("user_id", user_id).in_("question_id", q_ids).execute().data or []
        prog_dict = {p['question_id']: p for p in progress}

        n, r, g = 0, 0, 0
        for q_id in q_ids:
            p = prog_dict.get(q_id)
            if not p: n += 1
            else:
                next_rev = datetime.fromisoformat(p['next_review'].replace('Z', '+00:00')).replace(tzinfo=None)
                if next_rev <= now:
                    if p['interval'] == 0: r += 1
                    else: g += 1
        
        deck['stats'] = {'new': n, 'red': r, 'green': g}

    return render_template('dashboard.html', decks=all_decks)

# --- ROUTES ---

@app.route('/deck/<int:deck_id>/rename', methods=['POST'])
def rename_deck(deck_id):
    user_id = session['user']['id']
    new_title = request.form.get('title')
    supabase.table('decks').update({"title": new_title}).eq("id", deck_id).eq("created_by", user_id).execute()
    return redirect('/dashboard')

@app.route('/deck/<int:deck_id>/delete', methods=['POST'])
def delete_or_leave_deck(deck_id):
    user_id = session['user']['id']
    deck = supabase.table('decks').select("created_by").eq("id", deck_id).execute().data
    
    if deck and deck[0]['created_by'] == user_id:
        supabase.table('decks').delete().eq("id", deck_id).execute()
    else:
        supabase.table('deck_access').delete().eq("user_id", user_id).eq("deck_id", deck_id).execute()
    
    return redirect('/dashboard')

@app.route('/deck/<int:deck_id>/study_more', methods=['POST'])
def study_more(deck_id):
    user_id = session['user']['id']
    questions = supabase.table('questions').select("id").eq("deck_id", deck_id).execute().data or []
    q_ids = [q['id'] for q in questions]
    
    if q_ids:
        future_limit = datetime.now() + timedelta(days=7)
        supabase.table('user_progress')\
            .update({"next_review": datetime.now().isoformat()})\
            .eq("user_id", user_id)\
            .in_("question_id", q_ids)\
            .lte("next_review", future_limit.isoformat())\
            .gt("next_review", datetime.now().isoformat())\
            .execute()
    
    return redirect(f'/study/{deck_id}')

@app.route('/upload', methods=['POST'])
def upload():
    user_id = session['user']['id']
    title = request.form.get('title')
    file = request.files['file']
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    deck = supabase.table('decks').insert({"title": title, "access_code": code, "created_by": user_id}).execute().data[0]
    
    df = pd.read_excel(file)
    questions = []
    
    # Detect Type
    is_quiz = 'Option1' in df.columns
    
    for _, row in df.iterrows():
        q_data = {
            "deck_id": deck['id'],
            "question_text": str(row['Question']),
            "correct_answer": str(row['CorrectAnswer'])
        }
        
        if is_quiz:
            q_data["options"] = [
                str(row.get('Option1', '')), 
                str(row.get('Option2', '')), 
                str(row.get('Option3', '')), 
                str(row.get('Option4', ''))
            ]
        else:
            q_data["options"] = [] # Empty list for Flashcard mode
            
        questions.append(q_data)
        
    supabase.table('questions').insert(questions).execute()
    return redirect('/dashboard')

@app.route('/join', methods=['POST'])
def join_deck():
    user_id = session['user']['id']
    code = request.form.get('code')
    deck = supabase.table('decks').select("*").eq("access_code", code).execute().data
    if deck:
        supabase.table('deck_access').insert({"user_id": user_id, "deck_id": deck[0]['id']}).execute()
    return redirect('/dashboard')

@app.route('/study/<int:deck_id>')
def study(deck_id):
    if not session.get('user'): return redirect('/')
    return render_template('study.html', deck_id=deck_id)

@app.route('/api/cards/<int:deck_id>')
def get_cards(deck_id):
    if not session.get('user'): return jsonify([])
    user_id = session['user']['id']
    now = datetime.now()
    
    all_q = supabase.table('questions').select("*").eq("deck_id", deck_id).execute().data
    progress = supabase.table('user_progress').select("*").eq("user_id", user_id).execute().data
    prog_dict = {p['question_id']: p for p in progress}

    red_cards = []
    other_cards = []

    for q in all_q:
        p = prog_dict.get(q['id'])
        q['current_progress'] = p if p else {"interval": 0, "repetitions": 0, "ease_factor": 2.5}
        
        if not p:
            other_cards.append(q)
        else:
            next_rev = datetime.fromisoformat(p['next_review'].replace('Z', '+00:00')).replace(tzinfo=None)
            if next_rev <= now:
                if p['interval'] == 0:
                    red_cards.append(q)
                else:
                    other_cards.append(q)
    
    random.shuffle(other_cards)
    study_list = red_cards + other_cards
    
    return jsonify(study_list)

@app.route('/api/rate', methods=['POST'])
def rate():
    data = request.json
    user_id = session['user']['id']
    res = supabase.table('user_progress').select("*").eq("user_id", user_id).eq("question_id", data['card_id']).execute().data
    
    if not res:
        i, ef, r, d = calculate_sm2(data['rating'], 0, 2.5, 0)
        supabase.table('user_progress').insert({"user_id": user_id, "question_id": data['card_id'], "interval": i, "ease_factor": ef, "repetitions": r, "next_review": d.isoformat()}).execute()
    else:
        p = res[0]
        i, ef, r, d = calculate_sm2(data['rating'], p['interval'], p['ease_factor'], p['repetitions'])
        supabase.table('user_progress').update({"interval": i, "ease_factor": ef, "repetitions": r, "next_review": d.isoformat()}).eq("user_id", user_id).eq("question_id", data['card_id']).execute()
    return jsonify({"ok": True})

@app.route('/api/deck/<int:deck_id>/stats')
def get_custom_stats(deck_id):
    user_id = session['user']['id']
    now = datetime.now()
    
    questions = supabase.table('questions').select("id").eq("deck_id", deck_id).execute().data or []
    q_ids = [q['id'] for q in questions]
    
    progress = supabase.table('user_progress').select("*").eq("user_id", user_id).in_("question_id", q_ids).execute().data or []
    prog_dict = {p['question_id']: p for p in progress}
    
    stats = {'new': 0, 'forgotten': 0, 'total': len(q_ids)}
    
    for q_id in q_ids:
        p = prog_dict.get(q_id)
        if not p:
            stats['new'] += 1
        elif p['interval'] == 0:
            stats['forgotten'] += 1
            
    return jsonify(stats)

@app.route('/api/deck/<int:deck_id>/apply_custom', methods=['POST'])
def apply_custom(deck_id):
    user_id = session['user']['id']
    data = request.json
    action = data.get('action')
    count = int(data.get('count', 10))
    now_iso = datetime.now().isoformat()

    questions = supabase.table('questions').select("id").eq("deck_id", deck_id).execute().data or []
    all_q_ids = [q['id'] for q in questions]

    if action == 'add_new':
        progress = supabase.table('user_progress').select("question_id").eq("user_id", user_id).execute().data or []
        existing = [p['question_id'] for p in progress]
        to_add = [qid for qid in all_q_ids if qid not in existing][:count]
        for qid in to_add:
            supabase.table('user_progress').insert({"user_id": user_id, "question_id": qid, "next_review": now_iso, "interval": 0}).execute()

    elif action == 'forgotten' or action == 'preview':
        query = supabase.table('user_progress').select("question_id").eq("user_id", user_id).in_("question_id", all_q_ids)
        if action == 'forgotten':
            query = query.eq("interval", 0)
        
        target_ids = [r['question_id'] for r in query.execute().data or []][:count]
        if target_ids:
            supabase.table('user_progress').update({"next_review": now_iso}).in_("question_id", target_ids).eq("user_id", user_id).execute()

    return jsonify({"status": "ok"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- CARD EDITOR ROUTES ---

@app.route('/deck/<int:deck_id>/edit')
def edit_deck_page(deck_id):
    if not session.get('user'): return redirect('/')
    user_id = session['user']['id']
    deck = supabase.table('decks').select("*").eq("id", deck_id).eq("created_by", user_id).execute().data
    if not deck: return redirect('/dashboard')
    
    return render_template('edit_deck.html', deck=deck[0])

@app.route('/api/deck/<int:deck_id>/all_cards')
def get_all_cards_for_edit(deck_id):
    if not session.get('user'): return jsonify([])
    cards = supabase.table('questions').select("*").eq("deck_id", deck_id).order('id').execute().data
    return jsonify(cards)

@app.route('/api/card/add', methods=['POST'])
def add_card():
    if not session.get('user'): return "Unauthorized", 401
    data = request.json
    
    new_card = {
        "deck_id": data['deck_id'],
        "question_text": data['question'],
        "correct_answer": data['answer'],
        "options": ["nan", "nan", "nan", "nan"]
    }
    res = supabase.table('questions').insert(new_card).execute()
    return jsonify(res.data[0])

@app.route('/api/card/update', methods=['POST'])
def update_card():
    if not session.get('user'): return "Unauthorized", 401
    data = request.json
    
    update_data = {
        "question_text": data['question'],
        "correct_answer": data['answer']
    }
    res = supabase.table('questions').update(update_data).eq("id", data['id']).execute()
    return jsonify(res.data[0])

@app.route('/api/card/delete', methods=['POST'])
def delete_card():
    if not session.get('user'): return "Unauthorized", 401
    data = request.json
    supabase.table('user_progress').delete().eq("question_id", data['id']).execute()
    supabase.table('questions').delete().eq("id", data['id']).execute()
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(debug=True)