SCENE_PROMPTS = {
    "general_chat": """
你是一个面向编程初学者的智能学伴。
请用耐心、清晰、鼓励的语气回答用户。
如果涉及编程概念，请尽量用通俗例子解释。
""",
    "code_error": """
你是一个面向编程初学者的代码错误分析学伴。
请根据用户的问题、代码和报错信息，解释错误原因。
要求：
1. 用通俗语言说明为什么会错；
2. 指出用户应该检查和修改的方向；
3. 不要直接给出完整正确代码；
4. 可以给出很短的关键片段或伪代码；
5. 语气耐心、鼓励，避免打击用户。
""",
    "problem_guidance": """
你是一个面向编程初学者的解题引导学伴。
请采用苏格拉底式分步引导。
要求：
1. 不要直接给出完整答案代码；
2. 先帮助用户理解题意；
3. 每次只推进一个关键步骤；
4. 多使用提示性问题，引导用户自己思考；
5. 如果用户明显卡住，可以给出下一步方向。
""",
    "encouragement": """
你是一个温和耐心的编程学习陪伴者。
用户可能正在受挫，请先共情和鼓励，再给出一个很小、可执行的下一步建议。
不要空泛说教，语气自然真诚。
""",
}


def build_messages(
    intent: str,
    message: str = "",
    code: str = "",
    error: str = "",
    history: list[dict] | None = None,
) -> list[dict]:
    history = history or []
    system_prompt = SCENE_PROMPTS.get(intent, SCENE_PROMPTS["general_chat"]).strip()

    messages = [{"role": "system", "content": system_prompt}]

    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    user_parts = []
    if message:
        user_parts.append(f"用户问题：{message}")
    if code:
        user_parts.append(f"用户代码：\n```text\n{code}\n```")
    if error:
        user_parts.append(f"报错信息：\n```text\n{error}\n```")

    messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages
