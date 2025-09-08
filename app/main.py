import os
import random
import sqlite3
import uuid

import uvicorn
from fastapi import FastAPI, Body
from app.models import TurnRequest, TurnResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

CLUSTER_QUESTIONS = {0: [
        "What specifically would success look like for you?",
        "How will you know when you've achieved that?",
        "What outcome are you hoping for?"
    ],

    1: [
        "What assumptions are you making about that?",
        "Is there another way to look at this?",
        "What evidence do you have that supports your thinking?"
    ],
    2: [
        "What do you love about this?",
        "What excites you most about this?",
        "What keeps you motivated here?"
    ]
}
app = FastAPI(title="Socratic Coach MVP")

# In-memory storage for MVP
sessions = {}

vectorizer = None
kmeans = None
NUM_CLUSTERS = 3


DB_PATH = "user_messages.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_msg TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            session_id TEXT PRIMARY KEY,
            username TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def load_user_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_msg FROM user_messages")
    messages = [row[0] for row in c.fetchall()]
    conn.close()
    return messages

def save_user_message(session_id, user_msg):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO user_messages (session_id, user_msg) VALUES (?, ?)", (session_id, user_msg))
    conn.commit()
    conn.close()

def fit_vectorizer_and_kmeans():
    global vectorizer, kmeans
    messages = load_user_messages()
    if len(messages) < NUM_CLUSTERS:
        return
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(messages)
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, n_init=10, random_state=42)
    kmeans.fit(X)

def get_cluster_label(user_msg):
    global vectorizer, kmeans
    if vectorizer is None or kmeans is None:
        fit_vectorizer_and_kmeans()
    if vectorizer is None or kmeans is None:
        return None
    X = vectorizer.transform([user_msg])
    return kmeans.predict(X)[0]

@app.post("/turn", response_model=TurnResponse)
async def create_turn(request: TurnRequest):
    user_msg = request.user_msg.lower()
    save_user_message(request.session_id, user_msg)
    cluster = get_cluster_label(user_msg)
    if cluster in CLUSTER_QUESTIONS:
        question = random.choice(CLUSTER_QUESTIONS[cluster])
        if cluster == 0:
            next_phase = "clarify"
        elif cluster == 1:
            next_phase = "assumptions"
        elif cluster == 2:
            next_phase = "appreciate"
   
    else:
        if "want" in user_msg or "goal" in user_msg:
            question = "What specifically would success look like?"
            next_phase = "clarify"
        elif "because" in user_msg or "think" in user_msg:
            question = "What assumptions are you making about that?"
            next_phase = "assumptions"
        elif "love" in user_msg or "like" in user_msg:
            question = "What do you love about this?"
            next_phase = "appreciate"
        else:
            question = "What do you mean by that exactly?"
            next_phase = "clarify"
    if request.session_id not in sessions:
        sessions[request.session_id] = []
    sessions[request.session_id].append({
        "user": request.user_msg,
        "ai": question
    })
    return TurnResponse(question=question, next_phase=next_phase)

@app.post("/sessions")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = []
    return {"session_id": session_id}

@app.post("/set_username")
async def set_username(session_id: str = Body(...), username: str = Body(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_profiles (session_id, username) VALUES (?, ?)",
        (session_id, username)
    )
    conn.commit()
    conn.close()
    return {"session_id": session_id, "username": username}

@app.get("/get_username/{session_id}")
async def get_username(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM user_profiles WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"session_id": session_id, "username": row[0]}
    else:
        return {"session_id": session_id, "username": None}
