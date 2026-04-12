from groq import Groq
from openai import OpenAI as OpenAIClient
import requests
import re
import os
import json
from modules_context import MODULES_CONTEXT, MODULES

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL     = "llama-3.3-70b-versatile"

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_URL     = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL   = "openai/gpt-oss-120b"

OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "deepseek-r1:8b"

# ── TOPIC INTELLIGENCE ──
# Flattened keyword → (module_code, topic) mapping for fast detection
TOPIC_KEYWORDS = {}
for mod in MODULES:
    for topic in mod["topics"]:
        # Extract individual keywords from each topic
        words = [w.strip().lower() for w in re.split(r'[,;()\s]+', topic) if len(w.strip()) > 2]
        for w in words:
            TOPIC_KEYWORDS[w] = (mod["code"], mod["name"], topic)
    # Also map module code and name
    TOPIC_KEYWORDS[mod["code"].lower()] = (mod["code"], mod["name"], "General")
    for word in mod["name"].lower().split():
        if len(word) > 3:
            TOPIC_KEYWORDS[word] = (mod["code"], mod["name"], "General")

# Additional keyword aliases for common student search terms
KEYWORD_ALIASES = {
    "dijkstra": ("CS605", "Mathematics and Theory of CS", "Graph theory and discrete mathematics"),
    "bfs": ("CS605", "Mathematics and Theory of CS", "Graph theory and discrete mathematics"),
    "dfs": ("CS605", "Mathematics and Theory of CS", "Graph theory and discrete mathematics"),
    "backprop": ("CS618", "Deep Learning for Software Engineers", "Backpropagation and gradient descent"),
    "backpropagation": ("CS618", "Deep Learning for Software Engineers", "Backpropagation and gradient descent"),
    "gradient": ("CS618", "Deep Learning for Software Engineers", "Backpropagation and gradient descent"),
    "cnn": ("CS618", "Deep Learning for Software Engineers", "Convolutional Neural Networks (CNN)"),
    "rnn": ("CS618", "Deep Learning for Software Engineers", "Recurrent Neural Networks (RNN, LSTM)"),
    "lstm": ("CS618", "Deep Learning for Software Engineers", "Recurrent Neural Networks (RNN, LSTM)"),
    "transformer": ("CS618", "Deep Learning for Software Engineers", "Transformer architecture and attention"),
    "gpt": ("CS618", "Deep Learning for Software Engineers", "Large Language Models (LLMs), GPT, BERT"),
    "llm": ("CS618", "Deep Learning for Software Engineers", "Large Language Models (LLMs), GPT, BERT"),
    "rsa": ("CS616", "Practical Cryptography", "Asymmetric encryption: RSA, ECC"),
    "aes": ("CS616", "Practical Cryptography", "Symmetric encryption: AES, DES"),
    "tls": ("CS616", "Practical Cryptography", "SSL/TLS protocols"),
    "ssl": ("CS616", "Practical Cryptography", "SSL/TLS protocols"),
    "hash": ("CS616", "Practical Cryptography", "Hash functions: SHA-256, MD5"),
    "sha": ("CS616", "Practical Cryptography", "Hash functions: SHA-256, MD5"),
    "tdd": ("CS608", "Software Testing", "Test-driven development (TDD)"),
    "bdd": ("CS608", "Software Testing", "Behaviour-driven development (BDD)"),
    "junit": ("CS608", "Software Testing", "Test automation with Selenium, pytest, JUnit"),
    "pytest": ("CS608", "Software Testing", "Test automation with Selenium, pytest, JUnit"),
    "selenium": ("CS608", "Software Testing", "Test automation with Selenium, pytest, JUnit"),
    "scrum": ("CS603", "Rigorous Software Process", "Agile methodologies, Scrum, Kanban, XP"),
    "agile": ("CS603", "Rigorous Software Process", "Agile methodologies, Scrum, Kanban, XP"),
    "kanban": ("CS603", "Rigorous Software Process", "Agile methodologies, Scrum, Kanban, XP"),
    "waterfall": ("CS603", "Rigorous Software Process", "Waterfall and spiral models"),
    "cicd": ("CS603", "Rigorous Software Process", "CI/CD pipelines and DevOps"),
    "devops": ("CS603", "Rigorous Software Process", "CI/CD pipelines and DevOps"),
    "solid": ("CS613", "Advanced Concepts in OOP", "SOLID principles in depth"),
    "factory": ("CS613", "Advanced Concepts in OOP", "Creational patterns: Factory, Singleton, Builder"),
    "singleton": ("CS613", "Advanced Concepts in OOP", "Creational patterns: Factory, Singleton, Builder"),
    "observer": ("CS613", "Advanced Concepts in OOP", "Behavioural patterns: Observer, Strategy, Command"),
    "strategy": ("CS613", "Advanced Concepts in OOP", "Behavioural patterns: Observer, Strategy, Command"),
    "polymorphism": ("CS613", "Advanced Concepts in OOP", "Encapsulation, inheritance, polymorphism, abstraction"),
    "inheritance": ("CS613", "Advanced Concepts in OOP", "Encapsulation, inheritance, polymorphism, abstraction"),
    "encapsulation": ("CS613", "Advanced Concepts in OOP", "Encapsulation, inheritance, polymorphism, abstraction"),
    "dfa": ("CS605", "Mathematics and Theory of CS", "Finite automata, DFA, NFA"),
    "nfa": ("CS605", "Mathematics and Theory of CS", "Finite automata, DFA, NFA"),
    "turing": ("CS605", "Mathematics and Theory of CS", "Turing machines and computability"),
    "halting": ("CS605", "Mathematics and Theory of CS", "Decidability and the halting problem"),
    "chomsky": ("CS605", "Mathematics and Theory of CS", "Chomsky hierarchy"),
    "uml": ("CS607", "Requirements Engineering and System Design", "UML diagrams: class, sequence, use case"),
    "microservice": ("CS607", "Requirements Engineering and System Design", "MVC, microservices, monolithic architecture"),
    "microservices": ("CS607", "Requirements Engineering and System Design", "MVC, microservices, monolithic architecture"),
    "mvc": ("CS607", "Requirements Engineering and System Design", "MVC, microservices, monolithic architecture"),
    "nielsen": ("CS610", "Interaction Design", "Usability heuristics (Nielsen)"),
    "wireframe": ("CS610", "Interaction Design", "Wireframing and prototyping"),
    "persona": ("CS610", "Interaction Design", "User research and personas"),
    "gestalt": ("CS610", "Interaction Design", "Gestalt principles"),
    "wcag": ("CS610", "Interaction Design", "Accessibility and WCAG standards"),
    "figma": ("CS610", "Interaction Design", "Figma and design tools"),
}
TOPIC_KEYWORDS.update(KEYWORD_ALIASES)


def detect_topic(message):
    """Detect which module/topic the student's question maps to."""
    msg_lower = message.lower()
    words = re.findall(r'\b[a-z]{3,}\b', msg_lower)

    # Check exact keyword matches (longest match first for accuracy)
    best_match = None
    best_len = 0
    for word in words:
        if word in TOPIC_KEYWORDS and len(word) > best_len:
            best_match = TOPIC_KEYWORDS[word]
            best_len = len(word)

    # Also check multi-word phrases
    for phrase, mapping in KEYWORD_ALIASES.items():
        if phrase in msg_lower and len(phrase) > best_len:
            best_match = mapping
            best_len = len(phrase)

    return best_match  # Returns (code, module_name, topic) or None


def detect_struggle(message, history, topic_counts):
    """Detect if the student is struggling based on signals."""
    msg_lower = message.lower().strip()
    signals = []

    # Signal 1: Confusion keywords
    confusion_words = [
        "don't understand", "dont understand", "confused", "still don't get",
        "what do you mean", "huh", "i'm lost", "help me understand",
        "can you explain again", "explain it differently", "too complicated",
        "lost me", "not clear", "unclear", "makes no sense", "struggling",
        "i don't get it", "dont get it", "what does that mean",
        "one more time", "say that again", "try again", "different way"
    ]
    if any(phrase in msg_lower for phrase in confusion_words):
        signals.append("confusion")

    # Signal 2: Same topic asked 3+ times across all sessions
    current_topic = detect_topic(message)
    if current_topic and topic_counts:
        topic_key = current_topic[2]  # The specific topic string
        count = topic_counts.get(topic_key, 0)
        if count >= 3:
            signals.append("repeated_topic")

    # Signal 3: Very short follow-up after a long AI answer (student is overwhelmed)
    if len(history) > 0 and len(msg_lower.split()) <= 3:
        last_ai = history[-1].get("assistant", "")
        if len(last_ai) > 800:
            signals.append("overwhelmed")

    return signals


def build_memory_context(all_history, topic_counts, current_session_history):
    """Build a learning memory preamble the AI uses to personalize every response."""
    if not all_history and not topic_counts:
        return ""

    memory_parts = []

    # 1. Topics the student has explored
    if topic_counts:
        explored = sorted(topic_counts.items(), key=lambda x: -x[1])[:10]
        explored_str = ", ".join([f"{t} ({c}x)" for t, c in explored])
        memory_parts.append(f"Topics this student has explored: {explored_str}")

        # Count unique modules
        modules_explored = set()
        for topic_str, count in topic_counts.items():
            for mod in MODULES:
                if topic_str in mod["topics"]:
                    modules_explored.add(mod["code"])
        memory_parts.append(f"Modules touched: {len(modules_explored)}/8")

        # Find unexplored modules
        all_codes = {m["code"] for m in MODULES}
        unexplored = all_codes - modules_explored
        if unexplored:
            unexplored_names = [f"{m['code']} ({m['name']})" for m in MODULES if m["code"] in unexplored]
            memory_parts.append(f"Modules NOT yet explored: {', '.join(unexplored_names)}")

    # 2. The student's most recent questions (across ALL sessions, not just current)
    if all_history:
        recent_qs = [h["user"] for h in all_history[-5:]]
        memory_parts.append(f"Most recent questions (across sessions): {' | '.join(recent_qs)}")

    # 3. Detect if this is a returning student or brand new
    total_questions = len(all_history) if all_history else 0
    if total_questions == 0:
        memory_parts.append("STATUS: This is a BRAND NEW student. Welcome them warmly.")
    elif total_questions < 5:
        memory_parts.append(f"STATUS: Newer student ({total_questions} questions total). Still getting familiar.")
    else:
        memory_parts.append(f"STATUS: Returning student ({total_questions} questions total). Knows the system.")

    return "\n".join(memory_parts)


def build_welcome_line(all_history, topic_counts, is_first_message_in_session):
    """Generate the welcome/recall line that goes at the START of every first response in a session."""
    if not is_first_message_in_session:
        return ""

    # Brand new student — no history at all
    if not all_history:
        return ""  # Let the AI handle the welcome naturally

    # Returning student — build recall
    parts = []

    # What they last studied
    if all_history:
        last_q = all_history[-1]["user"]
        # Clean up tool prefixes
        for prefix in ["[Panic]", "[Clash]", "[Lecturer]"]:
            last_q = last_q.replace(prefix, "").strip()
        if len(last_q) > 60:
            last_q = last_q[:60].rsplit(" ", 1)[0] + "…"
        parts.append(f"Last time you were exploring: **{last_q}**")

    # Total topics covered
    if topic_counts:
        total_topics = sum(topic_counts.values())
        unique_topics = len(topic_counts)
        parts.append(f"📊 You've covered {unique_topics} topics across {total_topics} questions.")

        # Find their strongest module
        module_counts = {}
        for topic_str, count in topic_counts.items():
            for mod in MODULES:
                if topic_str in mod["topics"]:
                    module_counts[mod["code"]] = module_counts.get(mod["code"], 0) + count
        if module_counts:
            strongest = max(module_counts, key=module_counts.get)
            strongest_name = next(m["name"] for m in MODULES if m["code"] == strongest)
            parts.append(f"💪 Your strongest area: {strongest} — {strongest_name}")

        # Suggest unexplored
        explored_modules = set(module_counts.keys())
        all_codes = {m["code"] for m in MODULES}
        unexplored = all_codes - explored_modules
        if unexplored:
            suggest_mod = next(m for m in MODULES if m["code"] in unexplored)
            parts.append(f"💡 You haven't explored **{suggest_mod['code']} — {suggest_mod['name']}** yet. Want to start?")

    return "\n".join(parts)


# ── SYSTEM PROMPT (Enhanced with memory hooks) ──

SYSTEM_PROMPT = f"""You are an expert AI tutor for Masters-level Computer Science students at Maynooth University.
You are NOT a generic chatbot — you are a learning companion with memory. You remember everything the student has studied.

{MODULES_CONTEXT}

YOUR UNIQUE TEACHING APPROACH:

1. MEMORY & CONTINUITY
   When STUDENT_MEMORY context is provided, you MUST reference it naturally:
   - "Welcome back! I see you were working on [topic] last time..."
   - "Since you've already covered [X], let me connect this to what you know..."
   - If WELCOME_CONTEXT is provided, weave it naturally into your opening.

2. SOCRATIC METHOD (YOUR SIGNATURE)
   For conceptual questions (not code debugging), you follow this approach:
   - First, check prerequisite knowledge: "Before we dive into X, do you recall what Y is?"
   - Give a brief intuitive hook (1-2 sentences max)
   - Ask ONE guiding question that makes the student think
   - Then provide the full explanation
   - End with a reflection question: "In your own words, why does this matter?"
   
   EXAMPLE of your style:
   Student: "What is polymorphism?"
   You: "Great question! Quick check — do you remember what inheritance is in OOP?
   Think about this: what if you had a `Shape` class with a `draw()` method, and `Circle` and `Square` both extend it. When you call `draw()`, how does the program know WHICH version to execute?
   
   That's polymorphism — [full explanation follows]...
   
   🤔 Reflection: Can you think of a real-world situation where the same action behaves differently depending on who does it?"

3. STRUGGLE DETECTION
   When STRUGGLE_SIGNALS are provided:
   - "confusion" → Switch to analogy-first mode. Start with "Let me try a completely different angle..."
   - "repeated_topic" → Say "I notice you've come back to this topic. That's totally normal — it means your brain is working on it! Let me approach it from a fresh perspective..."
   - "overwhelmed" → Simplify drastically. Say "Let me break this down into just the essentials..."

4. PROACTIVE SUGGESTIONS
   At the end of substantive answers, add a "NEXT STEPS" section:
   🔗 **Related topics you should explore next:** X, Y, Z
   ✅ **Quick check:** [One question to test understanding]

YOUR CAPABILITIES:
- Answer any CS question with depth, clarity, and accuracy
- Reason step by step — always show your thinking process
- Explain uploaded documents and PDFs clearly with summaries
- Debug and explain code in any programming language
- Generate quiz questions and test students interactively
- Reference the 8 modules when relevant to the question
- Generate architecture and concept diagrams using Mermaid.js syntax

DIAGRAM RULES — very important:
Always wrap diagrams exactly like this:
DIAGRAM:
```mermaid
<your mermaid code here>
```

Supported types: flowchart TD, classDiagram, sequenceDiagram, stateDiagram-v2
- NEVER use graph LR/TD — always use flowchart LR/TD
- NEVER use -->|label|> syntax — only -->|label|
- No style commands, no %% comments, max 8 nodes
- Always put DIAGRAM: after explanation, one per response

AUTO-INCLUDE a diagram for: algorithms, OOP classes, protocols, automata, architecture, or when student says "show me"/"draw"/"diagram"

ADAPTIVE BEHAVIOUR:
- Casual question → friendly, conversational
- Formal/academic → structured, rigorous
- Code pasted → explain first, then debug
- Vague question → ask ONE clarifying question
- "explain simply" / "eli5" → analogies, simple language
- "quiz me" / "test me" → 3 MCQs with answers

OUTPUT RULES:
- Numbered steps for procedures
- Code blocks for ALL code
- End complex answers with: Related topics: X, Y, Z
- PDF content: 3 bullet summary first, then answer
- Never refuse a CS question
"""


def detect_prompt_style(message):
    msg = message.lower().strip()
    if any(k in msg for k in ["quiz me","test me","give me questions","practice questions"]):
        return "quiz"
    if any(k in msg for k in ["def ","class ","import ","function ","print(","console.log","public static","select ","create table"]):
        return "code"
    if any(k in msg for k in ["explain simply","eli5","simple terms","for beginners","what is","what are"]):
        return "simple"
    if any(k in msg for k in ["summarise","summarize","summary","from the pdf","in the document","this document"]):
        return "document"
    if any(k in msg for k in ["diagram","draw","visualise","visualize","show me","flowchart","uml","architecture"]):
        return "diagram"
    if len(msg.split()) <= 4:
        return "short"
    return "standard"


def build_messages(user_message, history, pdf_context=None,
                   memory_context=None, welcome_context=None, struggle_signals=None):
    """Build the full message list for the LLM with memory + teaching intelligence."""
    system = SYSTEM_PROMPT

    # Inject learning memory
    if memory_context:
        system += f"\n\nSTUDENT_MEMORY (use this to personalize your response):\n{memory_context}"

    # Inject welcome context for first message in session
    if welcome_context:
        system += f"\n\nWELCOME_CONTEXT (weave this into the START of your response naturally):\n{welcome_context}"

    # Inject struggle signals
    if struggle_signals:
        signals_str = ", ".join(struggle_signals)
        system += f"\n\nSTRUGGLE_SIGNALS DETECTED: [{signals_str}]. Adapt your teaching approach accordingly."

    # Inject PDF content
    if pdf_context:
        system += f"\n\nUPLOADED DOCUMENT CONTENT:\n{pdf_context}\n\nAnswer the student's question using the document above as your primary reference."

    # Inject style hints
    style = detect_prompt_style(user_message)
    style_hints = {
        "quiz":     "\n[Student wants quiz questions. Generate 3 MCQs with answers. After the quiz, suggest what to study next.]",
        "code":     "\n[Student shared code. Explain what it does, identify issues, suggest improvements. Connect to relevant module.]",
        "simple":   "\n[Student wants a simple explanation. Use analogies, avoid jargon. Still use Socratic approach but lighter.]",
        "document": "\n[Student is asking about an uploaded document. Summarise key points first, then answer.]",
        "diagram":  "\n[Student explicitly wants a diagram. You MUST include a relevant Mermaid diagram.]",
        "short":    "\n[Short or casual question. Give a direct, clear answer but still end with a follow-up suggestion.]",
        "standard": ""
    }
    system += style_hints.get(style, "")

    # Build message list
    messages = [{"role": "system", "content": system}]
    for entry in history[-8:]:
        messages.append({"role": "user",      "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["assistant"]})
    messages.append({"role": "user", "content": user_message})
    return messages


# ── LLM CALLERS (unchanged) ──

def ask_groq(messages):
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
        top_p=0.9
    )
    return response.choices[0].message.content.strip()

def ask_nvidia(messages):
    client = OpenAIClient(
        base_url=NVIDIA_URL,
        api_key=NVIDIA_API_KEY
    )
    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=messages,
        temperature=0.4,
        top_p=0.9,
        max_tokens=1024,
        stream=False
    )
    return response.choices[0].message.content.strip()

def ask_ollama_fallback(messages):
    history_text = ""
    for m in messages[1:]:
        role = "Student" if m["role"] == "user" else "Tutor"
        history_text += f"{role}: {m['content']}\n"
    prompt = f"{messages[0]['content']}\n\n{history_text}Tutor:"
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 400,
            "num_ctx":     2048,
            "num_thread":  10
        }
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()
    raw = response.json().get("response", "").strip()
    if "<think>" in raw and "</think>" in raw:
        raw = raw.split("</think>")[-1].strip()
    return raw


# ── MAIN AGENT ENTRY POINT ──

def ask_agent(user_message, history, pdf_context=None, model_pref="groq",
              all_history=None, topic_counts=None, is_first_in_session=False):
    """
    Main agent function — now with learning memory, topic intelligence, and struggle detection.

    Args:
        user_message: The student's current message
        history: Current session history (list of {user, assistant} dicts)
        pdf_context: Extracted PDF text if any
        model_pref: "groq", "nvidia", or "ollama"
        all_history: ALL messages across ALL sessions (for memory)
        topic_counts: Dict of {topic_string: count} across all sessions
        is_first_in_session: True if this is the first message in a new session
    """
    # Detect current topic
    detected_topic = detect_topic(user_message)
    topic_info = None
    if detected_topic:
        topic_info = {
            "module_code": detected_topic[0],
            "module_name": detected_topic[1],
            "topic": detected_topic[2]
        }

    # Detect struggle
    struggle_signals = detect_struggle(user_message, history, topic_counts or {})

    # Build learning memory context
    memory_context = build_memory_context(all_history or [], topic_counts or {}, history)

    # Build welcome line for first message
    welcome_context = build_welcome_line(all_history or [], topic_counts or {}, is_first_in_session)

    # Build messages with all intelligence injected
    messages = build_messages(
        user_message, history, pdf_context,
        memory_context=memory_context if (all_history or topic_counts) else None,
        welcome_context=welcome_context if welcome_context else None,
        struggle_signals=struggle_signals if struggle_signals else None
    )

    # Call the appropriate model
    if model_pref == "ollama":
        try:
            reply = ask_ollama_fallback(messages)
            return {"error": False, "reply": reply, "source": "ollama", "topic": topic_info}
        except Exception as e:
            return {"error": True, "message": f"Ollama error: {str(e)}", "source": "ollama"}

    if model_pref == "nvidia":
        try:
            reply = ask_nvidia(messages)
            return {"error": False, "reply": reply, "source": "nvidia", "topic": topic_info}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                return {"error": True, "message": "Invalid NVIDIA API key. Please check your key.", "source": "nvidia"}
            if "429" in error_msg:
                return {"error": True, "message": "NVIDIA rate limit reached. Please wait a moment.", "source": "nvidia"}
            if "404" in error_msg:
                return {"error": True, "message": "NVIDIA model not found. Check your API access.", "source": "nvidia"}
            return {"error": True, "message": f"NVIDIA error: {error_msg[:150]}", "source": "nvidia"}

    # Default: Groq with Ollama fallback
    try:
        reply = ask_groq(messages)
        return {"error": False, "reply": reply, "source": "groq", "topic": topic_info}
    except Exception as groq_error:
        error_msg = str(groq_error)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            return {"error": True, "message": "Invalid Groq API key. Please check your key.", "source": "groq"}
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            try:
                reply = ask_ollama_fallback(messages)
                return {"error": False, "reply": reply, "source": "ollama", "topic": topic_info}
            except:
                return {"error": True, "message": "Groq rate limit reached and Ollama is unavailable.", "source": "none"}
        try:
            reply = ask_ollama_fallback(messages)
            return {"error": False, "reply": reply, "source": "ollama", "topic": topic_info}
        except Exception as ollama_error:
            return {"error": True, "message": f"All models failed. Groq: {error_msg[:80]}. Ollama: {str(ollama_error)[:80]}", "source": "none"}


# ── STUDY TOOL PROMPT BUILDERS ──

def build_panic_prompt(module, topic):
    specific = f" focusing specifically on: {topic}" if topic else ""
    return f"""EXAM PANIC MODE activated for: {module}{specific}

You are an exam preparation expert. Generate a focused, practical revision plan for a Masters CS student who has an exam tomorrow. Structure your response EXACTLY as follows:

🎯 TOP 5 EXAM TOPICS
List the 5 most likely exam topics for this module with a one-line explanation of each.

⚡ KEY DEFINITIONS (must know)
List 8-10 essential definitions the student must memorise.

📝 PRACTICE QUESTIONS
For each of the top 3 topics, write 2 exam-style questions with model answers.

⏱️ 60-MINUTE REVISION PLAN
Break down exactly how to spend 60 minutes revising this module.

💡 LAST-MINUTE TIPS
3 specific tips for this module's exam."""

def build_clash_prompt(concept1, concept2):
    return f"""CONCEPT CLASH: {concept1} vs {concept2}

You are a CS tutor running a concept comparison session. Structure your response EXACTLY as follows:

⚡ {concept1.upper()} vs {concept2.upper()}

📌 QUICK DEFINITION
{concept1}: (one sentence)
{concept2}: (one sentence)

🔍 SIDE-BY-SIDE COMPARISON
| Aspect | {concept1} | {concept2} |
|--------|-----------|-----------| 
(fill in 5-6 rows covering: purpose, how it works, speed/complexity, use case, pros, cons)

🎯 REAL-WORLD ANALOGY
Give one memorable analogy for each concept that makes the difference crystal clear.

🧠 WHEN TO USE WHICH
Explain in 2-3 sentences when you would choose one over the other.

❓ QUICK QUIZ
Write 3 multiple choice questions that test whether the student can now tell these concepts apart. Include correct answers."""

def build_lecturer_prompt(content):
    return f"""EXPLAIN MY LECTURER MODE

A student has uploaded lecture content that they find confusing. Your job is to translate it into clear, understandable language. Here is the content:

---
{content}
---

Structure your response EXACTLY as follows:

📚 PLAIN ENGLISH SUMMARY
Rewrite the main ideas in simple, clear language a student can actually understand. No jargon without explanation.

🎯 TOP 3 KEY CONCEPTS
Identify the 3 most important concepts in this content and explain each one clearly.

💡 REAL-WORLD EXAMPLES
Give one concrete real-world example for each key concept.

🔗 HOW IT CONNECTS
Explain how this content connects to other topics the student might know.

❓ LIKELY EXAM QUESTIONS
Write 2 exam-style questions based on this content with brief model answers."""