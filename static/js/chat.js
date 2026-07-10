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
    const historyList = document.getElementById("history-list");

    // ── 状态 ──────────────────────────────────────────────
    let sessionId = localStorage.getItem("pc_session_id") || "";
    let isLoading = false;
    const STORAGE_PREFIX = "pc_session_";  // localStorage 键前缀
    const SESSIONS_INDEX_KEY = "pc_sessions_index";

    // ── 初始化 ────────────────────────────────────────────
    function init() {
        bindEvents();
        loadSessions();
        restoreChat();  // 从 localStorage 恢复当前会话的聊天记录
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
        // 自动保存到 localStorage
        saveChat();
    }

    function renderServerMessages(messages) {
        // 用服务器返回的消息列表重新渲染聊天区
        const welcome = document.querySelector(".welcome-banner");
        if (welcome) welcome.remove();

        // 清除现有消息（保留欢迎横幅除外）
        const existing = chatMessages.querySelectorAll(".message");
        existing.forEach(el => el.remove());

        messages.forEach(msg => {
            if (msg.role === "user") {
                appendMessageSilent("user", msg.content);
            } else if (msg.role === "assistant") {
                appendMessageSilent("bot", msg.content);
            }
        });
        saveChat();
    }

    function appendMessageSilent(role, content) {
        // 不带自动保存的 appendMessage（用于批量渲染，最后统一保存）
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

    // ── localStorage 持久化 ───────────────────────────────
    function saveChat() {
        // 保存当前页面的聊天 HTML 内容到 localStorage
        if (!sessionId) return;
        const messagesHtml = chatMessages.innerHTML;
        localStorage.setItem(STORAGE_PREFIX + sessionId, messagesHtml);
        // 更新会话索引
        updateSessionsIndex();
    }

    function restoreChat() {
        // 从 localStorage 恢复当前会话的聊天记录
        if (!sessionId) return;
        const saved = localStorage.getItem(STORAGE_PREFIX + sessionId);
        if (saved) {
            chatMessages.innerHTML = saved;
            scrollToBottom();
        }
    }

    function updateSessionsIndex() {
        // 维护所有本地会话的索引（用于下拉列表）
        if (!sessionId) return;
        let index = {};
        try {
            index = JSON.parse(localStorage.getItem(SESSIONS_INDEX_KEY) || "{}");
        } catch (e) { /* ignore */ }
        index[sessionId] = {
            updated_at: new Date().toISOString(),
            first_message: getFirstUserMessage(sessionId),
        };
        localStorage.setItem(SESSIONS_INDEX_KEY, JSON.stringify(index));
    }

    function getFirstUserMessage(sid) {
        // 从保存的 HTML 中提取第一条用户消息用于会话摘要
        try {
            const html = localStorage.getItem(STORAGE_PREFIX + sid);
            if (!html) return "";
            const match = html.match(/<div class="bubble user-bubble">([\s\S]*?)<\/div>/);
            if (match) {
                let text = match[1].replace(/<[^>]+>/g, "").trim();
                return text.substring(0, 30);
            }
        } catch (e) { /* ignore */ }
        return "";
    }

    function deleteLocalSession(sid) {
        localStorage.removeItem(STORAGE_PREFIX + sid);
        let index = {};
        try {
            index = JSON.parse(localStorage.getItem(SESSIONS_INDEX_KEY) || "{}");
        } catch (e) { /* ignore */ }
        delete index[sid];
        localStorage.setItem(SESSIONS_INDEX_KEY, JSON.stringify(index));
    }

    // ── 会话管理 ──────────────────────────────────────────
    async function handleNewSession() {
        // 先保存当前会话
        saveChat();

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

            saveChat();
            clearInputs();
            loadSessions();
        } catch (err) {
            console.error("新建会话失败:", err);
        }
    }

    async function switchSession(sid) {
        if (sid === sessionId) return;
        // 先保存当前会话
        saveChat();
        sessionId = sid;
        localStorage.setItem("pc_session_id", sessionId);

        // 先尝试从 localStorage 恢复
        const saved = localStorage.getItem(STORAGE_PREFIX + sessionId);
        if (saved) {
            chatMessages.innerHTML = saved;
            scrollToBottom();
        } else {
            // localStorage 没有，尝试从服务器加载
            try {
                const res = await fetch("/api/sessions/" + sid);
                const data = await res.json();
                if (data.messages && data.messages.length > 0) {
                    renderServerMessages(data.messages);
                }
            } catch (err) {
                // 都没有就显示欢迎页
                chatMessages.innerHTML = `
                    <div class="welcome-banner">
                        <div class="welcome-icon">🦊</div>
                        <h2>切换到这个会话</h2>
                        <p>聊天记录为空</p>
                    </div>`;
            }
        }

        loadSessions();
    }

    async function deleteSession(sid, e) {
        e.stopPropagation();  // 防止触发切换
        if (!confirm("确定删除这个会话吗？")) return;

        // 从 localStorage 删除
        deleteLocalSession(sid);

        // 从服务器删除
        try {
            await fetch("/api/sessions/" + sid, { method: "DELETE" });
        } catch (err) { /* ignore */ }

        // 如果删除的是当前会话，创建新会话
        if (sid === sessionId) {
            sessionId = "";
            localStorage.removeItem("pc_session_id");
            chatMessages.innerHTML = `
                <div class="welcome-banner">
                    <div class="welcome-icon">🦊</div>
                    <h2>你好！我是小码 👋</h2>
                    <p>你的编程学习伙伴，陪你一起探索代码的世界。</p>
                </div>`;
        }

        loadSessions();
    }

    function renderHistoryList(sessions) {
        if (!historyList) return;

        if (sessions.length === 0) {
            historyList.innerHTML = '<div class="history-empty">暂无历史会话</div>';
            return;
        }

        historyList.innerHTML = sessions.map(s => {
            const sid = s.session_id;
            const preview = s._preview || getFirstUserMessage(sid) || "(空会话)";
            const date = s.created_at
                ? new Date(s.created_at).toLocaleDateString("zh-CN")
                : "";
            const isActive = sid === sessionId ? " active" : "";
            return `
                <div class="history-item${isActive}" data-sid="${sid}" onclick="window._switchSessionHandler('${sid}')">
                    <span class="history-preview" title="${escapeHtml(preview)}">${escapeHtml(preview.substring(0, 25))}</span>
                    <span class="history-date">${date}</span>
                    <button class="history-delete" title="删除此会话" onclick="window._deleteSessionHandler('${sid}', event)">×</button>
                </div>`;
        }).join("");
    }

    async function loadSessions() {
        // 合并服务器会话列表和本地 localStorage 会话
        const sessions = [];

        // 从服务器加载
        try {
            const res = await fetch("/api/sessions");
            const data = await res.json();
            sessions.push(...(data.sessions || []));
        } catch (err) {
            console.error("加载服务器会话列表失败:", err);
        }

        // 从 localStorage 补充（可能有服务器上没有的）
        let localIndex = {};
        try {
            localIndex = JSON.parse(localStorage.getItem(SESSIONS_INDEX_KEY) || "{}");
        } catch (e) { /* ignore */ }

        Object.entries(localIndex).forEach(([sid, info]) => {
            if (!sessions.find(s => s.session_id === sid)) {
                sessions.push({
                    session_id: sid,
                    created_at: info.updated_at || "",
                    updated_at: info.updated_at || "",
                    message_count: 0,
                    _local: true,
                });
            }
        });

        sessions.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));

        // 更新下拉选择器
        sessionSelector.innerHTML = '<option value="">当前会话 (' + (sessionId ? sessionId.substring(0, 8) : "新") + '...)</option>';
        sessions.forEach((s) => {
            if (s.session_id === sessionId) return;
            const opt = document.createElement("option");
            opt.value = s.session_id;
            const date = s.created_at
                ? new Date(s.created_at).toLocaleDateString("zh-CN")
                : "";
            const local = s._local ? "💻" : "";
            const first = getFirstUserMessage(s.session_id) || "";
            const label = first ? first.substring(0, 20) : (s.message_count + "条消息");
            opt.textContent = `${local} ${date} · ${label}`;
            sessionSelector.appendChild(opt);
        });

        // 渲染侧边栏历史会话列表
        // 给每个 session 附上预览文本
        sessions.forEach(s => {
            s._preview = getFirstUserMessage(s.session_id) || "";
        });
        renderHistoryList(sessions);
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
    // 暴露到 window 供 onclick 属性调用（避免 addEventListener 的内存问题）
    window._switchSessionHandler = switchSession;
    window._deleteSessionHandler = deleteSession;
    init();
})();
