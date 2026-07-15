"""轻量、确定性知识检索器。"""
from dataclasses import dataclass

from .entries import ENTRIES, KnowledgeEntry


@dataclass(frozen=True)
class RetrievalResult:
    entries: tuple[KnowledgeEntry, ...]

    @property
    def sources(self) -> list[dict]:
        return [entry.public_source() for entry in self.entries]

    def prompt_context(self) -> str:
        if not self.entries:
            return ""
        blocks = []
        for index, entry in enumerate(self.entries, start=1):
            blocks.append(
                f"[{index}] {entry.title}\n"
                f"摘要：{entry.summary}\n"
                f"来源：{entry.source_title}（{entry.source_url}）"
            )
        return "\n\n".join(blocks)


class KnowledgeRetriever:
    """使用主题、语言和关键词打分，返回少量最相关条目。"""

    @staticmethod
    def retrieve(
        query: str,
        *,
        language: str = "unknown",
        topic: str | None = None,
        limit: int = 3,
    ) -> RetrievalResult:
        normalized = (query or "").lower()
        scored: list[tuple[int, KnowledgeEntry]] = []
        for entry in ENTRIES:
            keyword_hits = sum(1 for word in entry.keywords if word.lower() in normalized)
            topic_hit = bool(topic and topic in entry.topics)
            language_hit = language in entry.languages
            score = keyword_hits * 3 + int(topic_hit) * 4 + int(language_hit) * 2
            # 单独的语言命中不足以证明问题与该条目相关。
            if keyword_hits or topic_hit:
                scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return RetrievalResult(tuple(entry for _, entry in scored[:max(0, limit)]))
