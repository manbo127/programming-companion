(function () {
  const status = document.getElementById("account-status");
  const description = document.getElementById("account-description");
  const credentials = document.getElementById("account-credentials");
  const email = document.getElementById("account-email");
  const password = document.getElementById("account-password");
  const login = document.getElementById("account-login");
  const register = document.getElementById("account-register");
  const logout = document.getElementById("account-logout");

  function apply(account = {}) {
    const authenticated = Boolean(account.authenticated);
    status.textContent = authenticated ? "已登录" : "匿名模式";
    description.textContent = authenticated
      ? `当前账号：${account.email}`
      : "注册后会保留当前历史，并可在其他设备登录。匿名使用不受影响。";
    credentials.hidden = authenticated;
    logout.hidden = !authenticated;
  }

  function setBusy(busy) {
    login.disabled = busy;
    register.disabled = busy;
    logout.disabled = busy;
  }

  function values() {
    return { email: email.value.trim(), password: password.value };
  }

  async function submit(action) {
    setBusy(true);
    try {
      if (!email.value.trim() || password.value.length < 8) {
        UI.toast("请输入有效邮箱和至少 8 位密码", "error");
        return;
      }
      await API[action](values());
      window.location.reload();
    } catch (error) {
      UI.toast(error.message || "账号操作失败", "error");
    } finally {
      setBusy(false);
    }
  }

  login.addEventListener("click", () => submit("login"));
  register.addEventListener("click", () => submit("register"));
  logout.addEventListener("click", async () => {
    setBusy(true);
    try {
      await API.logout();
      window.location.reload();
    } catch (error) {
      UI.toast(error.message || "退出失败", "error");
      setBusy(false);
    }
  });

  window.Account = { apply };
})();
