"""
情绪检测与激励话术模块
感知用户学习状态，给予自然而真诚的情感化反馈
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmotionState:
    """情绪状态"""
    is_frustrated: bool = False
    is_positive: bool = False
    is_confused: bool = False
    consecutive_errors: int = 0
    consecutive_success: int = 0
    frustrated_keywords: list[str] = None
    positive_keywords: list[str] = None
    label: str = "neutral"
    score: float = 0.0
    intensity: str = "low"

    def __post_init__(self):
        if self.frustrated_keywords is None:
            self.frustrated_keywords = []
        if self.positive_keywords is None:
            self.positive_keywords = []


# ═══════════════════════════════════════════════════════════
# 关键词检测库
# ═══════════════════════════════════════════════════════════

FRUSTRATION_KEYWORDS = [
    "好难", "太难了", "好复杂", "看不懂", "不明白",
    "又错了", "还是错", "又报错", "还是报错", "又是这个",
    "不懂", "不会", "不理解", "搞不懂", "想不通",
    "放弃了", "不想做了", "不想学了", "学不会", "我太笨了",
    "崩溃", "好烦", "头疼", "痛苦", "绝望", "心态炸了",
    "救救我", "救命", "怎么办", "没救了",
    "too hard", "confused", "don't understand",
    "stuck", "frustrated", "giving up", "help me",
]

POSITIVE_KEYWORDS = [
    "明白了", "原来如此", "懂了", "理解了", "知道了", "哦！",
    "成功了", "通过了", "跑起来了", "可以了", "做到了",
    "谢谢", "感谢", "太棒了", "终于", "哈哈",
    "原来是这样", "这么简单", "我懂了！",
    "i see", "got it", "understand", "thanks",
    "works now", "finally", "awesome",
]

CONFUSION_KEYWORDS = [
    "?", "？", "什么意思", "没听懂", "再说一遍",
    "能再讲一遍吗", "还是不太懂", "能换个方式讲吗",
    "能举个例子吗", "我还是不会",
]


# ═══════════════════════════════════════════════════════════
# 话术库（随机轮换避免重复）
# ═══════════════════════════════════════════════════════════

PRAISE_TEMPLATES = [
    "你已经慢慢找到感觉了，继续保持！💪",
    "看，你在一点点进步！这次的思路比之前清晰多了。",
    "真不错！你能自己想通这一点，说明理解得很透彻。",
    "为你感到高兴！这种自己想出来的感觉是不是很棒？",
    "厉害！看得出来你有在认真思考，这个进步很明显。",
    "就是这样！编程就是要这样一步步琢磨出来的。",
]

ENCOURAGE_TEMPLATES = [
    "别着急，编程本来就是反复试错的过程，每个人都是这样走过来的。",
    "这个错误确实挺让人头疼的，但遇到它就说明你快搞懂了。",
    "慢慢来，不急。我当初学的时候被这个坑了好多次呢。",
    "没关系，出错其实是学习最快的方式。咱们一起看看问题出在哪里。",
    "卡住是很正常的事，休息一下再回来可能会有新的思路。",
    "你已经很努力了！这个问题确实不好理解，咱们换个角度试试。",
]

COMFORT_TEMPLATES = [
    "这个错误很常见的，不用担心。",
    "刚开始学都会遇到这个问题，没什么大不了的。",
    "出错不可怕，可怕的是不敢再试。你已经很勇敢了。",
]

CONCISE_TEMPLATES = {
    "praise": ["这一步判断正确，继续验证下一个边界。", "思路已经跑通，可以继续提高难度。"],
    "encourage": ["先缩小问题范围，我们一次只验证一个条件。", "先停一下，从第一条错误开始定位。"],
    "comfort": ["这是可定位的问题，先看第一处有效报错。", "不用重写全部代码，先验证一个变量。"],
}

WARM_TEMPLATES = {
    "praise": PRAISE_TEMPLATES,
    "encourage": ENCOURAGE_TEMPLATES,
    "comfort": COMFORT_TEMPLATES,
}

CONFUSION_RESPONSES = [
    "我换个方式再讲一遍～",
    "让我用更简单的说法再解释一下。",
    "好，我们用生活中的例子来理解一下。",
]


class MotivationEngine:
    """情绪检测与激励引擎 — 每个会话独立实例，防止多会话计数污染。"""

    _instances: dict[str, "MotivationEngine"] = {}

    def __init__(self):
        self.consecutive_errors = 0
        self.consecutive_success = 0
        self._used_praise: list[str] = []
        self._used_encourage: list[str] = []

    @classmethod
    def for_conversation(
        cls,
        conversation_id: str,
        consecutive_errors: int | None = None,
        consecutive_success: int | None = None,
    ) -> "MotivationEngine":
        """获取指定会话的独立实例，并与持久化状态同步。"""
        if conversation_id not in cls._instances:
            cls._instances[conversation_id] = cls()
        instance = cls._instances[conversation_id]
        if consecutive_errors is not None:
            instance.consecutive_errors = consecutive_errors
        if consecutive_success is not None:
            instance.consecutive_success = consecutive_success
        return instance

    @classmethod
    def reset_conversation(cls, conversation_id: str):
        """重置指定会话的计数器。"""
        cls._instances.pop(conversation_id, None)

    def analyze(self, text: str) -> EmotionState:
        """
        分析用户消息中的情绪信号。
        更新连续计数器并返回情绪状态。
        """
        text_lower = text.lower() if text else ""
        state = EmotionState()

        # 检测挫败信号
        frustrated = [kw for kw in FRUSTRATION_KEYWORDS if kw in text_lower]
        if frustrated:
            state.is_frustrated = True
            state.frustrated_keywords = frustrated

        # 检测积极信号
        positive = [kw for kw in POSITIVE_KEYWORDS if kw in text_lower]
        if positive:
            state.is_positive = True
            state.positive_keywords = positive

        # 检测困惑信号
        # 普通问句中的问号不是困惑证据，避免把所有技术提问都标成负面情绪。
        confused = [kw for kw in CONFUSION_KEYWORDS if kw not in {"?", "？"} and kw in text]
        if confused:
            state.is_confused = True

        positive_score = min(len(positive), 3)
        negative_score = min(len(frustrated), 3) + min(len(confused), 2) * 0.5
        raw_score = positive_score - negative_score
        state.score = round(max(-1.0, min(1.0, raw_score / 3)), 2)
        if raw_score > 0:
            state.label = "positive"
            state.is_positive = True
            state.is_frustrated = False
        elif raw_score < 0:
            state.label = "frustrated" if frustrated else "confused"
            state.is_positive = False
        elif state.is_confused:
            state.label = "confused"
        state.intensity = "high" if abs(state.score) >= 0.67 else "medium" if abs(state.score) >= 0.34 else "low"

        # 更新连续计数器
        if state.is_positive:
            self.consecutive_success += 1
            self.consecutive_errors = 0
        elif state.is_frustrated:
            self.consecutive_errors += 1
            self.consecutive_success = 0
        else:
            # 中性消息不重置计数器，但也不递增
            pass

        state.consecutive_errors = self.consecutive_errors
        state.consecutive_success = self.consecutive_success
        return state

    def _choose(self, category: str, style: str) -> str:
        if style == "concise":
            choices = CONCISE_TEMPLATES[category]
        else:
            choices = WARM_TEMPLATES[category]
        offset = self.consecutive_success if category == "praise" else self.consecutive_errors
        return choices[max(offset - 1, 0) % len(choices)]

    def get_praise(self, style: str = "balanced") -> Optional[str]:
        """获取表扬话术（连续成功 ≥ 3 时触发）"""
        if self.consecutive_success < 3:
            return None

        return self._choose("praise", style)

    def get_encouragement(self, style: str = "balanced") -> Optional[str]:
        """获取鼓励话术（连续错误 ≥ 2 时触发）"""
        if self.consecutive_errors < 2:
            return None

        return self._choose("encourage", style)

    def get_comfort(self, style: str = "balanced") -> str:
        """获取安慰话术（单次挫败）"""
        return self._choose("comfort", style)

    def build_emotion_hint(self, state: EmotionState) -> Optional[str]:
        """
        根据情绪状态生成送给 system prompt 的提示文字。
        返回 None 表示无需特别处理。
        """
        # 严重挫败：连续 ≥ 3 次
        if state.consecutive_errors >= 3:
            return (
                f"用户已经连续 {state.consecutive_errors} 次遇到困难，"
                "表现出明显的挫败感。请在回复开头先给予温暖真诚的鼓励，"
                "然后主动提议帮他系统梳理一下相关的基础概念，"
                "而不是继续推进当前的题目或错误。语气要像一个真正关心他的朋友。"
            )

        # 连续出错：2 次
        if state.consecutive_errors >= 2:
            return (
                "用户连续出错，需要鼓励。请在回复中自然地融入一句鼓励的话，"
                "然后考虑换个角度解释问题，或者放慢节奏。"
            )

        # 单次挫败
        if state.is_frustrated:
            return "用户有些挫败，先用一句话共情，再开始正式回复。"

        # 连续成功
        if state.consecutive_success >= 3:
            return (
                "用户连续表现很好！请给予具体真诚的表扬，"
                "然后可以适当提高一点难度或深入讲解。"
            )

        # 困惑
        if state.is_confused:
            return "用户没有完全理解，请换一种方式重新解释，最好用生活化的比喻。"

        return None

    def reset(self):
        """重置计数器（新会话时调用）"""
        self.consecutive_errors = 0
        self.consecutive_success = 0
        self._used_praise.clear()
        self._used_encourage.clear()
