

# scikit-learn imports for personalization
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import os


import uvicorn
from fastapi import FastAPI
from app.models import TurnRequest, TurnResponse
import uuid

app = FastAPI(title="Socratic Coach MVP")


# In-memory storage for MVP
sessions = {}


vectorizer = None
kmeans = None
NUM_CLUSTERS = 3  

def load_user_messages():
    if not os.path.exists("user_messages.txt"):
        return []
    with open("user_messages.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def fit_vectorizer_and_kmeans():
    global vectorizer, kmeans
    messages = load_user_messages()
    if len(messages) < NUM_CLUSTERS:
        return  # Not enough data to cluster
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(messages)
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, n_init=10, random_state=42)
    kmeans.fit(X)

def get_cluster_label(user_msg):
    global vectorizer, kmeans
    if vectorizer is None or kmeans is None:
        fit_vectorizer_and_kmeans()
    if vectorizer is None or kmeans is None:
        return None  # Not enough data
    X = vectorizer.transform([user_msg])
    return kmeans.predict(X)[0]


@app.post("/turn", response_model=TurnResponse)
async def create_turn(request: TurnRequest):
    """Ask one Socratic question based on user input"""
    user_msg = request.user_msg.lower()

   #User messages
    with open("user_messages.txt", "a", encoding="utf-8") as f:
        f.write(user_msg + "\n")

    # Personalize
    cluster = get_cluster_label(user_msg)
    if cluster == 0:
        question = "What specifically would success look like for you?"
        next_phase = "clarify"
    elif cluster == 1:
        question = "What assumptions are you making about that?"
        next_phase = "assumptions"
    elif cluster == 2:
        question = "What do you love about this?"
        next_phase = "appreciate"
    else:
        # Fallback to keyword-based logic if not enough data
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
    """Create new session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = []
    return {"session_id": session_id}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
