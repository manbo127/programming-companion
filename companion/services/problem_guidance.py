"""结构化报错诊断和渐进式解题引导。"""
from dataclasses import asdict, dataclass


ERROR_CATEGORIES = {
    "SyntaxError": ("语法错误", "代码结构不符合语言语法", "先看报错位置前一行的括号、冒号和分隔符"),
    "CompileError": ("编译错误", "代码未通过编译器检查", "从第一条编译错误开始处理，后续错误可能是连锁反应"),
    "IndexError": ("边界错误", "访问的索引超出了容器有效范围", "打印容器长度和本次索引，检查边界条件"),
    "java.lang.ArrayIndexOutOfBoundsException": ("边界错误", "数组下标不在 0 到 length-1 范围内", "检查循环终止条件和数组长度"),
    "KeyError": ("键访问错误", "字典中不存在当前键", "先确认键是否存在，以及键的类型是否一致"),
    "TypeError": ("类型错误", "当前操作收到不兼容的值或参数", "分别查看参与运算的值及其实际类型"),
    "NameError": ("名称错误", "名称在当前位置尚未定义或不可见", "检查拼写、定义顺序和作用域"),
    "AttributeError": ("属性错误", "对象没有被访问的属性或方法", "确认对象实际类型和属性名称"),
    "ZeroDivisionError": ("算术错误", "除数在运行时变成了零", "追踪除数来源并处理零值边界"),
    "FileNotFoundError": ("文件路径错误", "程序找不到目标文件", "打印绝对路径并确认运行目录和文件名"),
    "Panic": ("运行时崩溃", "Go 运行时检测到无法继续的状态", "从 panic 后第一段调用栈定位最接近业务代码的位置"),
    "RustCompileError": ("编译期约束错误", "Rust 编译器检测到类型、所有权或借用规则冲突", "先阅读错误编号说明，再检查值的移动与借用位置"),
    "SQLError": ("SQL 语句错误", "SQL 语法、字段或表结构与当前数据库不匹配", "先单独执行最小查询并核对字段、表名和方言"),
}


@dataclass(frozen=True)
class ErrorDiagnosis:
    error_type: str
    category: str
    location: str
    explanation: str
    first_check: str
    confidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GuidancePlan:
    stage: int
    stage_name: str
    instruction: str

    def prompt_context(self) -> str:
        return (
            f"当前引导阶段：第 {self.stage} 阶段（{self.stage_name}）。\n"
            f"本轮教学动作：{self.instruction}\n"
            "一次只推进一个认知步骤，以一个可回答的小问题收尾；除非用户明确要求核对自己的完整答案，否则不要直接交付完整解法。"
        )


class ProblemGuidanceService:
    STAGES = (
        (1, "理解题意", "确认输入、输出、约束和一个具体样例，不急着讨论代码。"),
        (2, "拆分问题", "把任务拆成小步骤，只提示眼下第一步需要得到什么中间结果。"),
        (3, "形成算法", "用伪代码、状态变化或边界样例帮助用户自己补全关键逻辑。"),
        (4, "验证与反思", "让用户用正常、边界和异常样例验证现有思路，并总结复杂度或可改进点。"),
    )

    @classmethod
    def diagnose(cls, error_info: dict, language: str) -> ErrorDiagnosis | None:
        error_type = str(error_info.get("error_type") or "").strip()
        if not error_type:
            return None
        category, explanation, first_check = ERROR_CATEGORIES.get(
            error_type,
            ("程序错误", "当前错误需要结合报错信息和触发输入进一步定位", "先找到调用栈中第一处属于自己代码的位置"),
        )
        line = error_info.get("line")
        column = error_info.get("column")
        location = f"第 {line} 行" if line else "报错位置未明确"
        if line and column:
            location += f"，第 {column} 列"
        return ErrorDiagnosis(
            error_type=error_type,
            category=category,
            location=location,
            explanation=explanation,
            first_check=first_check,
            confidence="high" if error_type in ERROR_CATEGORIES else "medium",
        )

    @classmethod
    def plan(cls, scene: str, prior_turns: int, skill_level: str = "beginner") -> GuidancePlan | None:
        if scene not in {"guidance", "error"}:
            return None
        if scene == "error":
            instruction = (
                "按“错误含义 → 证据位置 → 最可能原因 → 一项检查动作 → 一个验证问题”组织回答。"
                "引用用户代码片段可以，但不要重写完整程序。"
            )
            return GuidancePlan(1, "诊断与验证", instruction)
        stage_index = min(max(prior_turns, 0), len(cls.STAGES) - 1)
        stage, name, instruction = cls.STAGES[stage_index]
        if skill_level in {"intermediate", "advanced"}:
            instruction += " 语言保持简洁，可补充时间或空间复杂度判断。"
        return GuidancePlan(stage, name, instruction)

    @staticmethod
    def prompt_context(plan: GuidancePlan | None, diagnosis: ErrorDiagnosis | None) -> str:
        sections = []
        if diagnosis:
            sections.append(
                "结构化诊断（系统根据报错文本提取，若与代码证据冲突，以代码证据为准）：\n"
                f"- 类型：{diagnosis.error_type}\n"
                f"- 分类：{diagnosis.category}\n"
                f"- 位置：{diagnosis.location}\n"
                f"- 含义：{diagnosis.explanation}\n"
                f"- 首项检查：{diagnosis.first_check}"
            )
        if plan:
            sections.append(plan.prompt_context())
        return "\n\n".join(sections)
