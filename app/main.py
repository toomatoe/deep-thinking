import os
import random
import sqlite3
import uuid


import uvicorn
from fastapi import FastAPI, Body
from app.models import TurnRequest, TurnResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from transformers import pipeline

# Replace the model from "distilgpt2" to "gpt2-medium" for better responses
question_generator = pipeline("text-generation", model="gpt2-medium")

app = FastAPI(title="Socratic Coach MVP")

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

def generate_question(user_msg):
    prompt = (
        "You are a Socratic coach. Respond with a thoughtful question to help the user reflect deeper.\n"
        f"User: {user_msg}\nCoach:"
    )
    result = question_generator(prompt, max_length=50, num_return_sequences=1)
    # Ensure the output is a question and not just a fragment
    output = result[0]['generated_text'].split("Coach:")[-1].strip()
    # If the output doesn't end with a question mark, add a generic Socratic question
    if not output.endswith("?"):
        output += " What makes you feel that way?"
    return output

@app.post("/turn", response_model=TurnResponse)
async def create_turn(request: TurnRequest):
    user_msg = request.user_msg.lower()
    save_user_message(request.session_id, user_msg)
    question = generate_question(user_msg)
    next_phase = "contextual"
    cluster = get_cluster_label(user_msg)

    if request.session_id not in sessions:
        sessions[request.session_id] = []
    asked_questions = {entry["ai"] for entry in sessions[request.session_id]}
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
