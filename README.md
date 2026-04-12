<div align="center">
  <img src="https://img.icons8.com/nolan/256/1A6DFF/C822FF/artificial-intelligence.png" alt="Logo" width="80" height="80">
  <h1 align="center">AI CS Portal</h1>
  <p align="center">
    <strong>Your Personalized, AI-Powered Masters-Level Computer Science Tutor</strong>
    <br />
    A comprehensive learning companion that adapts to your learning style, tracks your progress, and deeply integrates with your curriculum.
    <br />
    <br />
    <strong><a href="https://cs-ai-portal-8oig.onrender.com" target="_blank">🚀 Try the Live Demo</a></strong>
    <br />
    <br />
    <a href="#features">Features</a>
    ·
    <a href="#tech-stack">Tech Stack</a>
    ·
    <a href="#installation">Installation</a>
    ·
    <a href="#usage-modes">Usage Modes</a>
  </p>
</div>

<hr />

## 🌟 Overview

The **AI CS Portal** is not just another chatbot. It is a **Socratic Learning Companion** specifically tailored for Computer Science students. Built to help clarify complex university topics, it comes loaded with cross-session learning memory, dynamic struggle detection, and specialized study tools to give you the exact learning experience you need.

With support for state-of-the-art Large Language Models via API (Groq, NVIDIA) and local fallbacks (Ollama), the portal is resilient, highly intelligent, and extremely fast.

---

## ✨ Key Features

### 🧠 Adaptive Learning Intelligence
* **Socratic Tutor:** Employs the Socratic method to guide you to answers rather than just giving them.
* **Continuous Memory:** Remembers your questions natively across all sessions, helping connect the dots between modules you've studied.
* **Struggle Detection:** Automatically switches to analogy-first teaching or simplifies explanations if it notices you are finding a topic difficult or overwhelming.
* **Topic Tracking & Analytics:** Tracks the modules you study, your learning strengths, and your consecutive study streak.

### 🛠️ Specialized Study Tools
* **🔥 Exam Panic Mode:** Generate a targeted 60-minute revision plan, core definitions, and exam questions for any specific module immediately.
* **⚔️ Concept Clash:** Confused between two concepts (e.g., Dijkstra vs A*, TCP vs UDP)? Get a side-by-side structural comparison with analogies and pros/cons.
* **👨‍🏫 Lecturer Mode:** Upload a confusing lecture slide or paste dense text. The AI will immediately summarize it into plain English, highlight key topics, and provide real-world examples.

### 📄 Document & PDF Mastery
* Seamlessly **upload PDF documents**. The portal will intelligently ingest them using PyMuPDF and use the document as direct context to answer your questions accurately.

### 💻 Developer Experience
* **Auto-Generating Mermaid Diagrams:** Asks for architecture or flow diagrams, and the AI correctly generates visual `.mermaid` diagrams in the chat.
* **Robust Session Management:** Beautiful interface to manage chat history: Pin, Favorite, Archive, Auto-Title, and Delete previous conversations.

---

## 🏗️ Tech Stack

**Frontend:**
- Clean HTML5, Vanilla JavaScript, and beautiful Vanilla CSS (incorporating modern glassmorphism and animations)
- Interactive, responsive, and app-like User Experience

**Backend:**
- **Python / Flask**: Robust, lightweight REST API
- **SQLite 3**: Embedded database mapping conversations, topics, and sessions
- **PyMuPDF**: Fast and reliable PDF parsing and text extraction

**AI Models & Integrations:**
- **Groq API**: Primary driver via `llama-3.3-70b-versatile` for blazing-fast inference
- **NVIDIA API**: Support for `gpt-oss-120b` for heavy reasoning
- **Ollama**: Local instance fallback via `deepseek-r1:8b`

---

## 🚀 Installation & Setup

Follow these steps to run the portal locally.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-cs-portal.git
cd ai-cs-portal
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add the following:
```env
SECRET_KEY="your-secure-session-secret"
PORT=5000

# API Keys for AI Models
GROQ_API_KEY="your-groq-api-key"
NVIDIA_API_KEY="your-nvidia-api-key"

# (Optional) Make sure Ollama is running dynamically on port 11434 if you want the local fallback running
```

### 5. Run the Application
```bash
python app.py
```
*The server will start at `http://localhost:5000`. Database tables and required upload directories are automatically generated on the first run.*

---

## 📖 Usage Modes

Navigate your portal to discover your learning styles:

1. **Standard Chat:** Talk to your tutor naturally. Paste code for debugging, ask Socratic questions.
2. **Panic Mode (Lightning Icon):** Select your university module from the dropdown to automatically build an emergency revision plan.
3. **Concept Clash (Swords Icon):** Input two separate algorithms or terms to generate a highly structured comparison table.
4. **Lecturer Mode (Graduation Cap Icon):** Attach a PDF or text snippet to have the AI dissect and simplify the academic jargon.

---

## 📁 Project Structure

```text
AI_CS_PORTAL/
├── database/            # SQLite databases (auto-generated)
├── static/
│   ├── index.html       # Primary portal interface
│   ├── main.js          # Client-side logic and API calls
│   └── style.css        # Animations, layouts, and theming
├── uploads/             # Temporary storage for PDF files
├── agent.py             # Core LLM logic, orchestration, and agents
├── app.py               # Flask application and routing
├── modules_context.py   # Embedded context maps for CS curriculum
├── pdf_reader.py        # PyMuPDF processing helper
├── requirements.txt     # Python dependencies
└── .env                 # Environment secrets
```

---

## 🤝 Contributing
Contributions are more than welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.

---
<div align="center">
Made with ❤️ to help students conquer Computer Science.
</div>
