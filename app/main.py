from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.models import TurnRequest, TurnResponse
import uuid

app = FastAPI(title="Socratic Coach MVP")

# In-memory storage for MVP
sessions = {}

@app.post("/turn", response_model=TurnResponse)
async def create_turn(request: TurnRequest):
    """Ask one Socratic question based on user input"""
    
    # Simple question generation for MVP
    user_msg = request.user_msg.lower()
    
    if "want" in user_msg or "goal" in user_msg:
        question = "What specifically would success look like?"
        next_phase = "clarify"
    elif "because" in user_msg or "think" in user_msg:
        question = "What assumptions are you making about that?"
        next_phase = "assumptions"
    else:
        question = "What do you mean by that exactly?"
        next_phase = "clarify"
    
    # Store in session
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

@app.get("/")
async def get_frontend():
    """Serve the frontend"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Socratic Coach MVP</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            #chat { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin: 20px 0; }
            .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .user { background: #e3f2fd; }
            .ai { background: #f3e5f5; }
            input[type="text"] { width: 70%; padding: 10px; }
            button { padding: 10px 20px; margin-left: 10px; }
        </style>
    </head>
    <body>
        <h1>Socratic Coach MVP</h1>
        <p>I'll ask you one question at a time to help you think deeper.</p>
        
        <div id="chat"></div>
        
        <div>
            <input type="text" id="userInput" placeholder="Share your thoughts..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            let sessionId = null;
            
            // Create session when page loads
            async function initSession() {
                const response = await fetch('/sessions', { method: 'POST' });
                const data = await response.json();
                sessionId = data.session_id;
                addMessage("Welcome! What's on your mind today?", "ai");
            }
            
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message to chat
                addMessage(message, "user");
                input.value = '';
                
                try {
                    const response = await fetch('/turn', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: sessionId,
                            user_msg: message
                        })
                    });
                    
                    const data = await response.json();
                    addMessage(data.question, "ai");
                    
                } catch (error) {
                    addMessage("Sorry, something went wrong. Try again.", "ai");
                }
            }
            
            function addMessage(text, sender) {
                const chat = document.getElementById('chat');
                const div = document.createElement('div');
                div.className = `message ${sender}`;
                div.textContent = text;
                chat.appendChild(div);
                chat.scrollTop = chat.scrollHeight;
            }
            
            // Enter key support
            document.getElementById('userInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
            
            // Initialize when page loads
            initSession();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
