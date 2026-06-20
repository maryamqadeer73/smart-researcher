import requests
import sys
import time
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API = "http://localhost:5001"

def test_publish_loop():
    print("1. Clearing queue for a clean test...")
    requests.post(f"{API}/api/queue/clear")
    requests.post(f"{API}/api/analytics/clear")

    print("\n2. Getting current autopilot status (initial weights)...")
    r = requests.get(f"{API}/api/autopilot/status")
    status_data = r.json()
    weights_before = status_data.get("status", {}).get("weights", {})
    print("Initial minimal style weight:", weights_before.get("styles", {}).get("minimal"))
    print("Initial pal1 palette weight:", weights_before.get("palettes", {}).get("pal1"))

    # Pick a time in the past (5 minutes ago) so it gets published immediately
    past_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    print(f"\n3. Scheduling a post for a past target time: {past_time}")
    
    payload = {
        "topic": "Python 3.14 JIT compiler hacks",
        "niche": "Web Dev & Coding",
        "style": "minimal",
        "palette": "pal1",
        "scheduled_time": past_time,
        "slides": [
            {"layout": "cover", "title": "TEST TITLE", "content": "Test content", "visual_type": "none", "visual_val": ""}
        ],
        "caption": "Test caption",
        "hashtags": ["#Python", "#Dev"]
    }
    
    r = requests.post(f"{API}/api/schedule-post", json=payload)
    print("Schedule Post Response:", r.json())

    print("\n4. Waiting 8 seconds for the background scheduler thread to process the publish...")
    time.sleep(8)

    print("\n5. Checking Queue status...")
    r = requests.get(f"{API}/api/queue")
    q_data = r.json()
    queue = q_data.get("queue", [])
    if queue:
        post = queue[0]
        print(f"Post topic: {post.get('topic')}")
        print(f"Post status: {post.get('status')} (Expected: published)")
    else:
        print("Error: queue is empty!")

    print("\n6. Checking Analytics logs...")
    r = requests.get(f"{API}/api/analytics")
    a_data = r.json()
    analytics = a_data.get("analytics", [])
    if analytics:
        entry = analytics[0]
        print(f"Logged analytics entry: {entry.get('topic')}")
        print(f"Engagement: {entry.get('views')} views, {entry.get('likes')} likes, {entry.get('comments')} comments")
    else:
        print("Error: no analytics logs generated!")

    print("\n7. Checking updated weights (Self-Betterment check)...")
    r = requests.get(f"{API}/api/autopilot/status")
    status_data = r.json()
    weights_after = status_data.get("status", {}).get("weights", {})
    print("Updated minimal style weight:", weights_after.get("styles", {}).get("minimal"))
    print("Updated pal1 palette weight:", weights_after.get("palettes", {}).get("pal1"))

    # Check if weights changed
    style_changed = weights_before.get("styles", {}).get("minimal") != weights_after.get("styles", {}).get("minimal")
    palette_changed = weights_before.get("palettes", {}).get("pal1") != weights_after.get("palettes", {}).get("pal1")
    
    if style_changed or palette_changed:
        print("\n🎉 SUCCESS: Self-Betterment loop worked! Weights were successfully updated based on performance feedback.")
    else:
        print("\n❌ FAILED: Weights did not change.")

if __name__ == "__main__":
    test_publish_loop()
