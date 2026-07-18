from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent import A2UException, agent
from controller import controller, utc_now


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

SUBMIT_NATURAL_LANGUAGE_INTENT_EXAMPLE = {
    "request-id": "req-1001",
    "correlation-id": "corr-20260630-001",
    "tenant-id": "tenant-1",
    "intent": {
        "intent-id": "intent-1001",
        "mode": "natural-language",
        "submitter": {"type": "system", "id": "oss-a"},
        "timestamp": "2026-06-30T10:00:00Z",
        "natural-language": {
            "text": (
                "Analyze the service degradation of OTN service svc-1001, "
                "identify the root cause, assess affected resources, and "
                "recommend recovery actions."
            )
        },
    },
}

SUBMIT_STRUCTURED_INTENT_EXAMPLE = {
    "request-id": "req-1002",
    "correlation-id": "corr-20260630-002",
    "tenant-id": "tenant-1",
    "intent": {
        "intent-id": "intent-1002",
        "mode": "structured",
        "submitter": {"type": "system", "id": "oss-a"},
        "timestamp": "2026-06-30T10:05:00Z",
        "structured": {
            "type": "DIAGNOSE",
            "target-resource": "incident-56433218",
            "constraints-schema": "urn:ietf:params:xml:ns:yang:ietf-incident",
            "constraints": {
                "incident-no": 56433218,
                "name": "otn-service-degradation",
                "type": "problem",
                "incident-id": "line-fault-svc-1001",
                "service-instance": ["svc-1001"],
                "domain": "otn",
                "priority": "critical",
                "status": "raised",
                "ack-status": "unacknowledged",
                "category": "network",
                "probable-events": ["OTU_LOF", "ODU_AIS"],
                "detail": (
                    "OTN service svc-1001 is degraded. OTU_LOF and ODU_AIS "
                    "alarm events were observed on the working path."
                ),
                "resolve-advice": (
                    "Diagnose the probable root cause and provide recovery "
                    "suggestions. Prefer actions that minimize service impact."
                ),
            },
            "priority": 9,
        },
    },
}

RESOLVE_CONFIRMATION_EXAMPLE = {
    "request-id": "req-1003",
    "correlation-id": "corr-20260630-002",
    "tenant-id": "tenant-1",
    "confirmation-id": "conf-5001",
    "action": "approve",
    "resolved-by": "operator-a",
}

ABORT_TASK_EXAMPLE = {
    "request-id": "req-1004",
    "correlation-id": "corr-20260630-002",
    "tenant-id": "tenant-1",
    "task-id": "task-2001",
    "reason": "The operator cancelled the requested operation.",
}

app = FastAPI(
    title="NMA A2U Interface Demo API",
    version="0.3.3",
    description=(
        "A2U operational-state resources and RPC operations implemented for "
        "the IETF 126 Hackathon demo. Demo-support, controller-internal, "
        "compatibility, and notification-transport endpoints are intentionally "
        "hidden from this OpenAPI view."
    ),
    openapi_tags=[
        {
            "name": "A2U Operational State",
            "description": (
                "Read-only A2U agent-capabilities, intent, task, and "
                "confirmation operational-state objects."
            ),
        },
        {
            "name": "A2U RPC Operations",
            "description": (
                "A2U submit-intent, resolve-confirmation, and abort-task RPCs."
            ),
        },
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class InteractionRecorder:
    def __init__(self, path: Path):
        self.path = path
        self.items = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def record(
        self,
        method: str,
        path: str,
        request_body: Any,
        response_body: Any,
        status: int,
        note: str = "",
    ) -> None:
        self.items.append(
            {
                "interaction-id": f"http-{uuid.uuid4().hex[:8]}",
                "time": utc_now(),
                "method": method,
                "path": path,
                "request": request_body,
                "response": response_body,
                "status": status,
                "note": note,
            }
        )
        self.items = self.items[-300:]
        print(f"[A2U] {method:<6} {status} {path} :: {note}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.items = []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("[]", encoding="utf-8")


interactions = InteractionRecorder(DATA_DIR / "interaction-log.json")

# Dynamic subscriptions are transport support reused by A2U; they are not part
# of the ietf-nma-a2u module and are therefore hidden from the A2U-only docs.
subscriptions: dict[int, dict[str, Any]] = {}
next_subscription_id = 22


@app.exception_handler(A2UException)
async def a2u_exception_handler(request: Request, exc: A2UException):
    interactions.record(
        request.method,
        request.url.path,
        None,
        exc.payload,
        exc.status_code,
        "A2U error-info",
    )
    return JSONResponse(status_code=exc.status_code, content=exc.payload)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def controller_page():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/oss", response_class=HTMLResponse, include_in_schema=False)
async def oss_page():
    return (FRONTEND_DIR / "oss.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A2U operational state data
# ---------------------------------------------------------------------------

@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/agent-capabilities",
    tags=["A2U Operational State"],
    summary="Discover NMA capabilities",
)
async def get_agent_capabilities():
    path = "/restconf/data/ietf-nma-a2u:a2u/agent-capabilities"
    response = agent.capabilities()
    interactions.record("GET", path, None, response, 200, "A2U capability discovery")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/intent",
    tags=["A2U Operational State"],
    summary="List retained A2U intent objects",
)
async def list_intents():
    path = "/restconf/data/ietf-nma-a2u:a2u/intent"
    response = {"intent": agent.list_intents()}
    interactions.record("GET", path, None, response, 200, "A2U operational state")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/intent={intent_id}",
    tags=["A2U Operational State"],
    summary="Read one A2U intent object",
)
async def get_intent(intent_id: str):
    path = f"/restconf/data/ietf-nma-a2u:a2u/intent={intent_id}"
    response = agent.get_intent(intent_id)
    interactions.record("GET", path, None, response, 200, "A2U intent object")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/task",
    tags=["A2U Operational State"],
    summary="List A2U task objects",
)
async def list_tasks():
    path = "/restconf/data/ietf-nma-a2u:a2u/task"
    response = {"task": agent.list_tasks()}
    interactions.record("GET", path, None, response, 200, "A2U operational state")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/task={task_id}",
    tags=["A2U Operational State"],
    summary="Read one A2U task, plan, and result",
)
async def get_task(task_id: str):
    path = f"/restconf/data/ietf-nma-a2u:a2u/task={task_id}"
    response = agent.get_task(task_id)
    interactions.record("GET", path, None, response, 200, "A2U task object")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/confirmation",
    tags=["A2U Operational State"],
    summary="List A2U confirmation objects",
)
async def list_confirmations():
    path = "/restconf/data/ietf-nma-a2u:a2u/confirmation"
    response = {"confirmation": agent.list_confirmations()}
    interactions.record("GET", path, None, response, 200, "A2U operational state")
    return response


@app.get(
    "/restconf/data/ietf-nma-a2u:a2u/confirmation={confirmation_id}",
    tags=["A2U Operational State"],
    summary="Read a full A2U confirmation object",
)
async def get_confirmation(confirmation_id: str):
    path = f"/restconf/data/ietf-nma-a2u:a2u/confirmation={confirmation_id}"
    response = agent.get_confirmation(confirmation_id)
    interactions.record("GET", path, None, response, 200, "Full confirmation object")
    return response


# ---------------------------------------------------------------------------
# A2U RPCs
# ---------------------------------------------------------------------------

@app.post(
    "/restconf/operations/ietf-nma-a2u:submit-intent",
    tags=["A2U RPC Operations"],
    summary="Submit a natural-language or structured intent",
    status_code=202,
)
async def submit_intent(
    body: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "natural-language-incident": {
                "summary": "Natural-language OTN incident diagnosis intent",
                "description": (
                    "Uses the natural-language case of the intent mode choice. "
                    "The NMA creates the same task lifecycle as for structured input."
                ),
                "value": SUBMIT_NATURAL_LANGUAGE_INTENT_EXAMPLE,
            },
            "structured-incident": {
                "summary": "Structured OTN incident diagnosis intent",
                "description": (
                    "Carries ietf-incident-aligned information in the constraints "
                    "anydata field."
                ),
                "value": SUBMIT_STRUCTURED_INTENT_EXAMPLE,
            },
        },
        description="Input of the ietf-nma-a2u submit-intent RPC.",
    ),
):
    path = "/restconf/operations/ietf-nma-a2u:submit-intent"
    request_body = body.get("ietf-nma-a2u:input", body)
    response = await agent.submit_intent(request_body)
    interactions.record("POST", path, body, response, 202, "submit-intent RPC")
    return JSONResponse(status_code=202, content=response)


@app.post(
    "/restconf/operations/ietf-nma-a2u:resolve-confirmation",
    tags=["A2U RPC Operations"],
    summary="Resolve an A2U confirmation",
)
async def resolve_confirmation(
    body: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "approve": {
                "summary": "Approve a pending confirmation",
                "value": RESOLVE_CONFIRMATION_EXAMPLE,
            }
        },
        description="Input of the ietf-nma-a2u resolve-confirmation RPC.",
    ),
):
    path = "/restconf/operations/ietf-nma-a2u:resolve-confirmation"
    request_body = body.get("ietf-nma-a2u:input", body)
    response = await agent.resolve_confirmation(request_body)
    interactions.record("POST", path, body, response, 200, "resolve-confirmation RPC")
    return response


@app.post(
    "/restconf/operations/ietf-nma-a2u:abort-task",
    tags=["A2U RPC Operations"],
    summary="Abort an A2U task",
)
async def abort_task(
    body: dict[str, Any] = Body(
        ...,
        openapi_examples={
            "abort": {
                "summary": "Abort a running A2U task",
                "value": ABORT_TASK_EXAMPLE,
            }
        },
        description="Input of the ietf-nma-a2u abort-task RPC.",
    ),
):
    path = "/restconf/operations/ietf-nma-a2u:abort-task"
    request_body = body.get("ietf-nma-a2u:input", body)
    response = await agent.abort_task(request_body)
    interactions.record("POST", path, body, response, 200, "abort-task RPC")
    return response


# ---------------------------------------------------------------------------
# RFC 8639 / RFC 8650 notification subscription transport support
# ---------------------------------------------------------------------------

def _task_id_from_subscription_input(subscription_input: dict[str, Any]) -> str:
    # The standard filter carries the A2U task selection. A direct task-id is
    # accepted only as a demo compatibility fallback.
    direct = str(subscription_input.get("task-id", "")).strip()
    if direct:
        return direct
    xpath = str(subscription_input.get("stream-xpath-filter", ""))
    match = re.search(r"task-id\s*=\s*['\"]([^'\"]+)['\"]", xpath)
    return match.group(1) if match else ""


@app.post(
    "/restconf/operations/ietf-subscribed-notifications:establish-subscription",
    include_in_schema=False,
)
async def establish_subscription(body: dict[str, Any] = Body(default={})):
    global next_subscription_id
    path = "/restconf/operations/ietf-subscribed-notifications:establish-subscription"
    subscription_input = body.get("ietf-subscribed-notifications:input", body)
    task_id = _task_id_from_subscription_input(subscription_input)
    if not task_id:
        error = {
            "ietf-restconf:errors": {
                "error": [
                    {
                        "error-type": "application",
                        "error-tag": "invalid-value",
                        "error-severity": "error",
                        "error-message": (
                            "The stream-xpath-filter must select an "
                            "a2u-task-notification task-id."
                        ),
                    }
                ]
            }
        }
        interactions.record("POST", path, body, error, 400, "Subscription rejected")
        return JSONResponse(status_code=400, content=error)

    subscription_id = next_subscription_id
    next_subscription_id += 1
    uri = f"/restconf/subscriptions/{subscription_id}"
    subscriptions[subscription_id] = {
        "id": subscription_id,
        "task-id": task_id,
        "stream": subscription_input.get("stream", "NETCONF"),
        "filter": subscription_input.get("stream-xpath-filter"),
        "uri": uri,
        "after": 0,
        "active": False,
        "closed": False,
    }
    response = {"id": subscription_id, "uri": uri}
    interactions.record(
        "POST",
        path,
        body,
        response,
        200,
        "Dynamic subscription accepted; publisher returned id and URI",
    )
    return response


@app.get("/restconf/subscriptions/{subscription_id}", include_in_schema=False)
async def activate_subscription(subscription_id: int):
    subscription = subscriptions.get(subscription_id)
    if not subscription:
        return JSONResponse(
            status_code=404,
            content={
                "ietf-restconf:errors": {
                    "error": [
                        {
                            "error-type": "application",
                            "error-tag": "data-missing",
                            "error-severity": "error",
                            "error-message": "Subscription was not found.",
                        }
                    ]
                }
            },
        )
    if subscription["active"]:
        return JSONResponse(
            status_code=409,
            content={
                "ietf-restconf:errors": {
                    "error": [
                        {
                            "error-type": "protocol",
                            "error-tag": "resource-denied",
                            "error-severity": "error",
                            "error-message": (
                                "A notification stream is already active for this URI."
                            ),
                        }
                    ]
                }
            },
        )
    if subscription["closed"]:
        return JSONResponse(
            status_code=410,
            content={
                "ietf-restconf:errors": {
                    "error": [
                        {
                            "error-type": "application",
                            "error-tag": "operation-failed",
                            "error-severity": "error",
                            "error-message": "The dynamic subscription has ended.",
                        }
                    ]
                }
            },
        )

    subscription["active"] = True
    uri = subscription["uri"]
    interactions.record(
        "SSE",
        uri,
        None,
        {"id": subscription_id, "task-id": subscription["task-id"]},
        200,
        "One long-lived RFC 8650 stream activation; no periodic notification GET",
    )

    async def event_stream():
        try:
            async for sequence, notification in agent.stream_notifications(
                subscription["task-id"], subscription["after"]
            ):
                subscription["after"] = sequence
                a2u_payload = {
                    key: deepcopy(value)
                    for key, value in notification.items()
                    if key != "time"
                }
                envelope = {
                    "ietf-restconf:notification": {
                        "eventTime": notification.get("time", utc_now()),
                        "ietf-nma-a2u:a2u-task-notification": a2u_payload,
                    }
                }
                interactions.record(
                    "PUSH",
                    uri,
                    None,
                    envelope,
                    200,
                    (
                        "Publisher-pushed YANG notification: "
                        f"{notification.get('notification-type')}"
                    ),
                )
                yield f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n"
                if notification.get("notification-type") in {
                    "task-completed",
                    "task-failed",
                }:
                    subscription["closed"] = True
                    return
        finally:
            subscription["active"] = False

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Demo/controller support APIs (not part of A2U)
# ---------------------------------------------------------------------------

@app.get("/api/demo/state", include_in_schema=False)
async def demo_state():
    tasks = agent.list_tasks()
    return {
        **controller.snapshot(),
        "a2u": {
            "agent-capabilities": agent.capabilities(),
            "intents": agent.list_intents(),
            "tasks": tasks,
            "confirmations": agent.list_confirmations(),
            "latest-task": tasks[0] if tasks else None,
        },
    }


@app.get("/api/demo/interactions", include_in_schema=False)
async def demo_interactions():
    return {"interactions": list(reversed(interactions.items))}


@app.post("/api/demo/reset", include_in_schema=False)
async def reset_demo():
    global subscriptions, next_subscription_id
    agent.reset()
    state = controller.reset()
    interactions.clear()
    subscriptions = {}
    next_subscription_id = 22
    return {"success": True, "state": state}


@app.post("/api/demo/inject-incident", include_in_schema=False)
async def inject_incident():
    incident = controller.inject_otn_degradation()
    return {"success": True, "incident": incident}


@app.get("/api/demo/health", include_in_schema=False)
async def health():
    return {"status": "ok", "time": utc_now()}


# ---------------------------------------------------------------------------
# Compatibility aliases for the original demo (hidden from A2U-only docs)
# ---------------------------------------------------------------------------

@app.get("/nma/agent-capabilities", include_in_schema=False)
async def legacy_capabilities():
    return await get_agent_capabilities()


@app.post("/nma/intent", include_in_schema=False)
async def legacy_intent(body: dict[str, Any] = Body(...)):
    if "intent" in body:
        request = deepcopy(body)
        request.pop("task_id", None)
    elif body.get("mode") == "natural-language":
        request = {
            "request-id": f"legacy-{uuid.uuid4().hex[:8]}",
            "intent": {
                "mode": "natural-language",
                "submitter": {"type": "user", "id": "controller-ui"},
                "natural-language": {"text": body.get("text", "")},
            },
        }
    else:
        request = body
    return await submit_intent(request)


@app.get("/nma/tasks", include_in_schema=False)
async def legacy_tasks():
    return await list_tasks()


@app.get("/nma/tasks/{task_id}", include_in_schema=False)
async def legacy_task(task_id: str):
    return await get_task(task_id)


@app.post("/nma/confirm", include_in_schema=False)
async def legacy_confirm(body: dict[str, Any] = Body(...)):
    if "resolution" in body:
        request = {
            "confirmation-id": body.get("confirmation-id"),
            "action": (body.get("resolution") or {}).get("action"),
            "modified-params": (body.get("resolution") or {}).get("modified-params"),
            "resolved-by": "legacy-client",
        }
    else:
        request = body
    return await resolve_confirmation(request)


if __name__ == "__main__":
    import uvicorn

    print("=" * 76)
    print("NMA A2U Hackathon Demo")
    print("Domain Controller + NMA:  http://127.0.0.1:8000/")
    print("OSS/BSS A2U Client:        http://127.0.0.1:8000/oss")
    print("A2U-only OpenAPI:           http://127.0.0.1:8000/docs")
    print("=" * 76)
    uvicorn.run(app, host="0.0.0.0", port=8000)
