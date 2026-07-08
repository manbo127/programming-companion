"""
消息分类器 — 基于规则的关键词匹配
零延迟、零成本、过程可解释、规则可调试
"""
from dataclasses import dataclass, field
from typing import Optional
from utils.code_utils import has_code, has_error


@dataclass
class ClassificationResult:
    """分类结果"""
    scene: str                    # "error" | "guidance" | "knowledge" | "general"
    has_code: bool = False
    has_error: bool = False
    language: str = "unknown"
    confidence: float = 1.0       # 置信度 (规则匹配 = 1.0)
    matched_keywords: list[str] = field(default_factory=list)


# ── 关键词库（中英文双语覆盖）──────────────────────────────

# 错误相关关键词（优先级最高）
ERROR_KEYWORDS = [
    # 中文
    "报错", "出错", "错误", "异常", "崩溃", "不运行", "运行不了",
    "没反应", "闪退", "bug", "Bug", "BUG",
    "怎么改", "帮我改", "改一下", "修一下", "修复",
    "哪里有问题", "哪里错了", "什么原因", "怎么回事",
    "跑不起来", "编译不通过", "编译失败", "编译错误",
    "这段代码有问题", "代码报错", "程序报错",
    "一直报", "老是报", "又报",
    # 英文
    "error", "Error", "ERROR",
    "exception", "Exception",
    "traceback", "Traceback",
    "failed", "failure",
    "not working", "doesn't work", "does not work",
    "what's wrong", "what is wrong",
    "help me fix", "how to fix",
]

# 解题求助关键词
GUIDANCE_KEYWORDS = [
    # 中文 — 完整答案请求
    "怎么做", "怎么写", "如何实现", "怎么实现", "怎样实现",
    "帮我写", "帮我做", "写一个", "做一个", "编一个",
    "代码怎么写", "程序怎么写", "求代码", "求答案",
    # 中文 — 思路请求（更偏向引导）
    "思路", "解题", "解这道题", "这道题",
    "请教", "请问这道", "不会做", "做不出来",
    "怎么做这道", "这题怎么", "这个题",
    "有什么方法", "用什么方法", "算法",
    "步骤", "流程", "应该怎么",
    # 英文
    "how to write", "how to code", "how to implement",
    "how to solve", "how would you",
    "can you write", "can you code",
    "solve this", "solution",
    "what approach", "best way to",
    "help me understand", "explain the logic",
    "write a program", "write a function",
]

# 知识点问答关键词
KNOWLEDGE_KEYWORDS = [
    # 中文 — 概念解释
    "什么是", "是什么", "什么意思", "指的是什么",
    "怎么理解", "如何理解",
    "定义", "概念", "区别", "区别是", "有什么区别",
    "和.*有什么不同", "和.*对比", "和.*比较",
    # 中文 — 对比
    "哪个好", "优缺点", "适用场景", "什么时候用",
    # 中文 — 通用
    "解释", "讲一下", "说一下", "介绍一下",
    "能讲讲", "能说说", "能解释",
    # 英文
    "what is", "what are",
    "explain", "describe",
    "difference between", "vs", "versus",
    "when to use", "why use", "why do we",
    "how does", "how do",
    "meaning of", "definition",
]

# 激励相关关键词（不单独成场景，用于 emotion 模块辅助）
MOTIVATION_SIGNALS = {
    "positive": [
        "明白了", "原来如此", "懂了", "理解了", "知道了",
        "成功了", "通过了", "跑起来了", "可以了", "实现了",
        "谢谢", "感谢", "太棒了", "终于",
        "i see", "got it", "understand", "thanks", "works now",
    ],
    "negative": [
        "好难", "太难了", "好复杂", "看不懂", "不明白",
        "又错了", "还是错", "又报错", "还是报错",
        "不懂", "不会", "不理解", "搞不懂", "想不通",
        "放弃了", "不想做了", "学不会", "太笨了",
        "崩溃", "烦", "头疼", "痛苦", "绝望",
        "too hard", "confused", "don't understand", "stuck",
        "frustrated", "giving up", "can't do",
        "我", "我",  # 待过滤
    ],
}


class MessageClassifier:
    """基于规则的消息分类器"""

    def __init__(self):
        self.error_keywords = ERROR_KEYWORDS
        self.guidance_keywords = GUIDANCE_KEYWORDS
        self.knowledge_keywords = KNOWLEDGE_KEYWORDS

    def classify(
        self,
        text: str = "",
        code: str = "",
        error: str = "",
    ) -> ClassificationResult:
        """
        分类用户消息。

        优先级: error > guidance > knowledge > general
        """
        result = ClassificationResult(scene="general")
        text_lower = text.lower() if text else ""

        # ── 特征检测 ─────────────────────────────
        result.has_code = bool(code and code.strip()) or has_code(text)
        result.has_error = bool(error and error.strip()) or has_error(
            text + (error or "")
        )

        # ── 优先级 1: 错误解读 ────────────────────
        error_score = self._match_score(text_lower, self.error_keywords)

        # 高置信条件：代码+错误同时存在 或 多个错误关键词
        if result.has_code and result.has_error:
            result.scene = "error"
            result.confidence = 1.0
            result.matched_keywords = ["code+error combined"]
            return result

        if error_score >= 2:
            result.scene = "error"
            result.confidence = 0.95
            result.matched_keywords = self._matched_list(
                text_lower, self.error_keywords
            )
            return result

        # ── 优先级 2: 解题引导 ────────────────────
        guidance_score = self._match_score(text_lower, self.guidance_keywords)
        if guidance_score >= 2:
            result.scene = "guidance"
            result.confidence = 0.9
            result.matched_keywords = self._matched_list(
                text_lower, self.guidance_keywords
            )
            return result

        # 有代码但没有错误 → 可能是解题求助
        if result.has_code and not result.has_error:
            result.scene = "guidance"
            result.confidence = 0.7
            result.matched_keywords = ["code present, no error"]
            return result

        # ── 优先级 3: 知识点问答 ──────────────────
        knowledge_score = self._match_score(text_lower, self.knowledge_keywords)
        if knowledge_score >= 1:
            result.scene = "knowledge"
            result.confidence = 0.85
            result.matched_keywords = self._matched_list(
                text_lower, self.knowledge_keywords
            )
            return result

        # ── 优先级 4: 一般对话 ────────────────────
        result.scene = "general"
        result.confidence = 0.8
        return result

    def _match_score(self, text: str, keywords: list[str]) -> int:
        """计算关键词命中数"""
        import re
        score = 0
        for kw in keywords:
            try:
                if re.search(kw, text):
                    score += 1
            except re.error:
                if kw in text:
                    score += 1
        return score

    def _matched_list(self, text: str, keywords: list[str]) -> list[str]:
        """返回命中的关键词列表"""
        import re
        matched = []
        for kw in keywords:
            try:
                if re.search(kw, text):
                    matched.append(kw)
            except re.error:
                if kw in text:
                    matched.append(kw)
        return matched[:5]  # 最多返回 5 个
