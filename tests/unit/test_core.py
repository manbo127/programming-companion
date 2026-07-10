"""
核心逻辑单元测试 — 使用 FakeLLM，无需网络。
"""
import pytest
from companion.services.classifier import MessageClassifier
from companion.services.motivation import MotivationEngine
from companion.utils.code_utils import detect_language, parse_error_info
from companion.llm.fake import FakeLLM


class TestClassifier:
    def setup_method(self):
        self.c = MessageClassifier()

    def test_error_with_code_and_error(self):
        r = self.c.classify(text="帮我看看", code="print(1/0)", error="ZeroDivisionError")
        assert r.scene == "error"

    def test_error_only_text(self):
        r = self.c.classify(text="我的代码又报错了，怎么改")
        assert r.scene == "error"

    def test_guidance_keywords(self):
        r = self.c.classify(text="冒泡排序怎么做")
        assert r.scene == "guidance"

    def test_knowledge_keywords(self):
        r = self.c.classify(text="什么是递归")
        assert r.scene == "knowledge"

    def test_general_fallback(self):
        r = self.c.classify(text="你好")
        assert r.scene == "general"

    def test_error_only_input(self):
        """仅填写 error 字段也应识别为 error 场景。"""
        r = self.c.classify(text="", code="", error="IndexError: list index out of range")
        assert r.scene == "error"


class TestLanguageDetection:
    def test_python_def(self):
        assert detect_language("def foo():\n    return 1") == "python"

    def test_java_main(self):
        assert detect_language("public class Main {\n  public static void main(String[] args) {}") == "java"

    def test_c_include(self):
        assert detect_language('#include <stdio.h>\nint main() {}') == "c"

    def test_cpp_iostream(self):
        assert detect_language('#include <iostream>\nint main() { std::cout << "hi"; }') == "cpp"

    def test_unknown_empty(self):
        assert detect_language("") == "unknown"


class TestErrorParsing:
    def test_python_index_error(self):
        r = parse_error_info('IndexError: list index out of range\n  File "test.py", line 3')
        assert r["error_type"] == "IndexError"
        assert r["line"] == 3

    def test_java_exception(self):
        r = parse_error_info('Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException: 5')
        assert r["error_type"] == "java.lang.ArrayIndexOutOfBoundsException"


class TestMotivationPerConversation:
    def test_separate_counters(self):
        a = MotivationEngine.for_conversation("conv-a")
        b = MotivationEngine.for_conversation("conv-b")
        a.analyze("好难啊不会")
        assert a.consecutive_errors == 1
        assert b.consecutive_errors == 0

    def test_encouragement_threshold(self):
        m = MotivationEngine.for_conversation("test")
        m.analyze("好难")
        m.analyze("又错了")
        assert m.get_encouragement() is not None

    def test_praise_threshold(self):
        m = MotivationEngine.for_conversation("test")
        for _ in range(3):
            m.analyze("我明白了")
        assert m.get_praise() is not None


class TestFakeLLM:
    def test_returns_default(self):
        llm = FakeLLM()
        resp = llm.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "这是一个测试回复。"
        assert resp.model == "fake"

    def test_custom_responses(self):
        llm = FakeLLM(responses=["第一句", "第二句"])
        assert llm.chat([]).content == "第一句"
        assert llm.chat([]).content == "第二句"
        assert llm.chat([]).content == "这是一个测试回复。"


class TestPromptConstraints:
    def test_error_scene_forbids_full_code(self):
        from companion.prompts.builder import build_system_prompt
        prompt = build_system_prompt("error")
        assert "不要输出完整的修复后代码" in prompt or "直接输出" in prompt

    def test_guidance_scene_no_full_answer(self):
        from companion.prompts.builder import build_system_prompt
        prompt = build_system_prompt("guidance")
        assert "绝对不要直接给出完整的代码答案" in prompt or "不要直接给" in prompt

    def test_has_prompt_version(self):
        from companion.prompts.builder import build_system_prompt
        prompt = build_system_prompt("general")
        assert "Prompt Version:" in prompt
