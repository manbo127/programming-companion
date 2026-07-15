"""人工整理的知识条目。

这里只保存短小、可复核的概念摘要，不在运行时抓取网页。每个条目都指向
语言或平台的官方文档，便于用户继续阅读，也避免把搜索结果直接提升为提示词。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    title: str
    topics: tuple[str, ...]
    languages: tuple[str, ...]
    keywords: tuple[str, ...]
    summary: str
    source_title: str
    source_url: str

    def public_source(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_title": self.source_title,
            "url": self.source_url,
        }


ENTRIES = (
    KnowledgeEntry(
        id="python-exceptions",
        title="Python 异常与异常层次",
        topics=("异常处理", "报错分析"),
        languages=("python",),
        keywords=("exception", "error", "异常", "报错", "try", "except", "indexerror", "keyerror", "typeerror"),
        summary="Python 的内置异常按层次组织。捕获异常时应优先捕获最具体的类型，并结合 traceback 中最后一段定位直接原因；不要用裸 except 隐藏无关错误。",
        source_title="Python 官方文档：Built-in Exceptions",
        source_url="https://docs.python.org/3/library/exceptions.html",
    ),
    KnowledgeEntry(
        id="python-data-structures",
        title="Python 列表与常用数据结构",
        topics=("数组与列表", "栈与队列"),
        languages=("python",),
        keywords=("list", "列表", "数组", "索引", "index", "append", "pop", "stack", "queue", "栈", "队列"),
        summary="Python 列表是可变序列，索引范围为 -len(list) 到 len(list)-1。append 在尾部加入元素，pop 默认移除尾部；频繁从头部插入或删除时更适合 collections.deque。",
        source_title="Python 官方教程：Data Structures",
        source_url="https://docs.python.org/3/tutorial/datastructures.html",
    ),
    KnowledgeEntry(
        id="java-arrays",
        title="Java 数组",
        topics=("数组与列表",),
        languages=("java",),
        keywords=("array", "数组", "索引", "index", "arrayindexoutofboundsexception", "length"),
        summary="Java 数组创建后长度固定，下标从 0 开始，到 length-1 结束。访问前应确认索引满足 0 <= index < array.length。",
        source_title="Oracle Java Tutorials：Arrays",
        source_url="https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html",
    ),
    KnowledgeEntry(
        id="javascript-promises",
        title="JavaScript Promise 与异步链",
        topics=("Web开发", "并发与异步"),
        languages=("javascript", "typescript"),
        keywords=("promise", "async", "await", "异步", "then", "catch", "finally", "事件循环"),
        summary="Promise 表示异步操作最终完成或失败的结果。then/catch/finally 会返回新的 Promise；async/await 是基于 Promise 的语法，应通过 try/catch 处理 await 的拒绝结果。",
        source_title="MDN：Using promises",
        source_url="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises",
    ),
    KnowledgeEntry(
        id="cpp-raii",
        title="C++ RAII 与对象生命周期",
        topics=("面向对象", "内存管理"),
        languages=("cpp",),
        keywords=("raii", "析构", "构造", "生命周期", "内存", "资源", "智能指针", "unique_ptr", "shared_ptr"),
        summary="RAII 把资源的生命周期绑定到对象生命周期：构造时取得资源，析构时释放。优先使用标准容器和智能指针表达所有权，可减少泄漏和异常路径上的清理遗漏。",
        source_title="C++ Core Guidelines：R.1 Manage resources automatically using RAII",
        source_url="https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rr-raii",
    ),
    KnowledgeEntry(
        id="go-concurrency",
        title="Go goroutine 与 channel",
        topics=("并发与异步",),
        languages=("go",),
        keywords=("goroutine", "channel", "并发", "协程", "go routine", "chan", "deadlock", "死锁"),
        summary="goroutine 是并发执行的函数，channel 用于 goroutine 之间通信和同步。应明确由发送方负责关闭 channel，并避免无人接收或无人发送导致的永久阻塞。",
        source_title="Go 官方文档：Effective Go - Concurrency",
        source_url="https://go.dev/doc/effective_go#concurrency",
    ),
    KnowledgeEntry(
        id="rust-ownership",
        title="Rust 所有权与借用",
        topics=("内存管理", "所有权与借用"),
        languages=("rust",),
        keywords=("ownership", "borrow", "borrowed", "所有权", "借用", "生命周期", "moved value", "e0382", "引用"),
        summary="Rust 通过所有权规则在编译期管理内存：每个值有一个所有者，所有者离开作用域时值被释放；借用允许在不取得所有权的情况下引用值，并受可变性与作用域规则约束。",
        source_title="The Rust Programming Language：What Is Ownership?",
        source_url="https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html",
    ),
    KnowledgeEntry(
        id="postgresql-joins",
        title="SQL 表连接与连接条件",
        topics=("数据库与SQL",),
        languages=("sql",),
        keywords=("sql", "join", "连接", "inner join", "left join", "表", "on", "外键", "查询"),
        summary="JOIN 按连接条件组合多张表。INNER JOIN 只保留两侧匹配行，LEFT JOIN 保留左表全部行；连接条件应写清关联列，避免无条件连接产生笛卡尔积。",
        source_title="PostgreSQL 官方教程：Joins Between Tables",
        source_url="https://www.postgresql.org/docs/current/tutorial-join.html",
    ),
)
