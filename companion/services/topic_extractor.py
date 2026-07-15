"""面向初学者编程学习内容的可解释主题提取。"""
import re


class TopicExtractor:
    """从问题、代码和报错中提取一个稳定的课程知识点标签。"""

    TOPICS = {
        "递归": (r"递归|recursion|recursive",),
        "数组与列表": (r"数组|列表|array|list\b|vector",),
        "字符串": (r"字符串|string\b|char\b",),
        "循环": (r"循环|for\s|while\s|loop",),
        "条件分支": (r"条件|if\s|else\b|switch\b|分支",),
        "函数": (r"函数|function|def\s|方法|method",),
        "面向对象": (r"面向对象|类和对象|class\s|继承|封装|多态|oop",),
        "异常处理": (r"异常处理|try\b|except\b|catch\b|throw\b|exception",),
        "排序算法": (r"排序|sort|冒泡|快排|归并",),
        "查找算法": (r"查找|搜索|search|二分",),
        "链表": (r"链表|linked\s*list",),
        "栈与队列": (r"栈|队列|stack|queue",),
        "树与图": (r"二叉树|树结构|图论|binary\s*tree|graph",),
        "动态规划": (r"动态规划|dynamic\s*programming|\bdp\b",),
        "数据库与SQL": (r"数据库|\bsql\b|select\s|insert\s|update\s|join\s",),
        "Web开发": (r"flask|django|html|css|javascript|前端|后端|接口|\bapi\b",),
        "文件与IO": (r"文件|读写|file\b|input/output|\bio\b",),
        "并发编程": (r"线程|进程|并发|异步|thread|process|async|await",),
    }

    @classmethod
    def extract(cls, text: str = "", code: str = "", error: str = "") -> str | None:
        source = "\n".join(part for part in (text, code, error) if part).lower()
        if not source:
            return None
        scores = {}
        for topic, patterns in cls.TOPICS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, source, re.IGNORECASE))
            if score:
                scores[topic] = score
        if not scores:
            return None
        return max(scores, key=lambda topic: (scores[topic], -list(cls.TOPICS).index(topic)))
