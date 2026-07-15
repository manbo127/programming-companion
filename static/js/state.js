const State = {
  currentConversationId: null,
  currentConversationTitle: "新的对话",
  conversations: [],
  profile: null,
  sceneHint: "",
  languageHint: "",
  isLoading: false,

  setCurrentConversation(conversation) {
    this.currentConversationId = conversation?.id || null;
    this.currentConversationTitle = conversation?.title || "新的对话";
  },

  currentConversation() {
    return this.conversations.find(item => item.id === this.currentConversationId) || null;
  },
};
