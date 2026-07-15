class APIRequestError extends Error {
  constructor(message, code = "REQUEST_FAILED", status = 0) {
    super(message);
    this.name = "APIRequestError";
    this.code = code;
    this.status = status;
  }
}

const API = {
  base: "/api/v1",
  timeoutMs: 55000,

  async _fetch(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    const method = (options.method || "GET").toUpperCase();
    if (options.body) headers["Content-Type"] = "application/json";
    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
      if (csrfToken) headers["X-CSRFToken"] = csrfToken;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
        credentials: "same-origin",
      });

      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : null;

      if (!response.ok || payload?.error) {
        throw new APIRequestError(
          payload?.error?.message || `请求失败 (${response.status})`,
          payload?.error?.code || "HTTP_ERROR",
          response.status,
        );
      }

      return payload?.data ?? null;
    } catch (error) {
      if (error.name === "AbortError") {
        throw new APIRequestError("响应时间过长，请稍后重试", "TIMEOUT", 408);
      }
      if (error instanceof APIRequestError) throw error;
      throw new APIRequestError("无法连接到服务，请检查应用是否正在运行", "NETWORK_ERROR", 0);
    } finally {
      clearTimeout(timeout);
    }
  },

  bootstrap() { return this._fetch(`${this.base}/bootstrap`); },
  getAccount() { return this._fetch(`${this.base}/auth/me`); },
  register(data) { return this._fetch(`${this.base}/auth/register`, { method: "POST", body: JSON.stringify(data) }); },
  login(data) { return this._fetch(`${this.base}/auth/login`, { method: "POST", body: JSON.stringify(data) }); },
  logout() { return this._fetch(`${this.base}/auth/logout`, { method: "POST" }); },
  getProfile() { return this._fetch(`${this.base}/profile`); },
  updateProfile(data) { return this._fetch(`${this.base}/profile`, { method: "PATCH", body: JSON.stringify(data) }); },
  clearProfileMemory() { return this._fetch(`${this.base}/profile/memory`, { method: "DELETE" }); },
  refreshProfileMemory() { return this._fetch(`${this.base}/profile/memory/refresh`, { method: "POST" }); },

  createConversation(title = null) { return this._fetch(`${this.base}/conversations`, { method: "POST", body: JSON.stringify({ title }) }); },
  listConversations() { return this._fetch(`${this.base}/conversations`); },
  getConversation(id) { return this._fetch(`${this.base}/conversations/${encodeURIComponent(id)}`); },
  updateConversation(id, data) { return this._fetch(`${this.base}/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(data) }); },
  deleteConversation(id) { return this._fetch(`${this.base}/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }); },

  getMessages(conversationId) { return this._fetch(`${this.base}/conversations/${encodeURIComponent(conversationId)}/messages`); },
  sendMessage(conversationId, data) { return this._fetch(`${this.base}/conversations/${encodeURIComponent(conversationId)}/messages`, { method: "POST", body: JSON.stringify(data) }); },

  getLearningOverview() { return this._fetch(`${this.base}/learning/overview`); },
  getLearningEvents(limit = 20) { return this._fetch(`${this.base}/learning/events?limit=${limit}`); },
  getReminders() { return this._fetch(`${this.base}/reminders`); },
  markReminderRead(id) { return this._fetch(`${this.base}/reminders/${id}/read`, { method: "POST" }); },
  dismissReminder(id) { return this._fetch(`${this.base}/reminders/${id}/dismiss`, { method: "POST" }); },
  getReviewPlans() { return this._fetch(`${this.base}/review-plans`); },
  completeReviewPlan(id) { return this._fetch(`${this.base}/review-plans/${id}/complete`, { method: "POST" }); },
};
