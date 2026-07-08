/*
 * 小码编程学伴 — 聊天交互逻辑
 * 零依赖，纯原生 JS
 */

(function () {
    "use strict";

    // ── DOM 引用 ──────────────────────────────────────────
    const chatMessages = document.getElementById("chat-messages");
    const messageInput = document.getElementById("message-input");
    const codeInput = document.getElementById("code-input");
    const errorInput = document.getElementById("error-input");
    const btnSend = document.getElementById("btn-send");
    const btnNewSession = document.getElementById("btn-new-session");
    const btnTogglePanel = document.getElementById("btn-toggle-panel");
    const btnClearInputs = document.getElementById("btn-clear-inputs");
    const sessionSelector = document.getElementById("session-selector");
    const sidePanel = document.getElementById("side-panel");

    // ── 状态 ──────────────────────────────────────────────
    let sessionId = localStorage.getItem("pc_session_id") || "";
    let isLoading = false;

    // ── 初始化 ────────────────────────────────────────────
    function init() {
        bindEvents();
        loadSessions();
    }

    function bindEvents() {
        // 发送按钮
        btnSend.addEventListener("click", handleSend);
        // Ctrl + Enter 发送
        messageInput.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                handleSend();
            }
        });

        // 新建会话
        btnNewSession.addEventListener("click", handleNewSession);

        // 侧边栏切换
        btnTogglePanel.addEventListener("click", togglePanel);

        // 清除输入
        btnClearInputs.addEventListener("click", clearInputs);

        // 会话切换
        sessionSelector.addEventListener("change", (e) => {
            if (e.target.value) {
                switchSession(e.target.value);
            }
        });

        // 欢迎提示 chips
        document.querySelectorAll(".tip-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                messageInput.value = chip.dataset.message;
                messageInput.focus();
            });
        });

        // 快捷场景 chips
        document.querySelectorAll(".action-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                document.querySelectorAll(".action-chip").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
            });
        });
    }

    // ── 发送消息 ──────────────────────────────────────────
    async function handleSend() {
        if (isLoading) return;

        const message = messageInput.value.trim();
        const code = codeInput.value.trim();
        const error = errorInput.value.trim();

        if (!message && !code && !error) return;

        // 禁用输入
        isLoading = true;
        btnSend.disabled = true;
        messageInput.disabled = true;

        // 移除欢迎横幅
        const welcome = document.querySelector(".welcome-banner");
        if (welcome) welcome.remove();

        // 渲染用户消息
        const userContent = buildUserDisplay(message, code, error);
        appendMessage("user", userContent);

        // 清空输入
        messageInput.value = "";
        codeInput.value = "";
        errorInput.value = "";

        // 显示打字动画
        const typingEl = showTyping();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    code: code,
                    error: error,
                    session_id: sessionId,
                }),
            });

            const data = await response.json();

            // 隐藏打字动画
            hideTyping(typingEl);

            if (data.error && !data.reply) {
                appendMessage("bot", "❌ " + data.error);
            } else {
                appendMessage("bot", data.reply);
            }

            // 更新 session_id
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem("pc_session_id", sessionId);
                loadSessions();
            }
        } catch (err) {
            hideTyping(typingEl);
            appendMessage("bot", "😥 抱歉，网络连接出现了问题。请检查网络后重试。\n\n*（确认 config.py 中已设置正确的 DEEPSEEK_API_KEY）*");
        }

        // 恢复输入
        isLoading = false;
        btnSend.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }

    // ── 消息渲染 ──────────────────────────────────────────
    function buildUserDisplay(message, code, error) {
        const parts = [];
        if (message) parts.push("<p>" + escapeHtml(message) + "</p>");
        if (code) {
            parts.push(
                '<div class="code-block-label">💻 代码</div>' +
                "<pre><code>" + escapeHtml(code) + "</code></pre>"
            );
        }
        if (error) {
            parts.push(
                '<div class="code-block-label">⚠️ 错误信息</div>' +
                "<pre><code>" + escapeHtml(error) + "</code></pre>"
            );
        }
        return parts.join("");
    }

    function appendMessage(role, content) {
        const div = document.createElement("div");
        div.className = "message " + role;

        if (role === "user") {
            div.innerHTML =
                '<div class="avatar user-avatar">🧑</div>' +
                '<div class="bubble user-bubble">' + content + "</div>";
        } else {
            const htmlContent = renderMarkdown(content);
            div.innerHTML =
                '<div class="avatar bot-avatar">🦊</div>' +
                '<div class="bubble bot-bubble">' + htmlContent + "</div>";
        }

        chatMessages.appendChild(div);
        scrollToBottom();
    }

    // ── Markdown 渲染（纯 JS，零依赖）───────────────────
    function renderMarkdown(text) {
        if (!text) return "";

        let html = escapeHtml(text);

        // 代码块 ```lang\ncode\n```
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            return "<pre><code>" + code.trim() + "</code></pre>";
        });

        // 行内代码 `code`
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

        // 粗体 **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        // 斜体 *text*
        html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

        // 分隔线 ---
        html = html.replace(/^---$/gm, "<hr>");

        // 无序列表 - item 或 * item
        html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

        // 换行
        html = html.replace(/\n\n/g, "</p><p>");
        html = html.replace(/\n/g, "<br>");

        // 包裹段落
        html = "<p>" + html + "</p>";

        // 清理空段落
        html = html.replace(/<p><\/p>/g, "");

        return html;
    }

    // ── 打字动画 ──────────────────────────────────────────
    function showTyping() {
        const div = document.createElement("div");
        div.className = "message bot";
        div.innerHTML =
            '<div class="avatar bot-avatar">🦊</div>' +
            '<div class="bubble typing-bubble">' +
            '<span class="dot"></span><span class="dot"></span><span class="dot"></span>' +
            "</div>";
        chatMessages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function hideTyping(el) {
        if (el && el.parentNode) {
            el.remove();
        }
    }

    // ── 会话管理 ──────────────────────────────────────────
    async function handleNewSession() {
        try {
            const res = await fetch("/api/sessions/new", { method: "POST" });
            const data = await res.json();
            sessionId = data.session_id;
            localStorage.setItem("pc_session_id", sessionId);

            // 清空聊天区
            chatMessages.innerHTML = `
                <div class="welcome-banner">
                    <div class="welcome-icon">🦊</div>
                    <h2>新对话开始了！</h2>
                    <p>有什么我可以帮你的吗？</p>
                </div>`;

            clearInputs();
            loadSessions();
        } catch (err) {
            console.error("新建会话失败:", err);
        }
    }

    async function switchSession(sid) {
        sessionId = sid;
        localStorage.setItem("pc_session_id", sessionId);
        // 刷新页面以加载对话历史
        location.reload();
    }

    async function loadSessions() {
        try {
            const res = await fetch("/api/sessions");
            const data = await res.json();
            const sessions = data.sessions || [];

            sessionSelector.innerHTML = '<option value="">当前会话</option>';
            sessions.forEach((s) => {
                const opt = document.createElement("option");
                opt.value = s.session_id;
                const date = s.created_at
                    ? new Date(s.created_at).toLocaleDateString("zh-CN")
                    : "";
                opt.textContent = `${date} · ${s.message_count}条消息`;
                if (s.session_id === sessionId) {
                    opt.selected = true;
                }
                sessionSelector.appendChild(opt);
            });
        } catch (err) {
            console.error("加载会话列表失败:", err);
        }
    }

    // ── 辅助 ──────────────────────────────────────────────
    function clearInputs() {
        messageInput.value = "";
        codeInput.value = "";
        errorInput.value = "";
        messageInput.focus();
    }

    function togglePanel() {
        sidePanel.classList.toggle("collapsed");
        const btn = btnTogglePanel;
        if (sidePanel.classList.contains("collapsed")) {
            btn.textContent = "▶";
            btn.title = "展开面板";
        } else {
            btn.textContent = "◀";
            btn.title = "收起面板";
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(text) {
        const map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        };
        return text.replace(/[&<>"']/g, (c) => map[c]);
    }

    // ── 启动 ──────────────────────────────────────────────
    init();
})();
