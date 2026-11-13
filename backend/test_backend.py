import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.ai_engine import ai_engine

client = TestClient(app)

def test_all():
    print("--- 0. Testing GET / (3D Romantic Web UI) ---")
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Alquama" in res_root.text
    assert "Online" in res_root.text
    print("Successfully served 3D Web Companion HTML branded as Alquama!")

    print("\n--- 1. Testing /api/health ---")
    res = client.get("/api/health")
    assert res.status_code == 200, res.text
    health_data = res.json()
    print("Health response:", health_data)
    assert health_data["status"] == "online"
    assert health_data["app_name"] == "Alquama ❤️"
    assert health_data["total_historical_messages"] == 1813
    assert health_data["total_conversation_chunks"] == 84

    print("\n--- 2. Testing /api/chat/greeting ---")
    res_greet = client.get("/api/chat/greeting")
    assert res_greet.status_code == 200
    greet_data = res_greet.json()
    print("Greeting response:", greet_data)
    assert "greeting" in greet_data
    assert "avatar_url" in greet_data
    assert greet_data["name"] == "Alquama ❤️"
    assert "2680598922269266.jpg" in greet_data["avatar_url"]

    print("\n--- 3. Testing /api/memories/stats ---")
    res = client.get("/api/memories/stats")
    assert res.status_code == 200, res.text
    stats = res.json()
    print(f"Stats: messages={stats['total_messages']}, curated_photos={stats['total_photos']}, stickers={stats['total_stickers']}")
    # Total curated clean solo portraits is 8
    assert stats["total_photos"] == 8
    assert stats["total_stickers"] == 26

    print("\n--- 4. Testing Curated Clean Photos (/api/media/photos) ---")
    photos = client.get("/api/media/photos").json()
    print(f"Curated clean photos count: {len(photos)}")
    assert len(photos) == 8
    # Verify NO excluded stranger/screenshot/inappropriate photos are in the curated list
    forbidden_ids = [
        "678396336819324", "1076132693332111", "651801795433520", "302176344333831",
        "807880769971052", "249866726187587", "672764320250624", "1207072352985597"
    ]
    curated_filenames = [p["filename"] for p in photos]
    for fid in forbidden_ids:
        assert not any(fid in fn for fn in curated_filenames), f"Forbidden file {fid} found in photos!"
    print("Verified: Only clean, verified Alquama solo portraits are exposed.")

    # Test static file serving of the first photo
    photo_res = client.get(photos[0]["url"])
    assert photo_res.status_code == 200
    assert len(photo_res.content) > 1000
    print(f"Successfully fetched photo static file! Status: {photo_res.status_code}")

    print("\n--- 5. Testing Stickers (/api/media/stickers) ---")
    stickers = client.get("/api/media/stickers").json()
    assert len(stickers) == 26
    sticker_res = client.get(stickers[0]["url"])
    assert sticker_res.status_code == 200
    print(f"Successfully fetched sticker static file! Status: {sticker_res.status_code}")

    print("\n--- 6. Testing Language & Intent Detection Logic ---")
    # Test English detection
    eng_1 = ai_engine.detect_user_language("Hey babe, I had such a long day today and missed you so much")
    assert eng_1 == "english", f"Expected english, got {eng_1}"
    eng_2 = ai_engine.detect_user_language("What do you want to do tonight? Tell me something cute")
    assert eng_2 == "english", f"Expected english, got {eng_2}"

    # Test Hinglish detection
    hin_1 = ai_engine.detect_user_language("khana khai")
    assert hin_1 == "hinglish", f"Expected hinglish, got {hin_1}"
    hin_2 = ai_engine.detect_user_language("kya kr rhi ho jaan")
    assert hin_2 == "hinglish", f"Expected hinglish, got {hin_2}"
    hin_3 = ai_engine.detect_user_language("ek kiss do na jaan")
    assert hin_3 == "hinglish", f"Expected hinglish, got {hin_3}"
    print("Verified: Language detection accurately distinguishes English from Hinglish.")

    # Test Photo Intent detection
    p_intent_1 = ai_engine.detect_photo_intent("apna photo bhejo jaan")
    assert p_intent_1 == "solo", f"Expected solo, got {p_intent_1}"
    p_intent_2 = ai_engine.detect_photo_intent("send me a selfie babe")
    assert p_intent_2 == "solo", f"Expected solo, got {p_intent_2}"
    p_intent_3 = ai_engine.detect_photo_intent("hamara photo dikhao")
    assert p_intent_3 == "couple", f"Expected couple, got {p_intent_3}"
    # Verify non-photo words like 'spicy' don't trigger photo intent
    p_intent_safe = ai_engine.detect_photo_intent("kuch spicy baat karo na")
    assert p_intent_safe is None, f"Expected None for 'spicy', got {p_intent_safe}"
    print("Verified: Photo intent detection works cleanly without false positives.")

    print("\n--- 7. Testing Live Chat: 'khana khai' (Bihari question to Alquama) ---")
    test_session = "backend_test_session"
    res_chat1 = client.post("/api/chat", json={
        "message": "khana khai",
        "session_id": test_session
    })
    assert res_chat1.status_code == 200
    data1 = res_chat1.json()
    print(f"User: khana khai\nAlquama: {data1['response']}")
    assert data1["response"]
    assert data1["seen_delay_ms"] > 0
    assert data1["typing_delay_ms"] > 0
    # Response should answer about herself or lovingly address him, NOT say "Haan, toh khaana kha liya?"
    lower_r1 = data1["response"].lower()
    assert not ("toh khaana kha liya?" in lower_r1 or "toh khana kha liya?" in lower_r1), "Did not properly comprehend 'khana khai'!"

    print("\n--- 8. Testing Live Chat: Photo Request ---")
    res_chat2 = client.post("/api/chat", json={
        "message": "apna photo bhejo jaan dekhna hai",
        "session_id": test_session
    })
    assert res_chat2.status_code == 200
    data2 = res_chat2.json()
    print(f"User: apna photo bhejo jaan dekhna hai\nAlquama: {data2['response']}\nPhoto URL: {data2.get('photo_url')}")
    assert data2.get("photo_url") is not None, "Expected photo_url in response!"
    assert any(p["url"] == data2["photo_url"] for p in photos), "Returned photo not in curated clean solo list!"
    photo1_url = data2["photo_url"]

    # Follow-up "ek aur bhejo" should send a DIFFERENT photo
    res_chat3 = client.post("/api/chat", json={
        "message": "ek aur photo bhejo na",
        "session_id": test_session
    })
    assert res_chat3.status_code == 200
    data3 = res_chat3.json()
    print(f"User: ek aur photo bhejo na\nAlquama: {data3['response']}\nPhoto URL: {data3.get('photo_url')}")
    assert data3.get("photo_url") is not None, "Expected photo_url for follow-up photo request!"
    assert data3["photo_url"] != photo1_url, "Did not send a different photo for follow-up request!"

    print("\n--- 9. Testing Live Chat: English Switching ---")
    res_chat4 = client.post("/api/chat", json={
        "message": "Hey babe, I missed you so much today! How was your day?",
        "session_id": test_session
    })
    assert res_chat4.status_code == 200
    data4 = res_chat4.json()
    print(f"User (English): Hey babe, I missed you...\nAlquama: {data4['response']}")
    # Response should contain natural English words
    lower_r4 = data4["response"].lower()
    has_english = any(w in lower_r4 for w in ("missed", "miss", "day", "you", "too", "today", "love", "hope", "mine", "baby", "babe", "my", "was"))
    assert has_english, f"Expected English reply, got: {data4['response']}"

    print("\n--- 10. Testing Live Chat: Romantic / Kiss Banter & Sticker ---")
    res_chat5 = client.post("/api/chat", json={
        "message": "paas aao na jaan ek kiss do 😘",
        "session_id": test_session
    })
    assert res_chat5.status_code == 200
    data5 = res_chat5.json()
    print(f"User: paas aao na jaan ek kiss do\nAlquama: {data5['response']}\nSticker URL: {data5.get('sticker_url')}")
    assert "jaan" in data5["response"].lower() or "😘" in data5["response"] or "kiss" in data5["response"].lower() or "mwah" in data5["response"].lower() or "mmwaah" in data5["response"].lower()

    # Clean up test session
    client.delete(f"/api/chat/history?session_id={test_session}")
    print("\nAll Backend Tests Passed Successfully! 🎉")

if __name__ == "__main__":
    test_all()
