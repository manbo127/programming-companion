"""部署后只读冒烟检查。用法：python scripts/smoke_test.py https://xiaomacode.xyz"""
import json
import sys
from urllib.request import Request, urlopen


def get_json(base_url: str, path: str) -> dict:
    request = Request(base_url.rstrip("/") + path, headers={"User-Agent": "codemate-smoke-test/1.0"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
        return json.load(response)


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        raise SystemExit("usage: python scripts/smoke_test.py https://your-domain.example")
    base_url = sys.argv[1]
    health = get_json(base_url, "/api/v1/health")
    ready = get_json(base_url, "/api/v1/ready")
    if health["data"]["status"] != "ok" or ready["data"]["status"] != "ready":
        raise RuntimeError("service is reachable but not ready")
    print("Smoke test passed: health=ok readiness=ready")


if __name__ == "__main__":
    main()
