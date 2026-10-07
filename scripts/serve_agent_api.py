from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from langgraph.types import Command

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novelops_agent.agent import _get_repository, build_agent
from novelops_agent.intent import classify_intent_locally


class TargetResolutionError(ValueError):
    pass


class AgentService:
    def __init__(self) -> None:
        self.runner = asyncio.Runner()
        self.repository = _get_repository()
        self.app = build_agent(repo=self.repository)
        self.targets: dict[str, dict[str, str]] = {}

    def investigate(self, novel_id: str, request: str) -> dict[str, Any]:
        target = self._resolve_target(novel_id, request)
        thread_id = str(uuid.uuid4())
        self.targets[thread_id] = target
        result = self.runner.run(
            self.app.ainvoke(
                {"novel_id": target["id"], "request": request},
                config={"configurable": {"thread_id": thread_id}},
            )
        )
        return self._response(result, thread_id, target)

    def approve(self, thread_id: str, approved: bool) -> dict[str, Any]:
        result = self.runner.run(
            self.app.ainvoke(
                Command(resume={"approved": approved, "reviewer": "web_user"}),
                config={"configurable": {"thread_id": thread_id}},
            )
        )
        return self._response(result, thread_id, self.targets.get(thread_id))

    def _resolve_target(self, novel_id: str, request: str) -> dict[str, str]:
        explicit_id = novel_id.strip().upper()
        if not explicit_id:
            match = re.search(r"(?<![A-Z0-9])N\d{3}(?!\d)", request.upper())
            explicit_id = match.group(0) if match else ""
        if explicit_id:
            novel = self.repository.novel(explicit_id)
            return {"id": novel["id"], "title": novel["title"]}

        normalized_request = request.replace("《", "").replace("》", "").replace(" ", "")
        matches = [
            novel
            for novel in self.repository.novels()
            if str(novel.get("title", "")).replace(" ", "") in normalized_request
        ]
        if len(matches) == 1:
            return {"id": matches[0]["id"], "title": matches[0]["title"]}
        if classify_intent_locally(request).intent == "policy_lookup":
            return {"id": "", "title": "制度查询"}
        if len(matches) > 1:
            titles = "、".join(f"《{item['title']}》" for item in matches[:5])
            raise TargetResolutionError(f"匹配到多部作品：{titles}，请补充更完整的书名。")
        raise TargetResolutionError(
            "未识别到要调查的作品，请在问题中写明书名，"
            "例如：检查《雾港来信》的结算。"
        )

    @staticmethod
    def _response(
        result: dict[str, Any],
        thread_id: str,
        target: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "thread_id": thread_id,
            "target": target,
            "intent": result.get("intent", {}),
            "plan": result.get("plan", []),
            "traces": result.get("traces", []),
            "report": result.get("report", {}),
            "case": result.get("case"),
            "requires_approval": "__interrupt__" in result,
        }


SERVICE: AgentService | None = None


class Handler(BaseHTTPRequestHandler):
    server_version = "NovelOpsAgentAPI/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._json(204, {})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if SERVICE is None:
                raise RuntimeError("Agent service is not initialized")
            if self.path == "/investigate":
                novel_id = str(body.get("novel_id", "")).strip().upper()
                request = str(body.get("request", "")).strip()
                if not request:
                    self._json(400, {"error": "request不能为空"})
                    return
                self._json(200, SERVICE.investigate(novel_id, request))
                return
            if self.path == "/approve":
                thread_id = str(body.get("thread_id", "")).strip()
                if not thread_id or not isinstance(body.get("approved"), bool):
                    self._json(400, {"error": "thread_id和approved不能为空"})
                    return
                self._json(200, SERVICE.approve(thread_id, body["approved"]))
                return
            self._json(404, {"error": "not_found"})
        except TargetResolutionError as exc:
            self._json(422, {"error": str(exc), "needs_target": True})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[agent-api] {self.address_string()} - {format % args}")


def main() -> None:
    global SERVICE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NovelOps Agent local API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    SERVICE = AgentService()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"NovelOps Agent API running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        SERVICE.runner.close()


if __name__ == "__main__":
    main()
