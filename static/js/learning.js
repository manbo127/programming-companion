(function () {
  const panel = document.getElementById("learning-panel");
  const content = document.getElementById("learning-content");
  const badge = document.getElementById("reminders-badge");
  const railBadge = document.getElementById("reminders-badge-rail");
  const languageNames = {
    python: "Python", java: "Java", c: "C", cpp: "C++",
    javascript: "JavaScript", typescript: "TypeScript", go: "Go", rust: "Rust", sql: "SQL",
  };

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

  function render(overview, reminders, reviewPlans) {
    content.replaceChildren();

    const metrics = document.createElement("section");
    metrics.className = "learning-metrics";
    const topError = overview.top_error_types?.[0];
    const trendLabels = {
      improving: "近 7 天错误量下降",
      needs_attention: "近 7 天错误量上升",
      stable: "近两周表现相对稳定",
    };
    metrics.append(
      metric("学习事件", String(overview.total_events || 0), `${overview.window_days || 30} 天窗口`),
      metric(
        "使用语言",
        String(overview.languages_used?.length || 0),
        overview.languages_used?.map(language => languageNames[language] || language).join("、") || "等待第一次代码分析",
      ),
      metric("高频错误", topError ? String(topError[1]) : "0", topError ? topError[0] : "尚未发现重复错误"),
      metric("活跃天数", String(overview.active_days || 0), trendLabels[overview.trend?.direction] || "等待更多学习记录"),
    );
    content.appendChild(metrics);

    const progressSection = document.createElement("section");
    progressSection.className = "learning-section";
    const progressHeading = document.createElement("h3");
    progressHeading.textContent = "知识点掌握趋势";
    progressSection.appendChild(progressHeading);
    const topicProgress = overview.topic_progress || [];
    if (!topicProgress.length) {
      const empty = document.createElement("p");
      empty.className = "learning-empty";
      empty.textContent = "提交包含知识点的问题或代码后，这里会形成学习趋势。";
      progressSection.appendChild(empty);
    } else {
      const progressList = document.createElement("div");
      progressList.className = "topic-progress-list";
      topicProgress.forEach(item => {
        const row = document.createElement("article");
        row.className = "topic-progress-item";
        const heading = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = item.topic;
        const score = document.createElement("span");
        score.textContent = `${item.mastery_score} / 100`;
        heading.append(name, score);
        const track = document.createElement("div");
        track.className = "topic-progress-track";
        const fill = document.createElement("span");
        fill.style.width = `${Math.max(0, Math.min(item.mastery_score, 100))}%`;
        track.appendChild(fill);
        const detail = document.createElement("small");
        detail.textContent = `${item.attempts} 次互动 · ${item.errors} 次错误 · ${item.positive} 次积极反馈`;
        row.append(heading, track, detail);
        progressList.appendChild(row);
      });
      progressSection.appendChild(progressList);
    }
    content.appendChild(progressSection);

    const planSection = document.createElement("section");
    planSection.className = "learning-section";
    const planHeading = document.createElement("h3");
    planHeading.textContent = "间隔复习计划";
    planSection.appendChild(planHeading);
    if (!reviewPlans.length) {
      const empty = document.createElement("p");
      empty.className = "learning-empty";
      empty.textContent = "系统会根据错误和练习主题自动安排 1、3、7、14、30 天复习。";
      planSection.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "review-plan-list";
      reviewPlans.forEach(plan => {
        const item = document.createElement("article");
        item.className = "review-plan-item";
        const copy = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = plan.topic;
        const due = document.createElement("small");
        due.textContent = `下次复习：${new Date(plan.next_review_at).toLocaleString("zh-CN")}`;
        copy.append(title, due);
        const complete = document.createElement("button");
        complete.type = "button";
        complete.textContent = "完成一次";
        complete.addEventListener("click", async () => {
          complete.disabled = true;
          try {
            await API.completeReviewPlan(plan.id);
            await loadOverview();
            UI.toast("已安排下一次复习");
          } catch (error) {
            UI.toast(error.message || "复习计划更新失败", "error");
            complete.disabled = false;
          }
        });
        item.append(copy, complete);
        list.appendChild(item);
      });
      planSection.appendChild(list);
    }
    content.appendChild(planSection);

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
        const start = document.createElement("button");
        start.type = "button";
        start.textContent = reminder.type === "positive_streak" ? "开始挑战" : "现在复习";
        start.addEventListener("click", async () => {
          await API.markReminderRead(reminder.id);
          UI.closeSheets();
          Conversations.newSession();
          const input = document.getElementById("message-input");
          input.value = reminder.type === "positive_streak"
            ? "请根据我最近的学习情况，给我一个稍有挑战但不要直接给答案的编程练习。"
            : `${reminder.content}\n请从基础概念开始带我复习。`;
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.focus();
          await refreshBadge();
        });
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
        actions.append(start, read, dismiss);
        item.append(text, actions);
        list.appendChild(item);
      });
      reminderSection.appendChild(list);
    }
    content.appendChild(reminderSection);
  }

  async function loadOverview() {
    const [overview, reminders, reviewPlans] = await Promise.all([
      API.getLearningOverview(),
      API.getReminders(),
      API.getReviewPlans(),
    ]);
    render(overview || {}, reminders || [], reviewPlans || []);
    updateBadge(reminders || []);
  }

  function updateBadge(reminders) {
    const count = reminders.length;
    [badge, railBadge].forEach(item => {
      item.hidden = count === 0;
      item.textContent = String(count);
    });
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
  document.getElementById("btn-learning-rail").addEventListener("click", open);
  document.getElementById("btn-close-learning").addEventListener("click", () => window.UI?.closeSheets());

  window.Learning = { open, loadOverview, refreshBadge };
})();
