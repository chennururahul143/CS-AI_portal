from groq import Groq
from openai import OpenAI as OpenAIClient
import requests
import re
from modules_context import MODULES_CONTEXT

GROQ_API_KEY   = "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"
GROQ_MODEL     = "llama-3.3-70b-versatile"

NVIDIA_API_KEY = "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"
NVIDIA_URL     = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL   = "openai/gpt-oss-120b"

OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "deepseek-r1:8b"

SYSTEM_PROMPT = f"""You are an expert AI tutor for Masters-level Computer Science students.

{MODULES_CONTEXT}

YOUR CAPABILITIES:
- Answer any CS question with depth, clarity, and accuracy
- Reason step by step — always show your thinking process
- Explain uploaded documents and PDFs clearly with summaries
- Debug and explain code in any programming language
- Generate quiz questions and test students interactively
- Reference the 8 modules above when relevant to the question
- Generate architecture and concept diagrams using Mermaid.js syntax

DIAGRAM RULES — very important:
You can and should include Mermaid diagrams when they add value.
Always wrap diagrams exactly like this — no exceptions:

DIAGRAM:
```mermaid
<your mermaid code here>
```

Supported diagram types and when to use them:
1. flowchart TD — for algorithms, processes, pipelines, CI/CD, neural networks, architecture
   SYNTAX: use --> arrows, -->|label| for labelled arrows, NO style commands, NO subgraph

2. classDiagram — for OOP class hierarchies, design patterns, UML
   SYNTAX: use <|-- for inheritance, use : for methods

3. sequenceDiagram — for protocols, API calls, TLS handshake, RSA exchange
   SYNTAX: use ->> for messages, -->> for return messages

4. stateDiagram-v2 — for finite automata, DFA, NFA, state machines
   SYNTAX: use --> for transitions, [*] for start and end

STRICT SYNTAX RULES — NEVER BREAK THESE:
- NEVER use graph LR or graph TD — always use flowchart LR or flowchart TD
- NEVER use -->|label|> syntax — only -->|label| is valid
- NEVER add style commands inside diagrams
- NEVER use %% comments inside diagrams
- Max 8 nodes — keep diagrams simple and clean
- Always put DIAGRAM: after the explanation, never before
- One diagram per response only

WHEN TO AUTO-INCLUDE A DIAGRAM:
- Any algorithm (Dijkstra, BFS, backprop) → flowchart TD
- Any OOP question with classes → classDiagram
- Any protocol or handshake → sequenceDiagram
- Any automata or state machine → stateDiagram-v2
- Any architecture question → flowchart TD
- Student says show me, draw, diagram, visualise → always include

WHEN NOT TO include a diagram:
- Simple one-line factual questions
- Short casual questions

YOUR ADAPTIVE BEHAVIOUR:
- Detect how the student writes and match their style:
  * Casual question → friendly, clear, conversational reply
  * Formal/academic question → structured, rigorous, referenced reply
  * Code pasted → explain what it does first, then debug if needed
  * Vague question → ask ONE clarifying question before answering
  * "explain simply" or "eli5" → use analogies and simple language
  * "quiz me" or "test me" → generate 3 multiple choice questions on the topic
- Always be honest when uncertain — say "I am not fully certain, but..."
- Keep answers concise but complete

OUTPUT RULES:
- Use numbered steps for procedures and problem solving
- Use code blocks for ALL code snippets
- End complex answers with: Related topics: X, Y, Z
- For PDF content: summarise first in 3 bullet points, then answer questions
- Never refuse a CS question — always attempt an answer
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

def build_messages(user_message, history, pdf_context=None):
    system = SYSTEM_PROMPT
    if pdf_context:
        system += f"\n\nUPLOADED DOCUMENT CONTENT:\n{pdf_context}\n\nAnswer the student's question using the document above as your primary reference."

    style = detect_prompt_style(user_message)
    style_hints = {
        "quiz":     "\n[Student wants quiz questions. Generate 3 multiple choice questions with answers.]",
        "code":     "\n[Student shared code. Explain what it does, identify any issues, suggest improvements.]",
        "simple":   "\n[Student wants a simple explanation. Use analogies, avoid jargon, keep it friendly.]",
        "document": "\n[Student is asking about an uploaded document. Summarise key points first, then answer.]",
        "diagram":  "\n[Student explicitly wants a diagram. You MUST include a relevant Mermaid diagram.]",
        "short":    "\n[Short or casual question. Give a direct, clear answer without over-explaining.]",
        "standard": ""
    }

    messages = [{"role": "system", "content": system + style_hints.get(style, "")}]
    for entry in history[-8:]:
        messages.append({"role": "user",      "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["assistant"]})
    messages.append({"role": "user", "content": user_message})
    return messages

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

def ask_agent(user_message, history, pdf_context=None, model_pref="groq"):
    messages = build_messages(user_message, history, pdf_context)

    if model_pref == "ollama":
        try:
            reply = ask_ollama_fallback(messages)
            return {"error": False, "reply": reply, "source": "ollama"}
        except Exception as e:
            return {"error": True, "message": f"Ollama error: {str(e)}", "source": "ollama"}

    if model_pref == "nvidia":
        try:
            reply = ask_nvidia(messages)
            return {"error": False, "reply": reply, "source": "nvidia"}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                return {"error": True, "message": "Invalid NVIDIA API key. Please check your key in agent.py.", "source": "nvidia"}
            if "429" in error_msg:
                return {"error": True, "message": "NVIDIA rate limit reached. Please wait a moment.", "source": "nvidia"}
            if "404" in error_msg:
                return {"error": True, "message": "NVIDIA model not found. Check your API access at integrate.api.nvidia.com.", "source": "nvidia"}
            return {"error": True, "message": f"NVIDIA error: {error_msg[:150]}", "source": "nvidia"}

    # Default: Groq with Ollama fallback
    try:
        reply = ask_groq(messages)
        return {"error": False, "reply": reply, "source": "groq"}
    except Exception as groq_error:
        error_msg = str(groq_error)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            return {"error": True, "message": "Invalid Groq API key. Please check your key in agent.py.", "source": "groq"}
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            try:
                reply = ask_ollama_fallback(messages)
                return {"error": False, "reply": reply, "source": "ollama"}
            except:
                return {"error": True, "message": "Groq rate limit reached and Ollama is unavailable.", "source": "none"}
        try:
            reply = ask_ollama_fallback(messages)
            return {"error": False, "reply": reply, "source": "ollama"}
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