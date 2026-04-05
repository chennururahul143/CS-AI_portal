from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3, os, uuid, json
from datetime import datetime
from agent import ask_agent
from pdf_reader import extract_text, cleanup_upload

app = Flask(__name__, static_folder="static")
CORS(app)
app.secret_key = "cs-agent-secret-2026"

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
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

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
    history = load_history(session_id)
    result  = ask_agent(user_msg, history, pdf_context, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    save_message(session_id, "user",      user_msg,        "user")
    save_message(session_id, "assistant", result["reply"],  result["source"])
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"]})

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

@app.route("/clear", methods=["POST"])
def clear():
    session_id = get_session_id()
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
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
    from agent import build_panic_prompt
    result = ask_agent(build_panic_prompt(module, topic), load_history(session_id), None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    save_message(session_id, "user",      f"[Panic] {module}" + (f" — {topic}" if topic else ""), "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "panic"})

@app.route("/tool/clash", methods=["POST"])
def tool_clash():
    data       = request.get_json()
    concept1   = data.get("concept1", "").strip()
    concept2   = data.get("concept2", "").strip()
    model_pref = data.get("model", "groq")
    session_id = get_session_id()
    if not concept1 or not concept2:
        return jsonify({"error": True, "message": "Please enter both concepts."})
    from agent import build_clash_prompt
    result = ask_agent(build_clash_prompt(concept1, concept2), load_history(session_id), None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    save_message(session_id, "user",      f"[Clash] {concept1} vs {concept2}", "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "clash"})

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
    from agent import build_lecturer_prompt
    result = ask_agent(build_lecturer_prompt(content[:4000]), load_history(session_id), None, model_pref)
    if result.get("error"):
        return jsonify({"error": True, "message": result["message"]})
    save_message(session_id, "user",      "[Lecturer] content uploaded", "user")
    save_message(session_id, "assistant", result["reply"], result["source"])
    return jsonify({"error": False, "reply": result["reply"], "source": result["source"], "tool": "lecturer"})

# ── RUN — always at the very bottom ──
if __name__ == "__main__":
    init_db()
    print("CS Agent running at http://localhost:5000")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)