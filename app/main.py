
import sklearn


import uvicorn
from fastapi import FastAPI
from app.models import TurnRequest, TurnResponse
import uuid

app = FastAPI(title="Socratic Coach MVP")


# In-memory storage for MVP
sessions = {}


@app.post("/turn", response_model=TurnResponse)
async def create_turn(request: TurnRequest):
    """Ask one Socratic question based on user input"""
    user_msg = request.user_msg.lower()

    # Save user message to file for adaptation
    with open("user_messages.txt", "a", encoding="utf-8") as f:
        f.write(user_msg + "\n")

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
