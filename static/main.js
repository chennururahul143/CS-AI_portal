document.addEventListener("DOMContentLoaded", function () {

    const sidebarToggle = document.getElementById("sidebar-toggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebar-overlay");
    const btnNewChat = document.getElementById("btn-new-chat");
    const textarea = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    const pdfInput = document.getElementById("pdf-input");
    const uploadBtn = document.getElementById("upload-btn");
    const pdfBanner = document.getElementById("pdf-banner");
    const pdfBannerText = document.getElementById("pdf-banner-text");
    const pdfClearBtn = document.getElementById("pdf-clear-btn");
    const typingIndicator = document.getElementById("typing-indicator");
    const sourceBadge = document.getElementById("source-badge");

    let pdfContext = null;
    let selectedModel = "groq";
    let isLanding = SHOW_LANDING;
    let mermaidLoaded = false;

    scrollToBottom();
    loadMermaid();

    /* ── MERMAID LOADER ── */
    function loadMermaid() {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
        script.onload = function () {
            mermaid.initialize({
                startOnLoad: false,
                theme: "default",
                securityLevel: "loose",
                flowchart: { useMaxWidth: true, htmlLabels: true },
                fontSize: 14
            });
            mermaidLoaded = true;
        };
        document.head.appendChild(script);
    }

    /* ── MERMAID SANITISER ── */
    function sanitiseMermaid(code) {
        let c = code.trim();
        c = c.replace(/^graph\s+LR/gm, "flowchart LR");
        c = c.replace(/^graph\s+TD/gm, "flowchart TD");
        c = c.replace(/-->\|([^|>]+)\|>/g, "-->|$1|");
        c = c.replace(/\bstyle\s+\w+[^\n]*/g, "");
        c = c.replace(/%%[^\n]*/g, "");
        c = c.replace(/\[ +/g, "[").replace(/ +\]/g, "]");
        return c.trim();
    }

    /* ── RENDER MERMAID ── */
    async function renderMermaid(container, code) {
        const sanitised = sanitiseMermaid(code);
        const id = "mermaid-" + Date.now() + "-" + Math.floor(Math.random() * 1000);
        try {
            const { svg } = await mermaid.render(id, sanitised);
            container.innerHTML = svg;
            container.style.cssText = "background:white;border:1px solid #e0e0e0;border-radius:10px;padding:16px;margin:10px 0;overflow-x:auto;";
        } catch (err) {
            container.innerHTML = `<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px;font-size:13px;color:#856404;">
        <strong>Diagram could not render.</strong> Raw syntax:<br><pre style="margin-top:8px;font-size:11px;white-space:pre-wrap;">${escapeHtml(sanitised)}</pre>
      </div>`;
        }
    }

    /* ── SIDEBAR TOGGLE ── */
    sidebarToggle.addEventListener("click", function () {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle("open");
            sidebarOverlay.classList.toggle("show");
        } else {
            sidebar.classList.toggle("collapsed");
        }
    });

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", function () {
            sidebar.classList.remove("open");
            sidebarOverlay.classList.remove("show");
        });
    }

    /* ── NEW CHAT ── */
    btnNewChat.addEventListener("click", function () {
        fetch("/clear", { method: "POST" })
            .then(() => window.location.replace("/?new=" + Date.now()));
    });

    /* ── MODEL SELECTION ── */
    window.selectModel = function (model) {
        const card = document.getElementById("model-" + model);
        if (!card || card.classList.contains("coming-soon")) return;
        selectedModel = model;
        document.querySelectorAll(".model-card").forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        updateSourceBadge(model);
    };

    /* ── SUGGESTION CARDS ── */
    window.startWithSuggestion = function (el) {
        const text = el.textContent.trim();
        switchToChat();
        textarea.value = text;
        textarea.dispatchEvent(new Event("input"));
        sendMessage();
    };

    /* ── LOAD SESSION FROM SIDEBAR ── */
    window.loadSession = function (sessionId) {
        window.location.href = "/session/" + sessionId;
    };

    /* ── SWITCH FROM LANDING TO CHAT ── */
    function switchToChat() {
        if (!isLanding) return;
        isLanding = false;
        const landing = document.getElementById("landing-screen");
        const contentArea = document.getElementById("content-area");
        if (landing) landing.remove();
        const chatScreen = document.createElement("div");
        chatScreen.className = "chat-screen";
        chatScreen.id = "chat-screen";
        chatScreen.innerHTML = `
      <div class="chat-messages" id="chat-messages">
        <div class="typing-indicator" id="typing-indicator">
          <div class="msg-avatar" style="background:var(--primary-light);color:var(--primary);">AI</div>
          <div>
            <div class="typing-dots"><span></span><span></span><span></span></div>
            <div class="typing-text">Thinking...</div>
          </div>
        </div>
      </div>`;
        contentArea.insertBefore(chatScreen, document.querySelector(".input-area"));
    }

    /* ── KEYBOARD ── */
    textarea.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    textarea.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });

    sendBtn.addEventListener("click", sendMessage);

    clearBtn.addEventListener("click", function () {
        if (!confirm("Clear this conversation?")) return;
        fetch("/clear", { method: "POST" })
            .then(() => window.location.replace("/?new=" + Date.now()));
    });

    /* ── PDF UPLOAD ── */
    uploadBtn.addEventListener("click", () => pdfInput.click());
    pdfInput.addEventListener("change", function () {
        const file = pdfInput.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append("pdf", file);
        switchToChat();
        appendSystemMessage("Reading PDF: " + file.name + "...");
        fetch("/upload", { method: "POST", body: formData })
            .then(r => r.json())
            .then(data => {
                if (data.error) { appendSystemMessage("PDF error: " + data.message); return; }
                pdfContext = data.pdf_context;
                pdfBannerText.textContent = "PDF loaded: " + file.name + " (" + data.char_count + " chars). Ask me anything about it.";
                pdfBanner.classList.add("show");
                appendSystemMessage("PDF ready. Ask your questions about it.");
            })
            .catch(() => appendSystemMessage("Failed to upload PDF."));
        pdfInput.value = "";
    });

    pdfClearBtn.addEventListener("click", function () {
        pdfContext = null;
        pdfBanner.classList.remove("show");
        appendSystemMessage("PDF cleared.");
    });

    /* ── SEND MESSAGE ── */
    function sendMessage() {
        const msg = textarea.value.trim();
        if (!msg) return;
        switchToChat();
        appendMessage("user", msg);
        textarea.value = "";
        textarea.style.height = "auto";
        setLoading(true);

        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg, pdf_context: pdfContext, model: selectedModel })
        })
            .then(r => r.json())
            .then(data => {
                setLoading(false);
                if (data.error) {
                    appendMessage("assistant", "Sorry, something went wrong: " + data.message, "none");
                } else {
                    appendMessage("assistant", data.reply, data.source);
                    updateSourceBadge(data.source);
                    refreshSidebar();
                }
            })
            .catch(() => {
                setLoading(false);
                appendMessage("assistant", "Network error. Please check your connection.", "none");
            });
    }

    /* ── APPEND MESSAGE ── */
    async function appendMessage(role, content, source) {
        const msgs = document.getElementById("chat-messages");
        if (!msgs) return;
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        const div = document.createElement("div");
        div.className = "msg " + role;

        let metaText = now;
        if (source && role === "assistant") {
            const labels = { groq: "Groq (fast)", ollama: "Ollama (local)", openai: "OpenAI 120B" };
            metaText += " · " + (labels[source] || "Error");
        }

        if (role === "assistant") {
            const parsed = parseDiagram(content);
            const bubbleHTML = formatMarkdown(parsed.text);

            div.innerHTML = `
        <div class="msg-avatar">AI</div>
        <div>
          <div class="msg-bubble" id="bubble-${now.replace(/:/g, '')}${Math.random().toString(36).slice(2, 6)}">${bubbleHTML}</div>
          <div class="msg-meta">${metaText}</div>
        </div>`;

            const typing = document.getElementById("typing-indicator");
            if (typing) msgs.insertBefore(div, typing);
            else msgs.appendChild(div);

            if (parsed.diagram && mermaidLoaded) {
                const diagramDiv = document.createElement("div");
                diagramDiv.className = "msg assistant";
                diagramDiv.innerHTML = `<div class="msg-avatar">AI</div><div id="diagram-container-${Date.now()}"></div>`;
                if (typing) msgs.insertBefore(diagramDiv, typing);
                else msgs.appendChild(diagramDiv);
                const container = diagramDiv.querySelector("div:last-child");
                await renderMermaid(container, parsed.diagram);
            }

        } else {
            div.innerHTML = `
        <div class="msg-avatar">S</div>
        <div>
          <div class="msg-bubble">${escapeHtml(content)}</div>
          <div class="msg-meta">${metaText}</div>
        </div>`;
            const typing = document.getElementById("typing-indicator");
            if (typing) msgs.insertBefore(div, typing);
            else msgs.appendChild(div);
        }

        scrollToBottom();
    }

    /* ── PARSE DIAGRAM FROM AI RESPONSE ── */
    function parseDiagram(content) {
        const diagramRegex = /DIAGRAM:\s*```mermaid\s*([\s\S]*?)```/i;
        const match = content.match(diagramRegex);
        if (match) {
            const text = content.replace(diagramRegex, "").trim();
            return { text, diagram: match[1].trim() };
        }
        const mermaidOnly = /```mermaid\s*([\s\S]*?)```/i;
        const m2 = content.match(mermaidOnly);
        if (m2) {
            const text = content.replace(mermaidOnly, "").trim();
            return { text, diagram: m2[1].trim() };
        }
        return { text: content, diagram: null };
    }

    function appendSystemMessage(text) {
        const msgs = document.getElementById("chat-messages");
        if (!msgs) return;
        const div = document.createElement("div");
        div.style.cssText = "text-align:center;font-size:12px;color:#aaa;padding:4px 0;";
        div.textContent = text;
        msgs.appendChild(div);
        scrollToBottom();
    }

    function setLoading(on) {
        sendBtn.disabled = on;
        textarea.disabled = on;
        const t = document.getElementById("typing-indicator");
        if (t) t.classList.toggle("show", on);
        if (on) scrollToBottom();
    }

    function updateSourceBadge(source) {
        if (!sourceBadge) return;
        sourceBadge.className = "source-badge source-" + (["groq", "ollama", "openai", "nvidia"].includes(source) ? source : "none");
        const labels = { groq: "Groq · Fast", ollama: "Ollama · Local", openai: "OpenAI · 120B" };
        sourceBadge.textContent = labels[source] || "Error";
    }

    function scrollToBottom() {
        const msgs = document.getElementById("chat-messages");
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }

    function refreshSidebar() {
        fetch("/sidebar")
            .then(r => r.text())
            .then(html => {
                const list = document.getElementById("chat-list");
                if (list) list.innerHTML = html;
            });
    }

    function escapeHtml(t) {
        return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
    }

    function formatMarkdown(text) {
        text = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        text = text.replace(/```[\w]*\n?([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
        text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
        text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
        text = text.replace(/^#{1,3}\s(.+)$/gm, "<strong>$1</strong>");
        text = text.replace(/^\d+\.\s(.+)$/gm, "<li>$1</li>");
        text = text.replace(/(<li>.*<\/li>(\n|<br>)*)+/g, "<ol>$&</ol>");
        text = text.replace(/^[-*]\s(.+)$/gm, "<li>$1</li>");
        text = text.replace(/\n{2,}/g, "<br><br>");
        text = text.replace(/\n/g, "<br>");
        return text;
    }
});

/* ── STUDY TOOLS ── */
window.openTool = function (tool) {
    document.getElementById("modal-" + tool).classList.add("show");
    if (tool === "clash") {
        setTimeout(() => document.getElementById("clash-concept1").focus(), 100);
    }
    if (tool === "panic") {
        setTimeout(() => document.getElementById("panic-module").focus(), 100);
    }
};

window.closeTool = function (tool) {
    document.getElementById("modal-" + tool).classList.remove("show");
};

document.querySelectorAll(".tool-modal-backdrop").forEach(function (backdrop) {
    backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop) {
            backdrop.classList.remove("show");
        }
    });
});

document.getElementById("lecturer-pdf").addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
        document.getElementById("lecturer-pdf-name").textContent = "Selected: " + file.name;
    }
});

window.submitPanic = function () {
    const module = document.getElementById("panic-module").value;
    const topic = document.getElementById("panic-topic").value.trim();
    if (!module) { alert("Please select a module."); return; }
    closeTool("panic");
    switchToChat();
    appendUserToolMessage("Exam Panic Mode — " + module + (topic ? " · " + topic : ""), "panic");
    setLoading(true);
    fetch("/tool/panic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module, topic, model: selectedModel })
    })
        .then(r => r.json())
        .then(data => {
            setLoading(false);
            if (data.error) { appendMessage("assistant", "Error: " + data.message, "none"); return; }
            appendToolMessage(data.reply, data.source, "panic");
            updateSourceBadge(data.source);
            refreshSidebar();
        })
        .catch(() => { setLoading(false); appendMessage("assistant", "Network error.", "none"); });
};

window.submitClash = function () {
    const c1 = document.getElementById("clash-concept1").value.trim();
    const c2 = document.getElementById("clash-concept2").value.trim();
    if (!c1 || !c2) { alert("Please enter both concepts."); return; }
    closeTool("clash");
    switchToChat();
    appendUserToolMessage("Concept Clash: " + c1 + " vs " + c2, "clash");
    setLoading(true);
    fetch("/tool/clash", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept1: c1, concept2: c2, model: selectedModel })
    })
        .then(r => r.json())
        .then(data => {
            setLoading(false);
            if (data.error) { appendMessage("assistant", "Error: " + data.message, "none"); return; }
            appendToolMessage(data.reply, data.source, "clash");
            updateSourceBadge(data.source);
            refreshSidebar();
        })
        .catch(() => { setLoading(false); appendMessage("assistant", "Network error.", "none"); });
};

window.submitLecturer = function () {
    const pdfFile = document.getElementById("lecturer-pdf").files[0];
    const text = document.getElementById("lecturer-text").value.trim();
    if (!pdfFile && !text) { alert("Please upload a PDF or paste some text."); return; }
    closeTool("lecturer");
    switchToChat();
    appendUserToolMessage("Explain My Lecturer — " + (pdfFile ? pdfFile.name : "pasted content"), "lecturer");
    setLoading(true);
    const formData = new FormData();
    if (pdfFile) formData.append("pdf", pdfFile);
    if (text) formData.append("text", text);
    formData.append("model", selectedModel);
    fetch("/tool/lecturer", { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            setLoading(false);
            if (data.error) { appendMessage("assistant", "Error: " + data.message, "none"); return; }
            appendToolMessage(data.reply, data.source, "lecturer");
            updateSourceBadge(data.source);
            refreshSidebar();
        })
        .catch(() => { setLoading(false); appendMessage("assistant", "Network error.", "none"); });
};

function appendUserToolMessage(text, tool) {
    const msgs = document.getElementById("chat-messages");
    if (!msgs) return;
    const icons = { panic: "&#128680;", clash: "&#9889;", lecturer: "&#128214;" };
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = `
    <div class="msg-avatar">S</div>
    <div>
      <div class="msg-bubble">${icons[tool] || ""} ${escapeHtml(text)}</div>
      <div class="msg-meta">${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
    </div>`;
    const typing = document.getElementById("typing-indicator");
    if (typing) msgs.insertBefore(div, typing); else msgs.appendChild(div);
    scrollToBottom();
}

function appendToolMessage(content, source, tool) {
    const msgs = document.getElementById("chat-messages");
    if (!msgs) return;
    const labels = { groq: "Groq (fast)", ollama: "Ollama (local)", nvidia: "NVIDIA 120B" };
    const tagLabels = { panic: "Exam Panic Mode", clash: "Concept Clash", lecturer: "Explain My Lecturer" };
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const parsed = parseDiagram(content);
    const div = document.createElement("div");
    div.className = "msg assistant";
    div.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div>
      <div class="msg-bubble">
        <div class="tool-tag ${tool}">${tagLabels[tool] || tool}</div>
        ${formatMarkdown(parsed.text)}
      </div>
      <div class="msg-meta">${now} · ${labels[source] || source}</div>
    </div>`;
    const typing = document.getElementById("typing-indicator");
    if (typing) msgs.insertBefore(div, typing); else msgs.appendChild(div);
    if (parsed.diagram && mermaidLoaded) {
        const dDiv = document.createElement("div");
        dDiv.className = "msg assistant";
        dDiv.innerHTML = `<div class="msg-avatar">AI</div><div id="dc-${Date.now()}"></div>`;
        if (typing) msgs.insertBefore(dDiv, typing); else msgs.appendChild(dDiv);
        renderMermaid(dDiv.querySelector("div:last-child"), parsed.diagram);
    }
    scrollToBottom();
}

function escapeHtml(t) {
    return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
}