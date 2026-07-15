"""无外部依赖的进程级运行指标。

单机 SQLite 部署只有一个 Gunicorn worker，因此这些指标可直接用于课程演示和
轻量告警。迁移到多 worker 后应改接 Prometheus/OpenTelemetry 聚合器。
"""
from collections import Counter
from threading import Lock
import time


class Observability:
    _lock = Lock()
    _started_at = time.time()
    _requests = 0
    _request_errors = 0
    _request_latency_ms = 0
    _status_codes = Counter()
    _endpoints = Counter()
    _llm_calls = 0
    _llm_failures = 0
    _llm_latency_ms = 0
    _llm_input_tokens = 0
    _llm_output_tokens = 0
    _llm_retries = 0

    @classmethod
    def record_request(cls, endpoint: str, status_code: int, latency_ms: int):
        with cls._lock:
            cls._requests += 1
            cls._request_latency_ms += max(latency_ms, 0)
            cls._status_codes[f"{status_code // 100}xx"] += 1
            cls._endpoints[endpoint or "unknown"] += 1
            if status_code >= 500:
                cls._request_errors += 1

    @classmethod
    def record_llm(cls, response=None, *, failed: bool = False):
        with cls._lock:
            cls._llm_calls += 1
            if failed:
                cls._llm_failures += 1
                return
            cls._llm_latency_ms += int(getattr(response, "latency_ms", 0) or 0)
            cls._llm_input_tokens += int(getattr(response, "input_tokens", 0) or 0)
            cls._llm_output_tokens += int(getattr(response, "output_tokens", 0) or 0)
            cls._llm_retries += max(int(getattr(response, "attempts", 1) or 1) - 1, 0)

    @classmethod
    def snapshot(cls) -> dict:
        with cls._lock:
            request_avg = round(cls._request_latency_ms / cls._requests, 2) if cls._requests else 0
            llm_successes = cls._llm_calls - cls._llm_failures
            llm_avg = round(cls._llm_latency_ms / llm_successes, 2) if llm_successes else 0
            return {
                "uptime_seconds": max(0, int(time.time() - cls._started_at)),
                "http": {
                    "requests_total": cls._requests,
                    "server_errors_total": cls._request_errors,
                    "average_latency_ms": request_avg,
                    "status_classes": dict(cls._status_codes),
                    "top_endpoints": cls._endpoints.most_common(10),
                },
                "llm": {
                    "calls_total": cls._llm_calls,
                    "failures_total": cls._llm_failures,
                    "retries_total": cls._llm_retries,
                    "average_latency_ms": llm_avg,
                    "input_tokens_total": cls._llm_input_tokens,
                    "output_tokens_total": cls._llm_output_tokens,
                },
            }

    @classmethod
    def reset_for_testing(cls):
        with cls._lock:
            cls._started_at = time.time()
            cls._requests = cls._request_errors = cls._request_latency_ms = 0
            cls._status_codes.clear()
            cls._endpoints.clear()
            cls._llm_calls = cls._llm_failures = cls._llm_latency_ms = 0
            cls._llm_input_tokens = cls._llm_output_tokens = cls._llm_retries = 0
