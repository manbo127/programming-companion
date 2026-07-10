(function () {
  const panel = document.getElementById("profile-panel");
  const form = document.getElementById("profile-form");
  const nickname = document.getElementById("profile-nickname");
  const level = document.getElementById("profile-level");
  const languages = document.getElementById("profile-langs");
  const goal = document.getElementById("profile-goal");
  const sidebarName = document.getElementById("sidebar-profile-name");

  function applyProfile(profile) {
    State.profile = profile || {};
    nickname.value = profile?.nickname || "";
    level.value = profile?.skill_level || "beginner";
    languages.value = profile?.preferred_languages || "";
    goal.value = profile?.learning_goal || "";
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

  document.getElementById("btn-profile").addEventListener("click", open);
  document.getElementById("btn-close-profile").addEventListener("click", () => window.UI?.closeSheets());
  document.getElementById("profile-cancel").addEventListener("click", () => window.UI?.closeSheets());
  form.addEventListener("submit", save);

  window.Profile = { open, loadProfile, applyProfile };
})();
