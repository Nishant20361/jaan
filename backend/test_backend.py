import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_all():
    print("--- 0. Testing GET / (3D Romantic Web UI) ---")
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Jaan AI" in res_root.text
    print("Successfully served 3D Web Companion HTML!")

    print("\n--- 1. Testing /api/health ---")
    res = client.get("/api/health")
    assert res.status_code == 200, res.text
    health_data = res.json()
    print("Health response:", health_data)
    assert health_data["total_historical_messages"] == 1813
    assert health_data["total_conversation_chunks"] == 84

    print("\n--- 2. Testing /api/memories/stats ---")
    res = client.get("/api/memories/stats")
    assert res.status_code == 200, res.text
    stats = res.json()
    print(f"Stats: messages={stats['total_messages']}, photos={stats['total_photos']}, stickers={stats['total_stickers']}")
    assert stats["total_photos"] == 34
    assert stats["total_stickers"] == 26

    print("\n--- 3. Testing /api/memories/chunks ---")
    res = client.get("/api/memories/chunks?page=1&page_size=5")
    assert res.status_code == 200
    chunks = res.json()
    print(f"Chunks returned: {len(chunks['chunks'])}, total: {chunks['total']}")

    print("\n--- 4. Testing /api/memories/search?q=jaan ---")
    res = client.get("/api/memories/search?q=jaan&limit=5")
    assert res.status_code == 200
    search_res = res.json()
    print(f"Search results for 'jaan': {search_res['count']} found")
    assert search_res['count'] > 0

    print("\n--- 5. Testing /api/media/photos and stickers ---")
    photos = client.get("/api/media/photos").json()
    stickers = client.get("/api/media/stickers").json()
    print(f"Photos available: {len(photos)}, sample url: {photos[0]['url']}")
    print(f"Stickers available: {len(stickers)}, sample url: {stickers[0]['url']}")

    # Test static file serving
    photo_res = client.get(photos[0]['url'])
    assert photo_res.status_code == 200
    print(f"Successfully fetched photo static file! Status: {photo_res.status_code}, bytes: {len(photo_res.content)}")

    sticker_res = client.get(stickers[0]['url'])
    assert sticker_res.status_code == 200
    print(f"Successfully fetched sticker static file! Status: {sticker_res.status_code}, bytes: {len(sticker_res.content)}")

    print("\n--- 6. Testing /api/chat ---")
    chat_payload = {
        "message": "Kya kar rahi ho jaan?",
        "session_id": "test_session_1"
    }
    chat_res = client.post("/api/chat", json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    print(f"AI Response to 'Kya kar rahi ho jaan?':")
    print(f"  Response: {chat_data['response']}")
    print(f"  Source: {chat_data['source']}")
    print(f"  Retrieved Chunks: {chat_data['retrieved_chunks']}")

    chat_payload2 = {
        "message": "Khana khaya tumne?",
        "session_id": "test_session_1"
    }
    chat_res2 = client.post("/api/chat", json=chat_payload2)
    assert chat_res2.status_code == 200
    print(f"AI Response to 'Khana khaya tumne?':")
    print(f"  Response: {chat_res2.json()['response']}")

    print("\n--- 7. Testing User Notes CRUD ---")
    note_res = client.post("/api/memories/notes", json={
        "title": "First date memory",
        "content": "We had coffee and talked for hours under the stars.",
        "tag": "romantic"
    })
    assert note_res.status_code == 200
    note_id = note_res.json()["id"]
    print(f"Created user note id: {note_id}")

    notes_list = client.get("/api/memories/notes").json()
    assert len(notes_list) >= 1
    print(f"Current notes count: {len(notes_list)}")

    del_res = client.delete(f"/api/memories/notes/{note_id}")
    assert del_res.status_code == 200
    print("Successfully deleted user note")

    print("\nAll Backend Tests Passed Successfully! 🎉")

if __name__ == "__main__":
    test_all()
