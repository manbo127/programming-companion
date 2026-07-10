(function () {
  const panel = document.getElementById("learning-panel");
  const content = document.getElementById("learning-content");
  const badge = document.getElementById("reminders-badge");
  const languageNames = { python: "Python", java: "Java", c: "C", cpp: "C++" };

  function metric(label, value, detail) {
    const block = document.createElement("div");
    block.className = "metric-block";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.textContent = value;
    const detailEl = document.createElement("small");
    detailEl.textContent = detail || "暂无记录";
    block.append(labelEl, valueEl, detailEl);
    return block;
  }

  function render(overview, reminders) {
    content.replaceChildren();

    const metrics = document.createElement("section");
    metrics.className = "learning-metrics";
    const topError = overview.top_error_types?.[0];
    metrics.append(
      metric("学习事件", String(overview.total_events || 0), "系统记录的近期学习信号"),
      metric(
        "使用语言",
        String(overview.languages_used?.length || 0),
        overview.languages_used?.map(language => languageNames[language] || language).join("、") || "等待第一次代码分析",
      ),
      metric("高频错误", topError ? String(topError[1]) : "0", topError ? topError[0] : "尚未发现重复错误"),
      metric("待处理提醒", String(reminders.length), reminders.length ? "可以逐条查看并处理" : "当前没有新提醒"),
    );
    content.appendChild(metrics);

    const reminderSection = document.createElement("section");
    reminderSection.className = "learning-section";
    const heading = document.createElement("h3");
    heading.textContent = "学习提醒";
    reminderSection.appendChild(heading);

    if (!reminders.length) {
      const empty = document.createElement("p");
      empty.className = "learning-empty";
      empty.textContent = "继续进行几轮学习后，这里会出现针对性的复习建议。";
      reminderSection.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "reminder-list";
      reminders.forEach(reminder => {
        const item = document.createElement("article");
        item.className = "reminder-item";
        const text = document.createElement("p");
        text.textContent = reminder.content;
        const actions = document.createElement("div");
        actions.className = "reminder-actions";
        const read = document.createElement("button");
        read.type = "button";
        read.textContent = "标记已读";
        read.addEventListener("click", async () => {
          await API.markReminderRead(reminder.id);
          await loadOverview();
        });
        const dismiss = document.createElement("button");
        dismiss.type = "button";
        dismiss.textContent = "忽略";
        dismiss.addEventListener("click", async () => {
          await API.dismissReminder(reminder.id);
          await loadOverview();
        });
        actions.append(read, dismiss);
        item.append(text, actions);
        list.appendChild(item);
      });
      reminderSection.appendChild(list);
    }
    content.appendChild(reminderSection);
  }

  async function loadOverview() {
    const [overview, reminders] = await Promise.all([API.getLearningOverview(), API.getReminders()]);
    render(overview || {}, reminders || []);
    updateBadge(reminders || []);
  }

  function updateBadge(reminders) {
    const count = reminders.length;
    badge.hidden = count === 0;
    badge.textContent = String(count);
  }

  async function refreshBadge() {
    try {
      updateBadge(await API.getReminders() || []);
    } catch (_) {
      updateBadge([]);
    }
  }

  async function open() {
    UI.openSheet(panel);
    content.innerHTML = '<div class="learning-empty">正在整理近期学习记录...</div>';
    try {
      await loadOverview();
    } catch (error) {
      content.innerHTML = '<div class="learning-empty">暂时无法加载学习概览。</div>';
      UI.toast(error.message || "学习概览加载失败", "error");
    }
  }

  document.getElementById("btn-learning").addEventListener("click", open);
  document.getElementById("btn-close-learning").addEventListener("click", () => window.UI?.closeSheets());

  window.Learning = { open, loadOverview, refreshBadge };
})();
