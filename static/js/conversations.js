(function () {
  const listEl = document.getElementById("conversation-list");
  const countEl = document.getElementById("conversation-count");
  const titleEl = document.getElementById("current-conversation-title");
  const deleteButton = document.getElementById("btn-delete-session");

  function relativeTime(value) {
    if (!value) return "刚刚";
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
    const date = new Date(hasTimezone ? value : `${value}Z`);
    const diff = Date.now() - date.getTime();
    if (!Number.isFinite(diff) || diff < 60000) return "刚刚";
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`;
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  }

  function renderList() {
    listEl.replaceChildren();
    countEl.textContent = String(State.conversations.length);

    if (!State.conversations.length) {
      const empty = document.createElement("p");
      empty.className = "conversation-list-empty";
      empty.textContent = "新建一段对话，记录会保存在这里。";
      listEl.appendChild(empty);
      return;
    }

    State.conversations.forEach(conversation => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `conversation-item${conversation.id === State.currentConversationId ? " active" : ""}`;
      button.dataset.conversationId = conversation.id;
      button.setAttribute("aria-current", conversation.id === State.currentConversationId ? "page" : "false");

      const title = document.createElement("strong");
      title.textContent = conversation.title || "未命名对话";
      const time = document.createElement("small");
      time.textContent = relativeTime(conversation.updated_at);
      const count = document.createElement("span");
      count.className = "message-count";
      count.textContent = String(conversation.message_count || 0);

      button.append(title, time, count);
      button.addEventListener("click", () => switchSession(conversation.id));
      listEl.appendChild(button);
    });
  }

  function updateHeader() {
    titleEl.textContent = State.currentConversationTitle || "新对话";
    document.title = `${State.currentConversationTitle || "新对话"} - 小码`;
    deleteButton.disabled = !State.currentConversationId;
    renderList();
  }

  async function loadSessions() {
    try {
      State.conversations = await API.listConversations() || [];
      const current = State.currentConversation();
      if (current) State.currentConversationTitle = current.title || "新对话";
      updateHeader();
      return State.conversations;
    } catch (error) {
      UI.toast(error.message || "无法加载会话列表", "error");
      return [];
    }
  }

  async function newSession() {
    try {
      const conversation = await API.createConversation();
      State.setCurrentConversation({ ...conversation, title: conversation.title || "新对话" });
      Chat.renderEmptyState();
      await loadSessions();
      updateHeader();
      closeMobileNavigation();
      document.getElementById("message-input").focus();
      return conversation;
    } catch (error) {
      UI.toast(error.message || "创建对话失败", "error");
      return null;
    }
  }

  async function switchSession(id) {
    if (!id || (id === State.currentConversationId && !document.querySelector(".empty-state"))) {
      closeMobileNavigation();
      return;
    }

    const conversation = State.conversations.find(item => item.id === id) || { id, title: "对话" };
    State.setCurrentConversation(conversation);
    updateHeader();
    Chat.showTyping();

    try {
      const messages = await API.getMessages(id);
      Chat.hideTyping();
      Chat.renderMessages(messages || []);
      closeMobileNavigation();
    } catch (error) {
      Chat.hideTyping();
      UI.toast(error.message || "无法加载这段对话", "error");
      Chat.renderEmptyState();
    }
  }

  async function deleteCurrent() {
    if (!State.currentConversationId) return;
    const confirmed = await UI.confirm("删除当前对话？", "这段对话及其中的代码和报错记录都会被删除，操作无法撤销。");
    if (!confirmed) return;

    try {
      await API.deleteConversation(State.currentConversationId);
      State.setCurrentConversation(null);
      const conversations = await loadSessions();
      if (conversations.length) {
        await switchSession(conversations[0].id);
      } else {
        await newSession();
      }
      UI.toast("对话已删除");
    } catch (error) {
      UI.toast(error.message || "删除对话失败", "error");
    }
  }

  function closeMobileNavigation() {
    document.body.classList.remove("navigation-open");
    document.getElementById("navigation-scrim").hidden = true;
  }

  document.getElementById("btn-new-session").addEventListener("click", newSession);
  document.getElementById("btn-delete-session").addEventListener("click", deleteCurrent);

  window.Conversations = { loadSessions, newSession, switchSession, deleteCurrent, updateHeader, closeMobileNavigation };
})();
