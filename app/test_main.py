from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_session():
    response = client.post("/sessions")
    assert response.status_code == 200
    assert "session_id" in response.json()