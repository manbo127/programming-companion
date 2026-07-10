"""
代码工具模块 — 语言检测、代码块提取、错误信息解析
不依赖任何第三方库，纯正则与字符串操作
"""
import re
from typing import Optional


# ── 编程语言关键词特征库 ──────────────────────────────────
LANGUAGE_FEATURES = {
    "python": {
        "keywords": [
            "def ", "import ", "print(", "class ", "if __name__",
            "elif ", "None", "True", "False", "self", "__init__",
            ":", "with ", "as ", "from ", "lambda", "yield", "raise",
        ],
        "extensions": [".py"],
        "comment": "#",
    },
    "java": {
        "keywords": [
            "public class", "public static void main", "System.out",
            "String[] args", "import java", "new ", "extends ",
            "implements ", "private ", "protected ", "@Override",
        ],
        "extensions": [".java"],
        "comment": "//",
    },
    "c": {
        "keywords": [
            "#include", "printf(", "scanf(", "malloc(", "free(",
            "int main(", "void main(", "->", "struct ", "typedef ",
        ],
        "extensions": [".c", ".h"],
        "comment": "//",
    },
    "cpp": {
        "keywords": [
            "#include <iostream>", "std::", "cout <<", "cin >>",
            "vector<", "template<", "namespace ", "new ", "delete ",
        ],
        "extensions": [".cpp", ".cc", ".cxx", ".hpp"],
        "comment": "//",
    },
}

# ── 中文编程语言关键词映射 ─────────────────────────────────
CN_LANGUAGE_HINTS = {
    "python": ["python", "py", "蟒蛇", "派森"],
    "java": ["java", "爪哇"],
    "c语言": ["c语言", "c ", "c/c++"],
    "c++": ["c++", "cpp", "c plus plus", "c加加"],
}


def detect_language(code: str, hint: str = "") -> str:
    """
    根据代码特征检测编程语言。
    返回语言名称字符串，如 "python"、"java"、"c"、"cpp"；无法判断时返回 "unknown"。
    """
    if not code or not code.strip():
        return "unknown"

    # 1. 中文提示词优先匹配
    if hint:
        hint_lower = hint.lower()
        for lang, patterns in CN_LANGUAGE_HINTS.items():
            if any(p in hint_lower for p in patterns):
                return lang

    # 2. 代码特征打分
    scores = {}
    code_normalized = code.strip()

    for lang, features in LANGUAGE_FEATURES.items():
        score = 0
        for kw in features["keywords"]:
            if kw in code_normalized:
                score += 1
        scores[lang] = score

    # 3. 取最高分
    if scores:
        best = max(scores, key=lambda k: scores[k])
        if scores[best] >= 2:
            return best

    # 4. 退化为 unknown
    return "unknown"


def extract_code_blocks(text: str) -> list[dict]:
    """
    从文本中提取 Markdown 风格代码块。
    返回 [{"language": "python", "code": "print('hello')"}, ...]
    """
    # 匹配 ```language\n code \n```
    pattern = r"```(\w*)\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    blocks = []
    for lang, code in matches:
        lang = lang.strip() if lang.strip() else detect_language(code)
        blocks.append({
            "language": lang,
            "code": code.strip(),
        })

    return blocks


def parse_error_info(error_text: str) -> dict:
    """
    解析报错信息，提取结构化字段。
    返回 {"error_type": "IndexError", "line": 3, "message": "..."}
    """
    result = {
        "error_type": "",
        "line": None,
        "message": error_text.strip(),
    }

    if not error_text or not error_text.strip():
        return result

    text = error_text.strip()

    # Python: File "xxx.py", line 3, in ...
    py_line = re.search(r'line\s+(\d+)', text)
    if py_line:
        result["line"] = int(py_line.group(1))

    # Python: IndexError: list index out of range
    # Java: Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException
    # C: error: expected ';' before '}'
    py_error = re.search(r'(\w+Error):\s*(.+)', text)
    java_error = re.search(r'(java\.\w+\.\w+Exception)', text)
    c_error = re.search(r'error:\s*(.+)', text)

    if py_error:
        result["error_type"] = py_error.group(1)
        result["message"] = py_error.group(2)
    elif java_error:
        result["error_type"] = java_error.group(1)
    elif c_error:
        result["error_type"] = "CompileError"
        result["message"] = c_error.group(1)
    else:
        # 尝试匹配常见错误关键词
        for err in ["IndexError", "TypeError", "ValueError", "KeyError",
                     "NameError", "SyntaxError", "AttributeError",
                     "ZeroDivisionError", "FileNotFoundError", "ImportError"]:
            if err.lower() in text.lower():
                result["error_type"] = err
                break

    return result


def has_code(text: str) -> bool:
    """判断文本中是否包含代码"""
    if not text:
        return False

    # Markdown 代码块
    if re.search(r"```[\s\S]*?```", text):
        return True

    # 代码特征行
    code_indicators = [
        r"^\s*(def |class |import |from |if __name__)",
        r"^\s*(public class|public static|System\.out)",
        r"^\s*#include\s*[<\"']",
        r"^\s*print\(",
        r"^\s*for\s+\w+\s+in\s+",
        r"^\s*while\s*\(.+\)",
        r"^\s*\{\s*$",
    ]
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for pattern in code_indicators:
            if re.search(pattern, line):
                return True

    return False


def has_error(text: str) -> bool:
    """判断文本中是否包含报错信息"""
    if not text:
        return False

    error_indicators = [
        r"(Error|Exception|Traceback)",
        r"line\s+\d+",
        r"(错误|报错|出错|异常|崩溃)",
        r"File\s+\"[^\"]+\",\s*line\s+\d+",
        r"^\s*at\s+\w+\.\w+\(.*\.java:\d+\)",
    ]
    return any(re.search(p, text) for p in error_indicators)
