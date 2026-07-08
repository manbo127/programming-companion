def classify_intent(message: str = "", code: str = "", error: str = "") -> str:
    """
    基于关键词的轻量意图识别。
    这样做响应快、成本低，也符合报告中“规则匹配”的设计约束。
    """
    text = f"{message}\n{code}\n{error}".lower()

    code_error_keywords = [
        "报错",
        "错误",
        "异常",
        "bug",
        "error",
        "exception",
        "traceback",
        "syntaxerror",
        "nameerror",
        "typeerror",
        "valueerror",
        "indexerror",
        "nullpointerexception",
    ]
    problem_guidance_keywords = [
        "怎么做",
        "怎么写",
        "思路",
        "算法",
        "题目",
        "不会",
        "解法",
        "提示",
        "步骤",
    ]
    encouragement_keywords = [
        "好难",
        "崩溃",
        "烦",
        "不想学",
        "放弃",
        "学不会",
        "太难了",
        "没信心",
    ]

    if any(keyword in text for keyword in encouragement_keywords):
        return "encouragement"
    if error or any(keyword in text for keyword in code_error_keywords):
        return "code_error"
    if any(keyword in text for keyword in problem_guidance_keywords):
        return "problem_guidance"
    return "general_chat"
