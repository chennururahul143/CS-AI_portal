from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import sqlite3, os, uuid, json
from datetime import datetime

load_dotenv()

from agent import ask_agent, detect_topic
from pdf_reader import extract_text, cleanup_upload

app = Flask(__name__, static_folder="static")
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "cs-agent-secret-2026")

DB_PATH    = os.path.join(os.path.dirname(__file__), "database", "agent.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT DEFAULT 'groq',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New Chat',
            pinned INTEGER DEFAULT 0,
            favorited INTEGER DEFAULT 0,
            archived INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topic_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            module_code TEXT NOT NULL,
            module_name TEXT NOT NULL,
            topic TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_session_id():
    """Get session_id from request header (set by frontend via localStorage) or Flask session."""
    sid = request.headers.get("X-Session-Id", "")
    if sid:
        return sid
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def ensure_session_exists(session_id, title="New Chat"):
    """Create a chat_sessions row if it doesn't exist yet."""
    conn = get_db()
    row = conn.execute("SELECT id FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (session_id, title, now, now)
        )
        conn.commit()
    conn.close()

def update_session_timestamp(session_id):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE chat_sessions SET updated_at=? WHERE id=?", (now, session_id))
    conn.commit()
    conn.close()

def auto_title_session(session_id, first_message):
    """Auto-generate a short title from the first user message."""
    title = first_message.strip()
    # Remove tool prefixes
    for prefix in ["[Panic]", "[Clash]", "[Lecturer]", "Exam Panic Mode —", "Concept Clash:"]:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    # Truncate to ~50 chars at word boundary
    if len(title) > 50:
        title = title[:50].rsplit(" ", 1)[0] + "…"
    if not title:
        title = "New Chat"
    conn = get_db()
    conn.execute("UPDATE chat_sessions SET title=? WHERE id=? AND title='New Chat'", (title, session_id))
    conn.commit()
    conn.close()

def load_history(session_id, limit=8):
    conn = get_db()
    rows = list(reversed(conn.execute("""
        SELECT role, message FROM conversations
        WHERE session_id=? ORDER BY created_at DESC LIMIT ?
    """, (session_id, limit * 2)).fetchall()))
    conn.close()
    history, i = [], 0
    while i < len(rows) - 1:
        if rows[i]["role"] == "user" and rows[i+1]["role"] == "assistant":
            history.append({"user": rows[i]["message"], "assistant": rows[i+1]["message"]})
            i += 2
        else:
            i += 1
    return history

def save_message(session_id, role, message, source="groq"):
    conn = get_db()
    conn.execute("""
        INSERT INTO conversations (session_id, role, message, source, created_at)
        VALUES (?,?,?,?,?)
    """, (session_id, role, message, source, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def track_topic(session_id, user_message):
    """Detect and record which topic a student's question maps to."""
    topic_info = detect_topic(user_message)
    if topic_info:
        conn = get_db()
        conn.execute("""
            INSERT INTO topic_tracker (session_id, module_code, module_name, topic, created_at)
            VALUES (?,?,?,?,?)
        """, (session_id, topic_info[0], topic_info[1], topic_info[2],
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    return topic_info

def load_all_history():
    """Load ALL user messages across ALL sessions (for learning memory)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT c.role, c.message FROM conversations c
        JOIN chat_sessions cs ON c.session_id = cs.id
        WHERE cs.archived = 0
        ORDER BY c.created_at ASC
    """).fetchall()
    conn.close()
    # Pair into user/assistant pairs
    history = []
    i = 0
    while i < len(rows) - 1:
        if rows[i]["role"] == "user" and rows[i+1]["role"] == "assistant":
            history.append({"user": rows[i]["message"], "assistant": rows[i+1]["message"]})
            i += 2
        else:
            i += 1
    return history

def load_topic_counts():
    """Load topic frequency counts across all sessions."""
    conn = get_db()
    rows = conn.execute("""
        SELECT topic, COUNT(*) as cnt FROM topic_tracker
        GROUP BY topic ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return {r["topic"]: r["cnt"] for r in rows}

# ── ROUTES ──

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data        = request.get_json()
    user_msg    = data.get("message", "").strip()
    pdf_context = data.get("pdf_context", None)
    model_pref  = data.get("model", "groq")
    session_id  = get_session_id()
    if not user_msg:
        return jsonify({"error": True, "message": "Please type a message."})
    ensure_session_exists(session_id)
    history = load_history(session_id)
    is_first = len(history) == 0

    # Load cross-session intelligence
    all_history = load_all_history()
    topic_counts = load_topic_counts()

    # Call the enhanced agent with full memory
    result = ask_agent(
        user_msg, history, pdf_context, model_pref,
        all_history=all_history,
        topic_counts=topic_counts,
        is_first_in_session=is_first
    )
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})

    save_message(session_id, "user",      user_msg,        "user")
    save_message(session_id, "assistant", result["reply"],  result["source"])

    # Track topic
    track_topic(session_id, user_msg)

    # Auto-title on first message
    if is_first:
        auto_title_session(session_id, user_msg)
    update_session_timestamp(session_id)

    # Build response with topic info
    resp = {"error": False, "reply": result["reply"], "source": result["source"], "session_id": session_id}
    if result.get("topic"):
        resp["topic"] = result["topic"]
    return jsonify(resp)

@app.route("/upload", methods=["POST"])
def upload():
    if "pdf" not in request.files:
        return jsonify({"error": True, "message": "No file selected."})
    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": True, "message": "Only PDF files are supported."})
    filepath = os.path.join(UPLOAD_DIR, str(uuid.uuid4()) + ".pdf")
    file.save(filepath)
    text, error = extract_text(filepath)
    cleanup_upload(filepath)
    if error:
        return jsonify({"error": True, "message": error})
    return jsonify({"error": False, "pdf_context": text, "preview": text[:200], "char_count": len(text)})

# ── PROGRESS & ANALYTICS ──

@app.route("/progress", methods=["GET"])
def get_progress():
    """Return the student's learning progress across all modules."""
    conn = get_db()

    # Topic counts
    topic_rows = conn.execute("""
        SELECT module_code, module_name, topic, COUNT(*) as cnt
        FROM topic_tracker GROUP BY module_code, topic ORDER BY cnt DESC
    """).fetchall()

    # Total questions asked
    total = conn.execute("SELECT COUNT(*) as c FROM conversations WHERE role='user'").fetchone()["c"]

    # Total sessions
    sessions = conn.execute("SELECT COUNT(*) as c FROM chat_sessions WHERE archived=0").fetchone()["c"]

    # Study streak (count consecutive days with activity)
    day_rows = conn.execute("""
        SELECT DISTINCT DATE(created_at) as d FROM conversations ORDER BY d DESC LIMIT 30
    """).fetchall()
    conn.close()

    streak = 0
    if day_rows:
        from datetime import timedelta
        today = datetime.now().date()
        for i, row in enumerate(day_rows):
            expected = today - timedelta(days=i)
            if str(expected) == row["d"]:
                streak += 1
            else:
                break

    # Build module progress
    module_progress = {}
    for r in topic_rows:
        code = r["module_code"]
        if code not in module_progress:
            module_progress[code] = {"name": r["module_name"], "topics": [], "total_questions": 0}
        module_progress[code]["topics"].append({"topic": r["topic"], "count": r["cnt"]})
        module_progress[code]["total_questions"] += r["cnt"]

    return jsonify({
        "total_questions": total,
        "total_sessions": sessions,
        "study_streak": streak,
        "modules": module_progress
    })

# ── HISTORY & SESSION MANAGEMENT ──

@app.route("/new-session", methods=["POST"])
def new_session():
    """Create a new chat session and return its ID."""
    sid = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
        (sid, "New Chat", now, now)
    )
    conn.commit()
    conn.close()
    return jsonify({"session_id": sid})

@app.route("/history", methods=["GET"])
def list_sessions():
    """Return all non-archived chat sessions, newest first."""
    conn = get_db()
    rows = conn.execute("""
        SELECT cs.id, cs.title, cs.pinned, cs.favorited, cs.created_at, cs.updated_at,
               (SELECT COUNT(*) FROM conversations c WHERE c.session_id = cs.id AND c.role = 'user') as msg_count
        FROM chat_sessions cs
        WHERE cs.archived = 0
        ORDER BY cs.pinned DESC, cs.updated_at DESC
    """).fetchall()
    conn.close()
    sessions = []
    for r in rows:
        sessions.append({
            "id": r["id"],
            "title": r["title"],
            "pinned": bool(r["pinned"]),
            "favorited": bool(r["favorited"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "msg_count": r["msg_count"]
        })
    return jsonify({"sessions": sessions})

@app.route("/history/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    """Return all messages for a specific session."""
    conn = get_db()
    sess = conn.execute("SELECT * FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
    if not sess:
        conn.close()
        return jsonify({"error": True, "message": "Session not found."}), 404
    rows = conn.execute("""
        SELECT role, message, source, created_at FROM conversations
        WHERE session_id=? ORDER BY created_at ASC
    """, (session_id,)).fetchall()
    conn.close()
    messages = [{"role": r["role"], "message": r["message"], "source": r["source"], "created_at": r["created_at"]} for r in rows]
    return jsonify({
        "session_id": session_id,
        "title": sess["title"],
        "pinned": bool(sess["pinned"]),
        "favorited": bool(sess["favorited"]),
        "messages": messages
    })

@app.route("/history/<session_id>/rename", methods=["POST"])
def rename_session(session_id):
    data = request.get_json()
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": True, "message": "Title cannot be empty."})
    conn = get_db()
    conn.execute("UPDATE chat_sessions SET title=? WHERE id=?", (title, session_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "title": title})

@app.route("/history/<session_id>/pin", methods=["POST"])
def toggle_pin(session_id):
    conn = get_db()
    row = conn.execute("SELECT pinned FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": True, "message": "Session not found."}), 404
    new_val = 0 if row["pinned"] else 1
    conn.execute("UPDATE chat_sessions SET pinned=? WHERE id=?", (new_val, session_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "pinned": bool(new_val)})

@app.route("/history/<session_id>/favorite", methods=["POST"])
def toggle_favorite(session_id):
    conn = get_db()
    row = conn.execute("SELECT favorited FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": True, "message": "Session not found."}), 404
    new_val = 0 if row["favorited"] else 1
    conn.execute("UPDATE chat_sessions SET favorited=? WHERE id=?", (new_val, session_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "favorited": bool(new_val)})

@app.route("/history/<session_id>/archive", methods=["POST"])
def archive_session(session_id):
    conn = get_db()
    conn.execute("UPDATE chat_sessions SET archived=1 WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/history/<session_id>/delete", methods=["DELETE"])
def delete_session(session_id):
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/clear", methods=["POST"])
def clear():
    session_id = get_session_id()
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    session.pop("session_id", None)
    return jsonify({"status": "ok"})

@app.route("/tool/panic", methods=["POST"])
def tool_panic():
    data       = request.get_json()
    module     = data.get("module", "").strip()
    topic      = data.get("topic", "").strip()
    model_pref = data.get("model", "groq")
    session_id = get_session_id()
    if not module:
        return jsonify({"error": True, "message": "Please select a module."})
    ensure_session_exists(session_id)
    from agent import build_panic_prompt
    history = load_history(session_id)
    result = ask_agent(build_panic_prompt(module, topic), history, None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    user_msg = f"[Panic] {module}" + (f" — {topic}" if topic else "")
    save_message(session_id, "user", user_msg, "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    if len(history) == 0:
        auto_title_session(session_id, user_msg)
    update_session_timestamp(session_id)
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "panic", "session_id": session_id})

@app.route("/tool/clash", methods=["POST"])
def tool_clash():
    data       = request.get_json()
    concept1   = data.get("concept1", "").strip()
    concept2   = data.get("concept2", "").strip()
    model_pref = data.get("model", "groq")
    session_id = get_session_id()
    if not concept1 or not concept2:
        return jsonify({"error": True, "message": "Please enter both concepts."})
    ensure_session_exists(session_id)
    from agent import build_clash_prompt
    history = load_history(session_id)
    result = ask_agent(build_clash_prompt(concept1, concept2), history, None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    user_msg = f"[Clash] {concept1} vs {concept2}"
    save_message(session_id, "user", user_msg, "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    if len(history) == 0:
        auto_title_session(session_id, user_msg)
    update_session_timestamp(session_id)
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "clash", "session_id": session_id})

@app.route("/tool/lecturer", methods=["POST"])
def tool_lecturer():
    session_id = get_session_id()
    model_pref = request.form.get("model", "groq")
    content    = ""
    if "pdf" in request.files and request.files["pdf"].filename:
        file     = request.files["pdf"]
        filepath = os.path.join(UPLOAD_DIR, str(uuid.uuid4()) + ".pdf")
        file.save(filepath)
        text, error = extract_text(filepath)
        cleanup_upload(filepath)
        if error:
            return jsonify({"error": True, "message": error})
        content = text
    elif request.form.get("text", "").strip():
        content = request.form.get("text", "").strip()
    else:
        return jsonify({"error": True, "message": "Please upload a PDF or paste some text."})
    ensure_session_exists(session_id)
    from agent import build_lecturer_prompt
    history = load_history(session_id)
    result = ask_agent(build_lecturer_prompt(content[:4000]), history, None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    user_msg = "[Lecturer] content uploaded"
    save_message(session_id, "user", user_msg, "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    if len(history) == 0:
        auto_title_session(session_id, user_msg)
    update_session_timestamp(session_id)
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "lecturer", "session_id": session_id})

# ── INIT DB (runs on import, required for gunicorn) ──
init_db()

# ── RUN — always at the very bottom ──
if __name__ == "__main__":
    print("CS Agent running at http://localhost:5000")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)