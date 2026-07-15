(function () {
  const shell = document.getElementById("app-shell");
  const sidePanel = document.getElementById("side-panel");
  const backdrop = document.getElementById("sheet-backdrop");
  const confirmDialog = document.getElementById("confirm-dialog");
  const sceneLabels = {
    "": "自动识别",
    error: "错误解读",
    guidance: "思路引导",
    knowledge: "知识讲解",
    general: "自由交流",
  };

  function setContextPanel(open) {
    if (open) Conversations.closeMobileNavigation();
    shell.classList.toggle("context-closed", !open);
    sidePanel.setAttribute("aria-hidden", String(!open));
    document.getElementById("btn-toggle-panel").setAttribute("aria-expanded", String(open));
  }

  function openSheet(panel) {
    Conversations.closeMobileNavigation();
    closeSheets();
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    backdrop.hidden = false;
  }

  function closeSheets() {
    document.querySelectorAll(".utility-sheet").forEach(panel => {
      panel.hidden = true;
      panel.setAttribute("aria-hidden", "true");
    });
    backdrop.hidden = true;
  }

  function toast(message, type = "success") {
    const region = document.getElementById("toast-region");
    const element = document.createElement("div");
    element.className = `toast ${type}`;
    element.textContent = message;
    region.appendChild(element);
    setTimeout(() => element.remove(), 3600);
  }

  function confirm(title, message) {
    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-message").textContent = message;
    confirmDialog.showModal();
    return new Promise(resolve => {
      confirmDialog.addEventListener("close", () => resolve(confirmDialog.returnValue === "confirm"), { once: true });
    });
  }

  window.UI = { setContextPanel, openSheet, closeSheets, toast, confirm };

  document.getElementById("btn-toggle-panel").addEventListener("click", () => {
    setContextPanel(shell.classList.contains("context-closed"));
  });
  document.getElementById("btn-open-context").addEventListener("click", () => setContextPanel(true));
  document.getElementById("btn-close-panel").addEventListener("click", () => setContextPanel(false));
  document.getElementById("btn-clear-inputs").addEventListener("click", Chat.clearInputs);
  document.getElementById("btn-clear-context").addEventListener("click", Chat.clearInputs);

  document.querySelectorAll(".action-chip").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".action-chip").forEach(item => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      State.sceneHint = button.dataset.mode || "";
      document.getElementById("scene-status").textContent = sceneLabels[State.sceneHint];
    });
  });

  const navigationScrim = document.getElementById("navigation-scrim");
  document.getElementById("btn-open-navigation").addEventListener("click", Conversations.openNavigation);
  document.getElementById("btn-close-navigation").addEventListener("click", Conversations.closeMobileNavigation);
  navigationScrim.addEventListener("click", Conversations.closeMobileNavigation);
  backdrop.addEventListener("click", closeSheets);

  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      Conversations.newSession();
    }
    if (event.key === "Escape") {
      closeSheets();
      Conversations.closeMobileNavigation();
      if (window.innerWidth <= 860) setContextPanel(false);
    }
  });

  async function init() {
    Chat.renderEmptyState();
    setContextPanel(false);

    try {
      const bootstrap = await API.bootstrap();
      Account.apply(bootstrap.account || {});
      Profile.applyProfile(bootstrap.profile || {});
      await Conversations.loadSessions();
      Conversations.showHome();
      await Learning.refreshBadge();
    } catch (error) {
      UI.toast(error.message || "应用初始化失败，请刷新页面重试", "error");
      Chat.renderEmptyState();
    }
  }

  init();
})();
