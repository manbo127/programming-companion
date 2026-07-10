"""
评测脚本 — 设计 8 个代表性测试场景，使用 FakeLLM 或 --live DeepSeek。
用法:
  python scripts/run_evaluation.py           # FakeLLM
  python scripts/run_evaluation.py --live     # DeepSeek (付费)
"""
import argparse
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SCENARIOS = [
    {
        "id": 1,
        "name": "Python 语法错误解读",
        "message": "我的代码出错了，帮我看看",
        "code": "items = [1, 2, 3]\nfor i in range(len(items)):\n    print(items[i+1])",
        "error": "IndexError: list index out of range\n  File \"test.py\", line 3, in <module>",
        "expected_scene": "error",
        "evaluate": "解释索引从0开始、列表长度概念，不输出完整正确代码",
    },
    {
        "id": 2,
        "name": "逻辑错误解读",
        "message": "这段代码一直运行不停止，怎么回事？",
        "code": "i = 0\nwhile i < 10:\n    print(i)",
        "error": "",
        "expected_scene": "guidance",
        "evaluate": "解释循环条件逻辑、终止条件的重要性",
    },
    {
        "id": 3,
        "name": "解题思路引导 — 素数判断",
        "message": "如何用 Python 判断一个数是否是素数？",
        "code": "",
        "error": "",
        "expected_scene": "guidance",
        "evaluate": "分步引导：输入→判断逻辑→特殊情况→优化，不直接给代码",
    },
    {
        "id": 4,
        "name": "知识点问答 — 递归",
        "message": "什么是递归？能举个例子吗？",
        "code": "",
        "error": "",
        "expected_scene": "knowledge",
        "evaluate": "用套娃/镜子比喻解释，给出简单代码片段（≤5行）",
    },
    {
        "id": 5,
        "name": "激励话术 — 连续挫败",
        "message": "又错了",
        "code": "",
        "error": "IndexError: list index out of range",
        "expected_scene": "error",
        "evaluate": "连续第2次同样错误，应触发鼓励话术",
    },
    {
        "id": 6,
        "name": "多轮上下文指代",
        "message": "那列表和元组有什么区别？",
        "code": "",
        "error": "",
        "expected_scene": "knowledge",
        "evaluate": "理解'那'指代上文讨论的列表，无需重复说明",
    },
    {
        "id": 7,
        "name": "Java 错误解析",
        "message": "Java 代码报错了",
        "code": "public class Main {\n  public static void main(String[] args) {\n    int[] arr = {1,2,3};\n    System.out.println(arr[5]);\n  }\n}",
        "error": "Exception in thread \"main\" java.lang.ArrayIndexOutOfBoundsException: 5",
        "expected_scene": "error",
        "evaluate": "识别 Java 异常类型，解释数组越界",
    },
    {
        "id": 8,
        "name": "跨会话画像和提醒",
        "message": "我最近总是遇到索引越界的问题",
        "code": "",
        "error": "",
        "expected_scene": "general",
        "evaluate": "触发 error_type=IndexError 的重复检测，生成提醒",
    },
]


def run_fake_evaluation():
    """使用 FakeLLM 运行评测。"""
    from companion import create_app
    from companion.extensions import db
    from companion.services.chat_service import ChatService
    from companion.llm.fake import FakeLLM
    from companion.repositories.conversation_repository import ConversationRepository

    app = create_app(config_override={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "eval",
    })
    app.app_context().push()
    db.create_all()

    # 创建测试 client 和会话
    from companion.repositories.profile_repository import ProfileRepository
    client = ProfileRepository.get_or_create_client("eval-client")
    conv = ConversationRepository.create(client.id, title="评测会话")
    db.session.commit()

    chat_service = ChatService(llm=FakeLLM())

    print("=" * 60)
    print("  程序设计学习智能学伴 — 评测")
    print(f"  模式: FakeLLM")
    print(f"  场景数: {len(SCENARIOS)}")
    print("=" * 60)

    for s in SCENARIOS:
        print(f"\n--- 场景 {s['id']}: {s['name']} ---")
        print(f"  输入: {s['message'][:60]}")
        t0 = time.monotonic()
        result = chat_service.process_message(
            client_id=client.id,
            conversation_id=conv.id,
            message_text=s["message"],
            code=s.get("code", ""),
            error_text=s.get("error", ""),
        )
        elapsed = int((time.monotonic() - t0) * 1000)
        actual_scene = result["scene"]
        match = "✓" if actual_scene == s["expected_scene"] else "✗"
        print(f"  场景: {actual_scene} (期望 {s['expected_scene']}) {match}")
        print(f"  回复: {result['reply'][:100]}...")
        print(f"  耗时: {elapsed}ms")
        print(f"  评价标准: {s['evaluate']}")

    print(f"\n{'=' * 60}")
    print("  评测完成。请人工审核每条回复的质量。")
    print("  (FakeLLM 输出不代表真实模型效果，仅验证流程正确性)")


def run_live_evaluation():
    """使用 DeepSeek 运行评测。"""
    import os
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("错误: 请设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    from companion import create_app
    from companion.extensions import db
    from companion.services.chat_service import ChatService
    from companion.llm.deepseek import DeepSeekGateway
    from companion.repositories.conversation_repository import ConversationRepository

    app = create_app()
    app.app_context().push()

    from companion.repositories.profile_repository import ProfileRepository
    client = ProfileRepository.get_or_create_client("eval-live-client")
    conv = ConversationRepository.create(client.id, title="实机评测")
    db.session.commit()

    llm = DeepSeekGateway(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )
    chat_service = ChatService(llm=llm)

    print("=" * 60)
    print("  程序设计学习智能学伴 — 实机评测 (DeepSeek)")
    print(f"  场景数: {len(SCENARIOS)}")
    print("=" * 60)

    for s in SCENARIOS:
        print(f"\n--- 场景 {s['id']}: {s['name']} ---")
        print(f"  输入: {s['message'][:60]}")
        t0 = time.monotonic()
        try:
            result = chat_service.process_message(
                client_id=client.id,
                conversation_id=conv.id,
                message_text=s["message"],
                code=s.get("code", ""),
                error_text=s.get("error", ""),
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            actual_scene = result["scene"]
            match = "✓" if actual_scene == s["expected_scene"] else "✗"
            print(f"  场景: {actual_scene} (期望 {s['expected_scene']}) {match}")
            print(f"  回复:\n{result['reply']}")
            print(f"  耗时: {elapsed}ms")
        except Exception as e:
            print(f"  ❌ 调用失败: {e}")
        print(f"  评价标准: {s['evaluate']}")

    print(f"\n{'=' * 60}")
    print("  实机评测完成。请在课程报告中填写每条回复的质量评价。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="使用 DeepSeek 实机评测")
    args = parser.parse_args()

    if args.live:
        run_live_evaluation()
    else:
        run_fake_evaluation()
