import os
import sys
import json
import time
import random
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from fact_finder import get_authentic_facts
from carousel_engine import generate_carousel_slides, generate_daily_briefing, get_autopilot_topic

# Force standard streams to use UTF-8 to prevent encoding errors on Windows background tasks
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, "research_history.json")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
QUEUE_FILE = os.path.join(DATA_DIR, "queue.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
ANALYTICS_FILE = os.path.join(DATA_DIR, "analytics.json")

# Helper lock for thread safety on file reads/writes
file_lock = threading.Lock()

def load_json_file(filepath, default_val):
    with file_lock:
        if not os.path.exists(filepath):
            return default_val
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val

def save_json_file(filepath, data):
    with file_lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving to {filepath}: {e}")
            return False

# ── SCHEDULER & AUTOPILOT ENGINE ──────────────────────────────────────────────

def calculate_next_peak_time():
    now = datetime.now()
    slot1 = now.replace(hour=12, minute=30, second=0, microsecond=0)
    slot2 = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if now < slot1:
        target = slot1
    elif now < slot2:
        target = slot2
    else:
        target = slot1 + timedelta(days=1)
        
    return target.strftime("%Y-%m-%d %H:%M")

def pick_weighted_option(weight_dict):
    """Picks a key from a dictionary of weights using weighted probability."""
    keys = list(weight_dict.keys())
    weights = [max(0.1, weight_dict[k]) for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]

def run_autopilot_iteration():
    """Research, design, write, style, and schedule a post automatically."""
    settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
    niche = settings.get("niche", "All of the above (my niche covers all tech)")
    
    # 1. Pick a topic
    topic = get_autopilot_topic(niche)
    print(f"[Autopilot] Selected topic: '{topic}' for niche '{niche}'")
    
    # 2. Retrieve facts
    facts = get_authentic_facts(topic)
    chosen_facts = facts[:3]
    
    # 3. Generate slides and baseline content
    analysis = generate_carousel_slides(topic, niche, chosen_facts)
    
    # 4. Apply Self-Betterment design choices if not matched by platform brand
    theme_config = analysis.get("theme_config", {})
    
    # Initialize default weights if missing
    style_names = ["minimal", "tech", "editorial", "memphis", "corporate", "typography", "gradient"]
    palette_names = [f"pal{i}" for i in range(1, 16)]
    
    default_weights = {
        "styles": {s: 1.0 for s in style_names},
        "palettes": {p: 1.0 for p in palette_names}
    }
    weights = settings.get("weights", default_weights)
    if "styles" not in weights or "palettes" not in weights:
        weights = default_weights
        
    if not theme_config.get("matched"):
        selected_style = pick_weighted_option(weights["styles"])
        selected_palette = pick_weighted_option(weights["palettes"])
        
        # Override values
        theme_config["style"] = selected_style
        theme_config["palette"] = selected_palette
        theme_config["logo_icon"] = "5x"
        theme_config["logo_text"] = "REACH"
        analysis["theme_config"] = theme_config
        print(f"[Autopilot] Optimized design: Style '{selected_style}', Palette '{selected_palette}'")
    else:
        print(f"[Autopilot] Brand design matched: Brand '{theme_config['brand']}', Palette '{theme_config['palette']}'")

    # Save selected style/palette into slides meta so simulator logs them correctly
    analysis["style"] = theme_config.get("style", "minimal")
    analysis["palette"] = theme_config.get("palette", "pal1")
    
    # 5. Schedule post
    scheduled_time = calculate_next_peak_time()
    
    post = {
        "id": str(int(time.time() * 1000)),
        "topic": topic,
        "slides": analysis.get("slides", []),
        "caption": analysis.get("caption", ""),
        "hashtags": analysis.get("hashtags", []),
        "niche": niche,
        "style": analysis["style"],
        "palette": analysis["palette"],
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    queue = load_json_file(QUEUE_FILE, [])
    queue.append(post)
    queue.sort(key=lambda x: x.get("scheduled_time", ""))
    save_json_file(QUEUE_FILE, queue)
    
    print(f"[Autopilot] Successfully queued post '{topic}' for {scheduled_time}\n")
    return post

def check_and_publish_posts():
    """Background loop that monitors the queue, publishes due posts, and runs Autopilot."""
    print("[Scheduler] Background publisher and autopilot service active.", flush=True)
    last_autopilot_check = 0
    
    while True:
        try:
            time.sleep(5) # Check every 5 seconds
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            queue = load_json_file(QUEUE_FILE, [])
            print(f"[Scheduler] Loop check. Current time: {now_str}. Queue size: {len(queue)}", flush=True)
            
            # 1. Check queue and publish due posts
            updated = False
            for post in queue:
                if post.get("status") == "scheduled":
                    scheduled_time = post.get("scheduled_time", "")
                    if scheduled_time and scheduled_time <= now_str:
                        post["status"] = "published"
                        post["published_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        updated = True
                        
                        accounts = load_json_file(ACCOUNTS_FILE, {})
                        connected = [platform for platform, info in accounts.items() if info.get("connected")]
                        
                        print(f"\n🚀 [PUBLISH] Autoposted carousel '{post.get('topic')}' to: {', '.join(connected) if connected else 'Simulation Mode'}")
                        
                        # Generate simulated analytics
                        views = random.randint(800, 15000)
                        
                        style_multipliers = {
                            "minimal": 1.0, "tech": 1.2, "editorial": 1.1, 
                            "memphis": 1.3, "corporate": 0.9, "typography": 1.0, "gradient": 1.4
                        }
                        palette_multipliers = {
                            "pal1": 1.1, "pal2": 1.2, "pal3": 1.0, "pal4": 1.1, "pal5": 1.3,
                            "pal6": 0.9, "pal7": 1.2, "pal8": 1.0, "pal9": 1.1, "pal10": 0.9,
                            "pal11": 1.0, "pal12": 1.1, "pal13": 1.2, "pal14": 1.3, "pal15": 1.0,
                            "claude": 1.4, "shopify": 1.5, "python": 1.3, "javascript": 1.3,
                            "spacex": 1.4, "openai": 1.5, "linkedin": 1.2
                        }
                        
                        post_style = post.get("style", "minimal")
                        post_palette = post.get("palette", "pal1")
                        
                        mult = style_multipliers.get(post_style, 1.0) * palette_multipliers.get(post_palette, 1.0)
                        engagement_rate = random.uniform(0.02, 0.08) * mult
                        
                        likes = int(views * engagement_rate)
                        comments = int(likes * random.uniform(0.06, 0.18))
                        shares = int(likes * random.uniform(0.04, 0.12))
                        followers_gained = int(views * random.uniform(0.002, 0.01))
                        
                        # Save analytics entry
                        analytics_data = load_json_file(ANALYTICS_FILE, [])
                        analytics_entry = {
                            "post_id": post.get("id"),
                            "topic": post.get("topic"),
                            "niche": post.get("niche"),
                            "style": post_style,
                            "palette": post_palette,
                            "views": views,
                            "likes": likes,
                            "comments": comments,
                            "shares": shares,
                            "followers": followers_gained,
                            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        analytics_data.insert(0, analytics_entry)
                        save_json_file(ANALYTICS_FILE, analytics_data[:100])
                        
                        # Optimization weights correction (Self-Betterment Feedback Loop)
                        perf_ratio = engagement_rate / 0.045
                        settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
                        
                        style_names = ["minimal", "tech", "editorial", "memphis", "corporate", "typography", "gradient"]
                        palette_names = [f"pal{i}" for i in range(1, 16)]
                        default_weights = {
                            "styles": {s: 1.0 for s in style_names},
                            "palettes": {p: 1.0 for p in palette_names}
                        }
                        weights = settings.get("weights", default_weights)
                        if "styles" not in weights or "palettes" not in weights:
                            weights = default_weights
                            
                        # Adjust style weight
                        if post_style in weights["styles"]:
                            s_w = weights["styles"][post_style]
                            s_w = max(0.2, min(5.0, s_w + (0.25 if perf_ratio > 1.0 else -0.12)))
                            weights["styles"][post_style] = round(s_w, 2)
                        
                        # Adjust palette weight
                        if post_palette in weights["palettes"]:
                            p_w = weights["palettes"][post_palette]
                            p_w = max(0.2, min(5.0, p_w + (0.25 if perf_ratio > 1.0 else -0.12)))
                            weights["palettes"][post_palette] = round(p_w, 2)
                            
                        settings["weights"] = weights
                        save_json_file(SETTINGS_FILE, settings)
                        print(f"📈 [BETTERMENT] Adjusted style/palette weights. Style '{post_style}' weight is now {weights['styles'].get(post_style, 1.0)}")
                        
                        # Add to history
                        history_entry = {
                            "type": "publish",
                            "topic": post.get("topic"),
                            "niche": post.get("niche"),
                            "slides": post.get("slides"),
                            "caption": post.get("caption"),
                            "platforms": connected,
                            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        history = load_json_file(HISTORY_FILE, [])
                        history.insert(0, history_entry)
                        save_json_file(HISTORY_FILE, history[:100])
                        
            if updated:
                save_json_file(QUEUE_FILE, queue)
            
            # 2. Autopilot check (every 30 seconds check if empty queue and Autopilot is enabled)
            t_now = time.time()
            if t_now - last_autopilot_check > 30:
                last_autopilot_check = t_now
                settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
                if settings.get("autopilot"):
                    # Check if any post is scheduled
                    scheduled_posts = [p for p in queue if p.get("status") == "scheduled"]
                    if not scheduled_posts:
                        print("[Autopilot] No scheduled posts found. Running automatic research/design loop...")
                        run_autopilot_iteration()
                        
        except Exception as e:
            print(f"Scheduler exception: {e}")

# Start background thread
scheduler_thread = threading.Thread(target=check_and_publish_posts, daemon=True)
scheduler_thread.start()

# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})

@app.route("/api/fetch-facts", methods=["POST"])
def fetch_facts():
    body = request.json or {}
    topic = body.get("topic", "").strip()
    if not topic:
        return jsonify({"ok": False, "error": "Topic is required"}), 400
    try:
        facts = get_authentic_facts(topic)
        return jsonify({"ok": True, "facts": facts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/generate-carousel", methods=["POST"])
def generate_carousel():
    body = request.json or {}
    topic = body.get("topic", "").strip()
    niche = body.get("niche", "All of the above (my niche covers all tech)")
    facts = body.get("facts", [])
    
    if not topic:
        return jsonify({"ok": False, "error": "Topic is required"}), 400
    
    try:
        analysis = generate_carousel_slides(topic, niche, facts)
        return jsonify({"ok": True, "analysis": analysis})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/schedule-post", methods=["POST"])
def schedule_post():
    body = request.json or {}
    topic = body.get("topic", "").strip()
    slides = body.get("slides", [])
    caption = body.get("caption", "")
    hashtags = body.get("hashtags", [])
    niche = body.get("niche", "")
    scheduled_time = body.get("scheduled_time", "")
    style = body.get("style", "minimal")
    palette = body.get("palette", "pal1")
    
    if not topic or not scheduled_time:
        return jsonify({"ok": False, "error": "Topic and Scheduled Time are required"}), 400
    
    post = {
        "id": str(int(time.time() * 1000)),
        "topic": topic,
        "slides": slides,
        "caption": caption,
        "hashtags": hashtags,
        "niche": niche,
        "style": style,
        "palette": palette,
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    queue = load_json_file(QUEUE_FILE, [])
    queue.append(post)
    queue.sort(key=lambda x: x.get("scheduled_time", ""))
    
    if save_json_file(QUEUE_FILE, queue):
        return jsonify({"ok": True, "message": "Post successfully scheduled!"})
    return jsonify({"ok": False, "error": "Failed to save schedule"}), 500

@app.route("/api/accounts", methods=["GET", "POST"])
def manage_accounts():
    if request.method == "GET":
        accounts = load_json_file(ACCOUNTS_FILE, {
            "linkedin": {"connected": False, "username": ""},
            "instagram": {"connected": False, "username": ""},
            "x": {"connected": False, "username": ""},
            "tiktok": {"connected": False, "username": ""},
            "facebook": {"connected": False, "username": ""}
        })
        return jsonify({"ok": True, "accounts": accounts})
    else:
        body = request.json or {}
        save_json_file(ACCOUNTS_FILE, body)
        return jsonify({"ok": True, "message": "Social accounts updated successfully!"})

@app.route("/api/queue", methods=["GET"])
def get_queue():
    queue = load_json_file(QUEUE_FILE, [])
    return jsonify({"ok": True, "queue": queue})

@app.route("/api/queue/clear", methods=["POST"])
def clear_queue():
    save_json_file(QUEUE_FILE, [])
    return jsonify({"ok": True, "message": "Queue cleared successfully!"})

@app.route("/api/briefing", methods=["POST"])
def briefing():
    body = request.json or {}
    niche = body.get("niche", "All of the above (my niche covers all tech)")
    
    history = load_json_file(HISTORY_FILE, [])
    queue = load_json_file(QUEUE_FILE, [])
    
    recent_topics = []
    for item in queue + history:
        topic = item.get("topic")
        if topic and topic not in recent_topics:
            recent_topics.append(topic)
            if len(recent_topics) >= 5:
                break
                
    if not recent_topics:
        recent_topics = ["Leveraging tech integrations", "Maximizing organic reach in 2026", "Self-contained systems design"]
        
    try:
        result = generate_daily_briefing(niche, recent_topics)
        
        history_entry = {
            "type": "briefing",
            "niche": niche,
            "result": result,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        history.insert(0, history_entry)
        save_json_file(HISTORY_FILE, history[:100])
        
        return jsonify({"ok": True, "briefing": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/history")
def history():
    hist = load_json_file(HISTORY_FILE, [])
    return jsonify(hist)

@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    save_json_file(HISTORY_FILE, [])
    return jsonify({"ok": True, "message": "History cleared successfully!"})

# ── NEW AUTOPILOT & ANALYTICS ENDPOINTS ───────────────────────────────────────

@app.route("/api/autopilot/toggle", methods=["POST"])
def autopilot_toggle():
    body = request.json or {}
    enabled = body.get("enabled", False)
    niche = body.get("niche", "All of the above (my niche covers all tech)")
    
    settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
    settings["autopilot"] = enabled
    settings["niche"] = niche
    
    if save_json_file(SETTINGS_FILE, settings):
        return jsonify({"ok": True, "enabled": enabled, "message": f"Autopilot set to {enabled}"})
    return jsonify({"ok": False, "error": "Failed to save settings"}), 500

@app.route("/api/autopilot/status", methods=["GET"])
def autopilot_status():
    settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
    
    style_names = ["minimal", "tech", "editorial", "memphis", "corporate", "typography", "gradient"]
    palette_names = [f"pal{i}" for i in range(1, 16)]
    default_weights = {
        "styles": {s: 1.0 for s in style_names},
        "palettes": {p: 1.0 for p in palette_names}
    }
    
    if "weights" not in settings:
        settings["weights"] = default_weights
        
    return jsonify({"ok": True, "status": settings})

@app.route("/api/autopilot/run", methods=["POST"])
def autopilot_run():
    """Immediately trigger an Autopilot iteration."""
    try:
        post = run_autopilot_iteration()
        return jsonify({"ok": True, "post": post, "message": "Autopilot post successfully generated and queued!"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    data = load_json_file(ANALYTICS_FILE, [])
    return jsonify({"ok": True, "analytics": data})

@app.route("/api/analytics/clear", methods=["POST"])
def clear_analytics():
    save_json_file(ANALYTICS_FILE, [])
    return jsonify({"ok": True, "message": "Analytics cleared successfully!"})

@app.route("/api/settings/save", methods=["POST"])
def save_settings():
    body = request.json or {}
    settings = load_json_file(SETTINGS_FILE, {"autopilot": False, "niche": "All of the above (my niche covers all tech)"})
    for k, v in body.items():
        settings[k] = v
    if save_json_file(SETTINGS_FILE, settings):
        return jsonify({"ok": True, "message": "Settings saved successfully!"})
    return jsonify({"ok": False, "error": "Failed to save settings"}), 500

@app.route("/api/image-proxy")
def image_proxy():
    prompt = request.args.get("prompt", "").strip()
    if not prompt:
        return "Prompt is required", 400
        
    settings = load_json_file(SETTINGS_FILE, {})
    gemini_key = settings.get("gemini_api_key", "").strip()
    
    if gemini_key:
        print(f"[AI Image Proxy] Generating using Gemini 2.5 Flash Image (Nano Banana) for prompt: '{prompt[:40]}...'")
        try:
            import requests as req
            import base64
            from flask import Response
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "responseModalities": ["IMAGE"]
                }
            }
            res = req.post(url, headers=headers, json=payload, timeout=25)
            res_json = res.json()
            
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    inline_data = parts[0].get("inlineData", {})
                    img_b64 = inline_data.get("data", "")
                    mime_type = inline_data.get("mimeType", "image/jpeg")
                    if img_b64:
                        img_data = base64.b64decode(img_b64)
                        return Response(img_data, mimetype=mime_type)
            
            print(f"[AI Image Proxy] Gemini failed or returned invalid format. Response: {res_json}")
        except Exception as e:
            print(f"[AI Image Proxy] Error calling Gemini: {e}")
            
    # Fallback to Pollinations AI
    print(f"[AI Image Proxy] Redirecting to Pollinations AI fallback for prompt: '{prompt[:40]}...'")
    import requests as req
    from flask import Response
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=400&height=220&nologo=true"
        r = req.get(url, timeout=15)
        return Response(r.content, mimetype=r.headers.get("content-type", "image/jpeg"))
    except Exception as e:
        print(f"[AI Image Proxy] Pollinations fallback failed: {e}")
        return "Failed to load image", 500

if __name__ == "__main__":
    print("\n[i] Smart Researcher starting...")
    print("[*] Open: http://localhost:5001\n")
    app.run(debug=False, port=5001)
