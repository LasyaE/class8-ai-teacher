from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import json
import requests
import time
from werkzeug.security import generate_password_hash, check_password_hash
import math
from collections import defaultdict

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')

if not app.config['SECRET_KEY']:
    raise RuntimeError("FLASK_SECRET_KEY environment variable is required")

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
        return User.query.get(user_id)
    except:
        return None

# Initialize database
with app.app_context():
    db.create_all()

# Ollama configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:500a1f067a9f')
OLLAMA_TIMEOUT = 30  # seconds

# Build index for a subject
def build_index(subject):
    text_dir = f"C:\Projects\class8-ai-teacher\data\extracted\raw\{subject}"
    if not os.path.exists(text_dir):
        return None, None, None, 0

    index = defaultdict(lambda: {'count': 0, 'total': 0})  # term -> count (docs with term), total (term occurrences)
    doc_term_freqs = []  # list of dictionaries: {term: freq, ...} for each document
    doc_lengths = []  # document lengths
    total_docs = 0

    text_files = [f for f in os.listdir(text_dir) if f.endswith('.txt')]

    for file in text_files:
        file_path = os.path.join(text_dir, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            words = content.split()
            doc_length = len(words)
            doc_lengths.append(doc_length)
            total_docs += 1

            term_freq = {}
            for word in words:
                term_freq[word] = term_freq.get(word, 0) + 1
            doc_term_freqs.append(term_freq)

            for word in term_freq:
                index[word]['count'] += 1  # Increment count if the term is present in the document
                index[word]['total'] += term_freq[word]  # Total occurrences in the document

    return index, doc_term_freqs, doc_lengths, total_docs

# Retrieve textbook content for a subject
def get_subject_text(subject):
    text_dir = f"C:\Projects\class8-ai-teacher\data\extracted\raw\{subject}"
    if not os.path.exists(text_dir):
        return []

    index, doc_term_freqs, doc_lengths, total_docs = build_index(subject)

    text_files = [f for f in os.listdir(text_dir) if f.endswith('.txt')]

    results = []
    for file in text_files:
        file_path = os.path.join(text_dir, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            words = content.split()
            doc_length = len(words)

            # Calculate BM25 score for the query
            score = 0
            for term in request.args.get('question', '').split():
                if term in index:
                    doc_freq = index[term]['count']
                    term_freq = doc_term_freqs[text_files.index(file)][term]  # Get term frequency in the current document
                    # Compute IDF
                    idf = math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5)) if doc_freq > 0 else 0
                    # Compute BM25 component
                    k1 = 1.2
                    b = 0.75
                    avg_doc_len = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
                    tf = term_freq / doc_length if doc_length > 0 else 0
                    denominator = (k1 + 1) * (1 - b + b * (doc_length / avg_doc_len)) if avg_doc_len > 0 else 1
                    score += (k1 + 1) * tf / denominator * idf

            if score > 0:
                results.append({
                    'file': file,
                    'content': content,
                    'subject': subject,
                    'source_pdf': os.path.splitext(file)[0] + '.pdf',
                    'page': os.path.splitext(file)[0].split('-')[-1],
                    'score': score
                })

    # Sort by score (descending)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

@app.route('/', methods=['GET'])
@login_required
def root():
    return redirect(url_for('chat'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('chat'))

        return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        user = User()
        user.username = username
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# Logout route
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
