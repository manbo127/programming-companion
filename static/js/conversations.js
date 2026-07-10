(function () {
  const shell = document.getElementById("app-shell");
  const listEl = document.getElementById("conversation-list");
  const countEl = document.getElementById("conversation-count");
  const titleEl = document.getElementById("current-conversation-title");
  const titleButton = document.getElementById("btn-rename-session");
  const titleInput = document.getElementById("conversation-title-input");
  const menuButton = document.getElementById("btn-conversation-menu");
  const menu = document.getElementById("conversation-menu");

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
    countEl.textContent = String(State.conversations.length).padStart(2, "0");

    if (!State.conversations.length) {
      const empty = document.createElement("p");
      empty.className = "conversation-list-empty";
      empty.textContent = "发送第一条消息后，对话会自动保存在这里。";
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
      title.textContent = conversation.title || "新的对话";
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

  function closeMenu() {
    menu.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
  }

  function updateHeader() {
    const active = Boolean(State.currentConversationId);
    const title = State.currentConversationTitle || "新的对话";
    titleEl.textContent = title;
    document.title = active ? `${title} · 小码` : "小码 · 程序设计学习智能学伴";
    titleButton.disabled = !active;
    menuButton.disabled = !active;
    if (!active) closeMenu();
    renderList();
  }

  function setHomeMode(home) {
    shell.classList.toggle("home-mode", home);
  }

  async function loadSessions() {
    try {
      State.conversations = await API.listConversations() || [];
      const current = State.currentConversation();
      if (current) State.currentConversationTitle = current.title || "新的对话";
      updateHeader();
      return State.conversations;
    } catch (error) {
      UI.toast(error.message || "无法加载历史对话", "error");
      return [];
    }
  }

  function showHome() {
    State.setCurrentConversation(null);
    setHomeMode(true);
    Chat.renderEmptyState();
    updateHeader();
    closeNavigation();
    closeMenu();
    document.getElementById("message-input").focus();
  }

  function newSession() {
    Chat.clearInputs();
    showHome();
    return null;
  }

  function suggestedTitle(text, code, error) {
    const cleaned = (text || "").replace(/\s+/g, " ").trim();
    if (cleaned) return cleaned.slice(0, 50);
    if (error) return "代码报错分析";
    if (code) return "代码问题分析";
    return "新的对话";
  }

  async function ensureSession(text = "", code = "", error = "") {
    if (State.currentConversationId) return State.currentConversation();
    try {
      const conversation = await API.createConversation(suggestedTitle(text, code, error));
      State.setCurrentConversation(conversation);
      setHomeMode(false);
      Chat.renderEmptyState();
      await loadSessions();
      updateHeader();
      return conversation;
    } catch (requestError) {
      UI.toast(requestError.message || "创建对话失败", "error");
      return null;
    }
  }

  async function switchSession(id) {
    if (!id) return;
    if (id === State.currentConversationId && !shell.classList.contains("home-mode")) {
      closeNavigation();
      return;
    }

    const conversation = State.conversations.find(item => item.id === id) || { id, title: "新的对话" };
    State.setCurrentConversation(conversation);
    setHomeMode(false);
    updateHeader();
    Chat.showTyping();

    try {
      const messages = await API.getMessages(id);
      Chat.hideTyping();
      Chat.renderMessages(messages || []);
      closeNavigation();
    } catch (error) {
      Chat.hideTyping();
      UI.toast(error.message || "无法加载这段对话", "error");
      Chat.renderEmptyState();
    }
  }

  function beginRename() {
    if (!State.currentConversationId) return;
    closeMenu();
    titleButton.hidden = true;
    titleInput.hidden = false;
    titleInput.value = State.currentConversationTitle || "";
    titleInput.focus();
    titleInput.select();
  }

  function cancelRename() {
    titleInput.hidden = true;
    titleButton.hidden = false;
  }

  async function saveRename() {
    if (titleInput.hidden || !State.currentConversationId) return;
    const nextTitle = titleInput.value.replace(/\s+/g, " ").trim();
    if (!nextTitle) {
      UI.toast("对话名称不能为空", "error");
      titleInput.focus();
      return;
    }
    if (nextTitle === State.currentConversationTitle) {
      cancelRename();
      return;
    }

    titleInput.disabled = true;
    try {
      const updated = await API.updateConversation(State.currentConversationId, { title: nextTitle });
      State.currentConversationTitle = updated.title;
      const current = State.conversations.find(item => item.id === State.currentConversationId);
      if (current) current.title = updated.title;
      cancelRename();
      updateHeader();
      UI.toast("对话名称已更新");
    } catch (error) {
      UI.toast(error.message || "对话名称修改失败", "error");
      titleInput.focus();
    } finally {
      titleInput.disabled = false;
    }
  }

  async function deleteCurrent() {
    if (!State.currentConversationId) return;
    closeMenu();
    const confirmed = await UI.confirm("删除当前对话？", "这段对话及其中的代码和报错记录会被永久删除。 ");
    if (!confirmed) return;

    try {
      await API.deleteConversation(State.currentConversationId);
      State.setCurrentConversation(null);
      await loadSessions();
      showHome();
      UI.toast("对话已删除");
    } catch (error) {
      UI.toast(error.message || "删除对话失败", "error");
    }
  }

  function setNavigation(open) {
    document.body.classList.toggle("navigation-open", open);
    document.getElementById("navigation-scrim").hidden = !open;
    document.getElementById("conversation-sidebar").setAttribute("aria-hidden", String(!open));
    document.getElementById("btn-toggle-history").setAttribute("aria-expanded", String(open));
  }

  function openNavigation() { setNavigation(true); }
  function toggleNavigation() { setNavigation(!document.body.classList.contains("navigation-open")); }
  function closeNavigation() { setNavigation(false); }
  function closeMobileNavigation() { closeNavigation(); }

  document.getElementById("btn-new-session").addEventListener("click", newSession);
  document.getElementById("btn-new-session-rail").addEventListener("click", newSession);
  document.getElementById("btn-home").addEventListener("click", showHome);
  document.getElementById("btn-toggle-history").addEventListener("click", toggleNavigation);
  document.getElementById("btn-delete-session").addEventListener("click", deleteCurrent);
  titleButton.addEventListener("click", beginRename);
  document.getElementById("menu-rename-session").addEventListener("click", beginRename);
  titleInput.addEventListener("keydown", event => {
    if (event.key === "Enter") { event.preventDefault(); saveRename(); }
    if (event.key === "Escape") { event.preventDefault(); cancelRename(); }
  });
  titleInput.addEventListener("blur", saveRename);
  menuButton.addEventListener("click", event => {
    event.stopPropagation();
    const open = menu.hidden;
    menu.hidden = !open;
    menuButton.setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("click", event => {
    if (!event.target.closest(".conversation-menu-wrap")) closeMenu();
  });

  window.Conversations = {
    loadSessions,
    newSession,
    showHome,
    ensureSession,
    switchSession,
    deleteCurrent,
    updateHeader,
    openNavigation,
    closeMobileNavigation,
  };
})();
