(function () {
  const panel = document.getElementById("profile-panel");
  const form = document.getElementById("profile-form");
  const nickname = document.getElementById("profile-nickname");
  const level = document.getElementById("profile-level");
  const languages = document.getElementById("profile-langs");
  const goal = document.getElementById("profile-goal");
  const feedbackStyle = document.getElementById("profile-feedback-style");
  const memoryEnabled = document.getElementById("profile-memory-enabled");
  const memorySummary = document.getElementById("profile-memory-summary");
  const memoryMeta = document.getElementById("profile-memory-meta");
  const memoryRefresh = document.getElementById("profile-memory-refresh");
  const memoryClear = document.getElementById("profile-memory-clear");
  const sidebarName = document.getElementById("sidebar-profile-name");

  function applyProfile(profile) {
    State.profile = profile || {};
    nickname.value = profile?.nickname || "";
    level.value = profile?.skill_level || "beginner";
    languages.value = profile?.preferred_languages || "";
    goal.value = profile?.learning_goal || "";
    feedbackStyle.value = profile?.feedback_style || "balanced";
    memoryEnabled.checked = profile?.memory_enabled !== false;
    memorySummary.textContent = !memoryEnabled.checked
      ? "跨对话记忆已关闭。新对话不会读取自动画像。"
      : profile?.memory_summary || "完成几轮学习后，这里会形成可解释的自动画像。";
    memoryMeta.textContent = profile?.memory_updated_at
      ? `最近整理：${new Date(profile.memory_updated_at).toLocaleString("zh-CN")}`
      : "只记录场景、语言和错误类型，不保存原始问题文本。";
    memoryRefresh.disabled = !memoryEnabled.checked;
    memoryClear.disabled = !profile?.memory_summary;
    sidebarName.textContent = profile?.nickname || "学习画像";
  }

  async function loadProfile() {
    const profile = await API.getProfile();
    applyProfile(profile);
    return profile;
  }

  async function open() {
    UI.openSheet(panel);
    try {
      await loadProfile();
      nickname.focus();
    } catch (error) {
      UI.toast(error.message || "无法加载学习画像", "error");
    }
  }

  async function save(event) {
    event.preventDefault();
    const submit = document.getElementById("profile-save");
    submit.disabled = true;
    try {
      const profile = await API.updateProfile({
        nickname: nickname.value.trim(),
        skill_level: level.value,
        preferred_languages: languages.value.trim(),
        learning_goal: goal.value.trim(),
        feedback_style: feedbackStyle.value,
        memory_enabled: memoryEnabled.checked,
      });
      applyProfile(profile);
      UI.closeSheets();
      UI.toast("学习画像已保存");
    } catch (error) {
      UI.toast(error.message || "画像保存失败", "error");
    } finally {
      submit.disabled = false;
    }
  }

  async function refreshMemory() {
    memoryRefresh.disabled = true;
    try {
      const profile = await API.refreshProfileMemory();
      applyProfile(profile);
      UI.toast("跨对话画像已重新整理");
    } catch (error) {
      UI.toast(error.message || "自动画像整理失败", "error");
    } finally {
      memoryRefresh.disabled = !memoryEnabled.checked;
    }
  }

  async function clearMemory() {
    const confirmed = await UI.confirm(
      "清除自动记忆？",
      "系统会忘记此前从学习记录中整理出的场景、语言和错误偏好；手动填写的昵称与学习目标会保留。",
    );
    if (!confirmed) return;
    memoryClear.disabled = true;
    try {
      const profile = await API.clearProfileMemory();
      applyProfile(profile);
      UI.toast("自动记忆已清除");
    } catch (error) {
      UI.toast(error.message || "自动记忆清除失败", "error");
    }
  }

  document.getElementById("btn-profile").addEventListener("click", open);
  document.getElementById("btn-profile-rail").addEventListener("click", open);
  document.getElementById("btn-close-profile").addEventListener("click", () => window.UI?.closeSheets());
  document.getElementById("profile-cancel").addEventListener("click", () => window.UI?.closeSheets());
  memoryEnabled.addEventListener("change", () => {
    memoryRefresh.disabled = !memoryEnabled.checked;
    if (!memoryEnabled.checked) {
      memorySummary.textContent = "保存后将关闭跨对话记忆。";
    } else if (State.profile?.memory_summary) {
      memorySummary.textContent = State.profile.memory_summary;
    }
  });
  memoryRefresh.addEventListener("click", refreshMemory);
  memoryClear.addEventListener("click", clearMemory);
  form.addEventListener("submit", save);

  window.Profile = { open, loadProfile, applyProfile };
})();
