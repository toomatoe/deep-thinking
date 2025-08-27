from pydantic import BaseModel
from typing import List, Optional

class TurnRequest(BaseModel):
    session_id: str
    user_msg: str

class TurnResponse(BaseModel):
    question: str
    next_phase: str
