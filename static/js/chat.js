(function () {
  const messagesEl = document.getElementById("chat-messages");
  const messageInput = document.getElementById("message-input");
  const codeInput = document.getElementById("code-input");
  const errorInput = document.getElementById("error-input");
  const languageHint = document.getElementById("language-hint");
  const btnSend = document.getElementById("btn-send");
  const inputCount = document.getElementById("input-count");
  const codeCount = document.getElementById("code-count");
  const errorCount = document.getElementById("error-count");
  const contextSummary = document.getElementById("context-summary");
  const contextSummaryText = document.getElementById("context-summary-text");

  function createMessageElement(role, text, code = "", error = "") {
    const article = document.createElement("article");
    article.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = role === "bot" ? "码" : "我";

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = Markdown.render(text || "");

    if (code) {
      const pre = document.createElement("pre");
      pre.className = "code-block";
      const codeEl = document.createElement("code");
      codeEl.textContent = code;
      pre.appendChild(codeEl);
      content.appendChild(pre);
    }

    if (error) {
      const pre = document.createElement("pre");
      pre.className = "error-block";
      const codeEl = document.createElement("code");
      codeEl.textContent = error;
      pre.appendChild(codeEl);
      content.appendChild(pre);
    }

    article.append(avatar, content);
    return article;
  }

  function appendBubble(role, text, code = "", error = "") {
    removeEmptyState();
    const element = createMessageElement(role, text, code, error);
    messagesEl.appendChild(element);
    scrollToBottom();
    return element;
  }

  function appendMotivation(text) {
    if (!text) return;
    const note = document.createElement("div");
    note.className = "motivation-note";
    note.textContent = text;
    messagesEl.appendChild(note);
    scrollToBottom();
  }

  function renderEmptyState() {
    messagesEl.replaceChildren();
    const template = document.getElementById("empty-state-template");
    messagesEl.appendChild(template.content.cloneNode(true));
    messagesEl.querySelectorAll(".suggestion-card").forEach(button => {
      button.addEventListener("click", () => {
        messageInput.value = button.dataset.message || "";
        updateCounts();
        resizeMessageInput();
        messageInput.focus();
      });
    });
  }

  function removeEmptyState() {
    messagesEl.querySelector(".empty-state")?.remove();
  }

  function renderMessages(messages) {
    messagesEl.replaceChildren();
    if (!messages.length) {
      renderEmptyState();
      return;
    }
    messages.forEach(message => {
      appendBubble(message.role === "assistant" ? "bot" : "user", message.content, message.code, message.error_text);
      if (message.role === "assistant" && message.motivation_text) appendMotivation(message.motivation_text);
    });
    scrollToBottom(false);
  }

  function showTyping() {
    hideTyping();
    removeEmptyState();
    const article = document.createElement("article");
    article.id = "typing-indicator";
    article.className = "message bot typing";
    article.innerHTML = `
      <div class="message-avatar" aria-hidden="true">码</div>
      <div class="message-content" aria-label="小码正在思考">
        <div class="typing-lines"><span></span><span></span><span></span></div>
      </div>`;
    messagesEl.appendChild(article);
    scrollToBottom();
  }

  function hideTyping() {
    document.getElementById("typing-indicator")?.remove();
  }

  function setLoading(loading) {
    State.isLoading = loading;
    btnSend.disabled = loading;
    messageInput.disabled = loading;
    btnSend.setAttribute("aria-label", loading ? "正在等待回复" : "发送消息");
  }

  async function sendMessage() {
    const text = messageInput.value.trim();
    const code = codeInput.value.trim();
    const error = errorInput.value.trim();
    if ((!text && !code && !error) || State.isLoading) return;

    if (!State.currentConversationId) {
      await Conversations.ensureSession(text, code, error);
    }
    if (!State.currentConversationId) return;

    setLoading(true);
    appendBubble("user", text, code, error);
    messageInput.value = "";
    codeInput.value = "";
    errorInput.value = "";
    updateCounts();
    updateContextSummary();
    resizeMessageInput();
    showTyping();

    try {
      const result = await API.sendMessage(State.currentConversationId, {
        message: text,
        code,
        error,
        scene_hint: State.sceneHint,
        language_hint: languageHint.value,
        client_message_id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      });
      hideTyping();
      appendBubble("bot", result.reply);
      appendMotivation(result.motivation);
      await Conversations.loadSessions();
    } catch (errorObject) {
      hideTyping();
      UI.toast(errorObject.message || "暂时无法获取回复，请稍后重试", "error");
      appendBubble("bot", "这次请求没有成功。你的问题已经保留，可以稍后重新发送。 ");
    } finally {
      setLoading(false);
      messageInput.focus();
    }
  }

  function clearInputs() {
    messageInput.value = "";
    codeInput.value = "";
    errorInput.value = "";
    languageHint.value = "";
    State.languageHint = "";
    updateCounts();
    updateContextSummary();
    resizeMessageInput();
    messageInput.focus();
  }

  function updateContextSummary() {
    const parts = [];
    if (codeInput.value.trim()) parts.push(`已添加 ${codeInput.value.trim().split("\n").length} 行代码`);
    if (errorInput.value.trim()) parts.push("已添加报错信息");
    if (languageHint.value) parts.push(languageHint.options[languageHint.selectedIndex].text);
    contextSummary.hidden = parts.length === 0;
    contextSummaryText.textContent = parts.join("，");
  }

  function updateCounts() {
    inputCount.textContent = `${messageInput.value.length} / 5000`;
    codeCount.textContent = `${codeInput.value.length} / 10000`;
    errorCount.textContent = `${errorInput.value.length} / 5000`;
  }

  function resizeMessageInput() {
    messageInput.style.height = "auto";
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
  }

  function scrollToBottom(smooth = true) {
    messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }

  btnSend.addEventListener("click", sendMessage);
  messageInput.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  });
  messageInput.addEventListener("input", () => { updateCounts(); resizeMessageInput(); });
  codeInput.addEventListener("input", () => { updateCounts(); updateContextSummary(); });
  errorInput.addEventListener("input", () => { updateCounts(); updateContextSummary(); });
  languageHint.addEventListener("change", () => { State.languageHint = languageHint.value; updateContextSummary(); });

  window.Chat = {
    sendMessage,
    appendBubble,
    appendMotivation,
    renderMessages,
    renderEmptyState,
    clearInputs,
    updateContextSummary,
    showTyping,
    hideTyping,
  };
})();
