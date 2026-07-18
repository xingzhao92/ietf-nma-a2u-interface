"""
Network Management Agent implementation for the A2U Hackathon demo.

Exposed A2U objects and operations follow draft-zhao-nmop-nma-a2u-yang-00:
- operational state: agent-capabilities, intent, task, confirmation
- RPCs: submit-intent, resolve-confirmation, abort-task
- notification: a2u-task-notification
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from controller import VirtualController, controller, utc_now


INCIDENT_SCHEMA = "urn:ietf:params:xml:ns:yang:ietf-incident"

TASK_STATES = {
    "PENDING",
    "ANALYZING",
    "AWAITING_CLARIFICATION",
    "PLANNING",
    "AWAITING_CONFIRMATION",
    "EXECUTING",
    "COMPLETED",
    "FAILED",
    "ABORTED",
}

INTENT_TYPES = {
    "CREATE",
    "DELETE",
    "MODIFY",
    "QUERY",
    "REPORT",
    "DIAGNOSE",
    "REMEDIATE",
    "OPTIMIZE",
    "ASSURE",
}

CONFIRMATION_ACTIONS = {
    "approve",
    "reject",
    "modify-and-approve",
    "escalate-to-human",
}


class A2UException(Exception):
    def __init__(
        self,
        error_type: str,
        error_code: str,
        error_message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
        target: str = "",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(error_message)
        self.status_code = status_code
        self.payload = {
            "error-type": error_type,
            "error-code": error_code,
            "error-message": error_message,
            "retryable": retryable,
            "target": target,
        }
        if details is not None:
            self.payload["details"] = details


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _iso(value: str | None = None) -> str:
    return value or utc_now()


class A2UAgent:
    def __init__(
        self,
        controller_instance: VirtualController = controller,
        data_dir: str | Path = "data",
        demo_delay: float | None = None,
    ):
        self.controller = controller_instance
        self.path = Path(data_dir) / "a2u-sessions.json"
        self.lock = threading.RLock()
        # A deliberate pace makes the autonomous workflow observable during
        # a live demonstration. Tests can still pass an explicit small value.
        self.demo_delay = (
            float(demo_delay)
            if demo_delay is not None
            else float(os.getenv("A2U_DEMO_DELAY_SECONDS", "1.25"))
        )
        self.state = self._load()
        self._running: dict[str, asyncio.Task] = {}

    def capabilities(self) -> dict[str, Any]:
        return {
            "agent-id": "nma-transport-1",
            "version": "0.1.0-hackathon",
            "skills": [
                {
                    "skill-id": "otn-incident-handling",
                    "name": "OTN incident handling",
                    "description": (
                        "Analyze OTN alarms, performance degradation, and service "
                        "impact, and propose or execute recovery actions."
                    ),
                    "input-schema": INCIDENT_SCHEMA,
                    "confirmation-required": True,
                    "tags": ["transport", "otn", "incident", "remediation"],
                },
                {
                    "skill-id": "otn-service-provisioning",
                    "name": "OTN service provisioning",
                    "description": (
                        "Create and query transport services through the controller."
                    ),
                    "input-schema": "urn:demo:otn-service-intent",
                    "confirmation-required": True,
                    "tags": ["transport", "otn", "service", "provisioning"],
                },
            ],
            "policies": {
                "human-in-the-loop": True,
                "max-timeout-seconds": 1800,
            },
        }

    def reset(self) -> None:
        with self.lock:
            for task in self._running.values():
                task.cancel()
            self._running.clear()
            self.state = self._empty_state()
            self._save()

    async def submit_intent(self, request: dict[str, Any]) -> dict[str, Any]:
        metadata = self._metadata(request)
        body = request.get("intent")
        if not isinstance(body, dict):
            raise A2UException(
                "invalid-request",
                "A2U-INTENT-001",
                "The submit-intent RPC requires an intent object.",
                target="submit-intent.intent",
            )

        mode = body.get("mode")
        if mode not in {"natural-language", "structured"}:
            raise A2UException(
                "unprocessable-content",
                "A2U-INTENT-002",
                "intent.mode must be natural-language or structured.",
                target="submit-intent.intent.mode",
            )

        if mode == "natural-language":
            text = ((body.get("natural-language") or {}).get("text") or "").strip()
            if not text:
                raise A2UException(
                    "unprocessable-content",
                    "A2U-INTENT-003",
                    "Natural-language intent text is empty.",
                    target="submit-intent.intent.natural-language.text",
                )
        else:
            structured = body.get("structured") or {}
            intent_type = str(structured.get("type", "")).upper()
            if intent_type not in INTENT_TYPES:
                raise A2UException(
                    "unprocessable-content",
                    "A2U-INTENT-004",
                    "Structured intent type is not supported.",
                    target="submit-intent.intent.structured.type",
                    details={"supported-types": sorted(INTENT_TYPES)},
                )
            if "constraints" not in structured:
                raise A2UException(
                    "unprocessable-content",
                    "A2U-INTENT-005",
                    "Structured intent requires constraints.",
                    target="submit-intent.intent.structured.constraints",
                )

        intent_id = body.get("intent-id") or _id("intent")
        task_id = _id("task")
        timestamp = body.get("timestamp") or utc_now()
        submitter = body.get("submitter") or {"type": "system", "id": "oss-simulator"}

        intent_object: dict[str, Any] = {
            "intent-id": intent_id,
            "mode": mode,
            "submitter": submitter,
            "timestamp": timestamp,
            "state": "PENDING",
            "task-id": task_id,
        }
        if mode == "natural-language":
            intent_object["natural-language"] = deepcopy(body["natural-language"])
        else:
            structured = deepcopy(body["structured"])
            structured["type"] = str(structured["type"]).upper()
            structured.setdefault("priority", 5)
            intent_object["structured"] = structured
        intent_object["estimated-completion"] = 300

        task_object = {
            "task-id": task_id,
            "parent-intent-id": intent_id,
            "state": "PENDING",
            "created-at": utc_now(),
            "updated-at": utc_now(),
            "plan": [],
            "result": {},
        }

        with self.lock:
            self.state["intents"][intent_id] = intent_object
            self.state["tasks"][task_id] = task_object
            self.state["internal"][task_id] = {
                "request-metadata": metadata,
                "scenario": self._classify(intent_object),
                "confirmation-id": None,
                "execution-params": {},
            }
            self._save()

        response = {
            **metadata,
            "accepted": True,
            "intent-id": intent_id,
            "task-id": task_id,
            "state": "PENDING",
            "task": deepcopy(task_object),
        }
        running = asyncio.create_task(self._run_task(task_id))
        self._running[task_id] = running
        running.add_done_callback(lambda _: self._running.pop(task_id, None))
        return response

    async def resolve_confirmation(self, request: dict[str, Any]) -> dict[str, Any]:
        confirmation_id = str(request.get("confirmation-id", ""))
        action = str(request.get("action", ""))
        if not confirmation_id:
            raise A2UException(
                "invalid-request",
                "A2U-CONFIRM-001",
                "confirmation-id is required.",
                target="resolve-confirmation.confirmation-id",
            )
        if action not in CONFIRMATION_ACTIONS:
            raise A2UException(
                "unprocessable-content",
                "A2U-CONFIRM-002",
                "Unsupported confirmation action.",
                target="resolve-confirmation.action",
                details={"allowed-actions": sorted(CONFIRMATION_ACTIONS)},
            )

        with self.lock:
            conf = self.state["confirmations"].get(confirmation_id)
            if not conf:
                raise A2UException(
                    "not-found",
                    "A2U-CONFIRM-003",
                    f"Confirmation {confirmation_id} was not found.",
                    status_code=404,
                    target="resolve-confirmation.confirmation-id",
                )
            if conf.get("status") != "pending":
                raise A2UException(
                    "conflict",
                    "A2U-CONFIRM-004",
                    f"Confirmation is already {conf.get('status')}.",
                    status_code=409,
                    target="resolve-confirmation.confirmation-id",
                )
            if action not in conf.get("allowed-actions", []):
                raise A2UException(
                    "forbidden",
                    "A2U-CONFIRM-005",
                    "The selected action is not allowed for this confirmation.",
                    status_code=403,
                    target="resolve-confirmation.action",
                )

            task_id = conf["task-id"]
            task = self.state["tasks"][task_id]
            resolution: dict[str, Any] = {
                "action": action,
                "resolved-by": request.get("resolved-by", "operator-a"),
                "resolved-at": utc_now(),
            }
            if request.get("modified-params-schema"):
                resolution["modified-params-schema"] = request["modified-params-schema"]
            if request.get("modified-params") is not None:
                resolution["modified-params"] = deepcopy(request["modified-params"])
            conf["resolution"] = resolution

            if action == "reject":
                conf["status"] = "rejected"
                self._set_task_state(task_id, "ABORTED")
                task["result"] = {
                    "summary": "The proposed action was rejected by the A2U client.",
                    "affected-resources": self._affected_resources(task_id),
                }
                self._notify(
                    task_id,
                    "task-failed",
                    {
                        "task-failed": {
                            "reason": "The proposed action was rejected.",
                            "failed-step-id": self._confirmation_step_id(task),
                        }
                    },
                )
                self._save()
                return {
                    "confirmation-id": confirmation_id,
                    "task-id": task_id,
                    "status": "rejected",
                    "task-state": "ABORTED",
                }

            if action == "escalate-to-human":
                conf["status"] = "escalated"
                self._save()
                return {
                    "confirmation-id": confirmation_id,
                    "task-id": task_id,
                    "status": "escalated",
                    "task-state": task["state"],
                }

            conf["status"] = "modified" if action == "modify-and-approve" else "approved"
            internal = self.state["internal"][task_id]
            internal["execution-params"] = deepcopy(request.get("modified-params") or {})
            self._set_task_state(task_id, "EXECUTING")
            self._save()

        running = asyncio.create_task(self._execute_confirmed_task(task_id))
        self._running[f"execute:{task_id}"] = running
        running.add_done_callback(lambda _: self._running.pop(f"execute:{task_id}", None))
        return {
            "confirmation-id": confirmation_id,
            "task-id": task_id,
            "status": conf["status"],
            "task-state": "EXECUTING",
        }

    async def abort_task(self, request: dict[str, Any]) -> dict[str, Any]:
        task_id = str(request.get("task-id", ""))
        if not task_id:
            raise A2UException(
                "invalid-request",
                "A2U-ABORT-001",
                "task-id is required.",
                target="abort-task.task-id",
            )
        with self.lock:
            task = self.state["tasks"].get(task_id)
            if not task:
                raise A2UException(
                    "not-found",
                    "A2U-ABORT-002",
                    f"Task {task_id} was not found.",
                    status_code=404,
                    target="abort-task.task-id",
                )
            if task["state"] in {"COMPLETED", "FAILED", "ABORTED"}:
                raise A2UException(
                    "conflict",
                    "A2U-ABORT-003",
                    f"Task is already {task['state']}.",
                    status_code=409,
                    target="abort-task.task-id",
                )
            self._set_task_state(task_id, "ABORTED")
            task["result"] = {
                "summary": request.get("reason") or "Task aborted by A2U client.",
                "affected-resources": self._affected_resources(task_id),
            }
            self._notify(
                task_id,
                "task-failed",
                {"task-failed": {"reason": task["result"]["summary"]}},
            )
            self._save()
        return {"task-id": task_id, "state": "ABORTED"}

    def get_intent(self, intent_id: str) -> dict[str, Any]:
        with self.lock:
            value = self.state["intents"].get(intent_id)
            if not value:
                self._not_found("intent", intent_id)
            return deepcopy(value)

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self.lock:
            value = self.state["tasks"].get(task_id)
            if not value:
                self._not_found("task", task_id)
            return deepcopy(value)

    def get_confirmation(self, confirmation_id: str) -> dict[str, Any]:
        with self.lock:
            value = self.state["confirmations"].get(confirmation_id)
            if not value:
                self._not_found("confirmation", confirmation_id)
            return deepcopy(value)

    def list_intents(self) -> list[dict[str, Any]]:
        return self._sorted_values("intents", "timestamp")

    def list_tasks(self) -> list[dict[str, Any]]:
        return self._sorted_values("tasks", "created-at")

    def list_confirmations(self) -> list[dict[str, Any]]:
        return self._sorted_values("confirmations", "confirmation-id")

    def notifications_for_task(self, task_id: str, after: int = 0) -> list[dict[str, Any]]:
        with self.lock:
            return [
                deepcopy(item)
                for item in self.state["notifications"]
                if item["_sequence"] > after and item["task-id"] == task_id
            ]

    async def stream_notifications(
        self,
        task_id: str,
        after: int = 0,
    ) -> AsyncGenerator[tuple[int, dict[str, Any]], None]:
        """Replay stored notifications, then poll for new YANG notifications."""
        current = after
        idle = 0
        while True:
            events = self.notifications_for_task(task_id, current)
            if events:
                idle = 0
                for event in events:
                    current = event["_sequence"]
                    clean = {k: v for k, v in event.items() if not k.startswith("_")}
                    yield current, clean
            else:
                idle += 1

            task = self.get_task(task_id)
            if task["state"] in {"COMPLETED", "FAILED", "ABORTED"} and not self.notifications_for_task(task_id, current):
                return
            if idle > 180:
                return
            await asyncio.sleep(0.4)

    async def wait_for_state(
        self,
        task_id: str,
        states: set[str],
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            task = self.get_task(task_id)
            if task["state"] in states:
                return task
            await asyncio.sleep(0.05)
        raise TimeoutError(f"Task {task_id} did not reach {states}")

    async def _demo_pause(self, multiplier: float = 1.0) -> None:
        """Pause between visible demo phases without blocking the event loop."""
        await asyncio.sleep(max(0.0, self.demo_delay * multiplier))

    def _notify_step_completed(
        self,
        task_id: str,
        step_id: str,
        observation: str,
    ) -> None:
        self._notify(
            task_id,
            "step-completed",
            {
                "step-completed": {
                    "step-id": step_id,
                    "observation": observation,
                }
            },
        )
        self._save()

    async def _run_task(self, task_id: str) -> None:
        try:
            # Keep PENDING visible after submit-intent returns, then move into
            # ANALYZING so the audience can follow the lifecycle transition.
            await self._demo_pause(0.70)
            self._set_task_state(task_id, "ANALYZING")
            self._save()
            await self._demo_pause(1.00)
            scenario = self.state["internal"][task_id]["scenario"]
            if scenario == "incident":
                await self._prepare_incident_task(task_id)
            elif scenario == "service-create":
                await self._prepare_service_creation_task(task_id)
            else:
                await self._run_query_task(task_id)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._fail_task(task_id, "A2U-INTERNAL-001", str(exc))

    async def _prepare_incident_task(self, task_id: str) -> None:
        intent = self._intent_for_task(task_id)
        constraints = self._incident_constraints(intent)
        incident_no = int(constraints.get("incident-no", 56433218))
        if not self.controller.get_incident(incident_no):
            self.controller.inject_otn_degradation()

        target = f"incident-{incident_no}"
        self._replace_plan(
            task_id,
            [
                {
                    "step-id": "step-1",
                    "action": "collect-controller-context",
                    "target": target,
                    "status": "running",
                },
                {
                    "step-id": "step-2",
                    "action": "analyze-network-incident",
                    "target": target,
                    "status": "pending",
                },
                {
                    "step-id": "step-3",
                    "action": "generate-incident-resolution-plan",
                    "target": target,
                    "status": "pending",
                },
                {
                    "step-id": "step-4",
                    "action": "request-confirmation-before-incident-resolution",
                    "target": target,
                    "status": "pending",
                },
            ],
        )

        # A2C data acquisition: the NMA calls controller functions rather than
        # reading the demo data files or asking the controller to diagnose.
        incident_context = self.controller.a2c_get_incident(incident_no)
        await self._demo_pause(0.40)
        service_id = incident_context["service-instance"][0]
        service_context = self.controller.a2c_get_service(service_id)
        await self._demo_pause(0.40)
        alarm_context = self.controller.a2c_get_alarms(incident_no)
        await self._demo_pause(0.40)
        topology_context = self.controller.a2c_get_topology(service_id)
        await self._demo_pause(0.40)
        with self.lock:
            self.state["internal"][task_id]["a2c-context"] = {
                "incident": deepcopy(incident_context),
                "service": deepcopy(service_context),
                "alarms": deepcopy(alarm_context),
                "topology": deepcopy(topology_context),
            }
            self._save()
        step1_observation = (
            "The NMA invoked controller get-incident, get-service, "
            "get-alarms, and get-topology functions and assembled the "
            "incident context."
        )
        self._complete_step(task_id, "step-1", step1_observation)
        self._notify_step_completed(task_id, "step-1", step1_observation)
        await self._demo_pause(0.75)

        # NMA-local analysis and decision logic based on A2C query results.
        self._run_step(task_id, "step-2")
        await self._demo_pause(1.10)
        alarm_types = {item.get("event-type") for item in alarm_context}
        working_path = service_context.get("working-path", [])
        has_affected_segment = "NE2" in working_path and "NE3" in working_path
        if {"OTU_LOF", "ODU_AIS"}.issubset(alarm_types) and has_affected_segment:
            probable_cause = "working-path-line-failure"
            confidence = 0.96
            affected = ["NE2/OTU-1", "NE3/ODU-1"]
        else:
            probable_cause = "unclassified-transport-degradation"
            confidence = 0.68
            affected = [item.get("resource") for item in alarm_context if item.get("resource")]

        probable_causes = [
            {
                "cause-id": "pc-001",
                "cause": probable_cause,
                "confidence": confidence,
                "affected-resources": affected,
            }
        ]
        detail = (
            "The NMA correlated OTU_LOF and ODU_AIS alarms with the working "
            "path topology and identified a probable line failure between "
            "NE2 and NE3."
        )
        protection_path = topology_context.get("protection-path", [])
        resolve_advice = (
            f"Switch service {service_id} to the protection path "
            f"{'-'.join(protection_path)}, then verify service recovery."
        )
        incident = self.controller.a2c_update_incident_analysis(
            incident_no,
            probable_causes,
            detail,
            resolve_advice,
        )
        step2_observation = (
            "The NMA correlated controller alarm, service, and topology "
            "responses and identified a probable working-path line failure."
        )
        self._complete_step(task_id, "step-2", step2_observation)
        self._notify_step_completed(task_id, "step-2", step2_observation)
        await self._demo_pause(0.80)

        self._set_task_state(task_id, "PLANNING")
        self._save()
        self._run_step(task_id, "step-3")
        await self._demo_pause(1.15)
        step3_observation = (
            f"The NMA selected the available protection path for {service_id} "
            "and generated a recovery and verification plan."
        )
        self._complete_step(task_id, "step-3", step3_observation)
        task = self.state["tasks"][task_id]
        task["result"] = {
            "summary": (
                "The incident has been analyzed. Probable cause information has "
                "been identified, and an incident resolution action is awaiting confirmation."
            ),
            "affected-resources": [
                f"incident-{incident_no}",
                service_id,
                "NE2",
                "NE3",
                *affected,
            ],
            "output-data": {
                "incident-no": incident_no,
                "status": incident["status"],
                "ack-status": incident["ack-status"],
                "probable-cause": probable_cause,
                "protection-path": protection_path,
                "next-action": "confirmation-required",
            },
        }
        self._notify(
            task_id,
            "plan-generated",
            {
                "plan-generated": {
                    "step-count": 4,
                    "estimated-duration": 300,
                }
            },
        )
        self._save()
        # Leave the generated plan visible before opening the confirmation card.
        await self._demo_pause(1.10)

        confirmation_id = _id("conf")
        context = deepcopy(incident)
        context["resolve-advice"] = resolve_advice
        confirmation = {
            "confirmation-id": confirmation_id,
            "task-id": task_id,
            "type": "EXECUTION",
            "priority": 9,
            "timeout-seconds": 600,
            "context-schema": INCIDENT_SCHEMA,
            "context": context,
            "allowed-actions": ["approve", "reject", "escalate-to-human"],
            "status": "pending",
            "resolution": {},
        }
        with self.lock:
            self.state["confirmations"][confirmation_id] = confirmation
            self.state["internal"][task_id]["confirmation-id"] = confirmation_id
            self._set_task_state(task_id, "AWAITING_CONFIRMATION")
            self._notify(
                task_id,
                "confirmation-required",
                {
                    "confirmation-required": {
                        "confirmation-id": confirmation_id,
                        "confirmation-type": "EXECUTION",
                        "priority": 9,
                        "timeout-seconds": 600,
                        "context-schema": INCIDENT_SCHEMA,
                        "summary": (
                            f"Switch service {service_id} to the protection path "
                            "to bypass the affected working-path resources."
                        ),
                        "allowed-actions": ["approve", "reject", "escalate-to-human"],
                    }
                },
            )
            self._save()

    async def _prepare_service_creation_task(self, task_id: str) -> None:
        intent = self._intent_for_task(task_id)
        constraints = self._structured_constraints(intent)
        source = constraints.get("source", "NE1")
        destination = constraints.get("destination", "NE6")
        target = f"{source}->{destination}"
        self._replace_plan(
            task_id,
            [
                {
                    "step-id": "step-1",
                    "action": "validate-service-intent",
                    "target": target,
                    "status": "running",
                },
                {
                    "step-id": "step-2",
                    "action": "calculate-service-path",
                    "target": target,
                    "status": "pending",
                },
                {
                    "step-id": "step-3",
                    "action": "request-confirmation-before-service-creation",
                    "target": target,
                    "status": "pending",
                },
            ],
        )
        await self._demo_pause(0.90)
        step1_observation = "Required service parameters were validated."
        self._complete_step(task_id, "step-1", step1_observation)
        self._notify_step_completed(task_id, "step-1", step1_observation)

        self._set_task_state(task_id, "PLANNING")
        self._save()
        self._run_step(task_id, "step-2")
        await self._demo_pause(0.70)
        path_result = self.controller.a2c_calculate_path(source, destination)
        await self._demo_pause(0.65)
        with self.lock:
            self.state["internal"][task_id]["calculated-path"] = deepcopy(path_result)
            self._save()
        step2_observation = (
            "The NMA invoked the controller calculate-path function and "
            f"received {'-'.join(path_result['path'])}."
        )
        self._complete_step(task_id, "step-2", step2_observation)
        self._notify_step_completed(task_id, "step-2", step2_observation)
        await self._demo_pause(0.70)

        self._notify(
            task_id,
            "plan-generated",
            {"plan-generated": {"step-count": 3, "estimated-duration": 180}},
        )
        self._save()
        await self._demo_pause(1.00)

        confirmation_id = _id("conf")
        confirmation_context = deepcopy(constraints)
        confirmation_context["calculated-path"] = path_result["path"]
        confirmation = {
            "confirmation-id": confirmation_id,
            "task-id": task_id,
            "type": "EXECUTION",
            "priority": int((intent.get("structured") or {}).get("priority", 5)),
            "timeout-seconds": 600,
            "context-schema": "urn:demo:otn-service-intent",
            "context": confirmation_context,
            "allowed-actions": [
                "approve",
                "reject",
                "modify-and-approve",
                "escalate-to-human",
            ],
            "status": "pending",
            "resolution": {},
        }
        with self.lock:
            self.state["confirmations"][confirmation_id] = confirmation
            self.state["internal"][task_id]["confirmation-id"] = confirmation_id
            self._set_task_state(task_id, "AWAITING_CONFIRMATION")
            self._notify(
                task_id,
                "confirmation-required",
                {
                    "confirmation-required": {
                        "confirmation-id": confirmation_id,
                        "confirmation-type": "EXECUTION",
                        "priority": confirmation["priority"],
                        "timeout-seconds": 600,
                        "context-schema": confirmation["context-schema"],
                        "summary": (
                            f"Create {constraints.get('service-type', 'EPL')} service "
                            f"from {source} to {destination}."
                        ),
                        "allowed-actions": confirmation["allowed-actions"],
                    }
                },
            )
            self._save()

    async def _run_query_task(self, task_id: str) -> None:
        self._set_task_state(task_id, "PLANNING")
        self._replace_plan(
            task_id,
            [
                {
                    "step-id": "step-1",
                    "action": "query-controller-state",
                    "target": "transport-services",
                    "status": "running",
                }
            ],
        )
        await self._demo_pause(1.00)
        services = self.controller.a2c_list_services()
        await self._demo_pause(0.55)
        self._complete_step(
            task_id,
            "step-1",
            f"The NMA invoked the controller list-services function and received {len(services)} services.",
        )
        with self.lock:
            task = self.state["tasks"][task_id]
            task["result"] = {
                "summary": f"Found {len(services)} transport services.",
                "affected-resources": [item["service-id"] for item in services],
                "output-data": {"services": services},
            }
            self._set_task_state(task_id, "COMPLETED")
            self._notify(
                task_id,
                "task-completed",
                {
                    "task-completed": {
                        "summary": task["result"]["summary"],
                        "affected-resources": task["result"]["affected-resources"],
                    }
                },
            )
            self._save()

    async def _execute_confirmed_task(self, task_id: str) -> None:
        try:
            await self._demo_pause(0.85)
            scenario = self.state["internal"][task_id]["scenario"]
            params = self.state["internal"][task_id].get("execution-params") or {}
            task = self.state["tasks"][task_id]
            confirmation_step = self._confirmation_step_id(task)
            if confirmation_step:
                self._complete_step(
                    task_id,
                    confirmation_step,
                    "The A2U client approved execution.",
                )

            if scenario == "incident":
                incident = self._incident_constraints(self._intent_for_task(task_id))
                incident_no = int(incident.get("incident-no", 56433218))
                service_id = (incident.get("service-instance") or ["svc-1001"])[0]
                step = {
                    "step-id": "step-5",
                    "action": "execute-incident-resolution",
                    "target": f"incident-{incident_no}",
                    "status": "running",
                    "started-at": utc_now(),
                }
                task["plan"].append(step)
                self._save()
                execution = self.controller.a2c_switch_to_protection(incident_no, params)
                await self._demo_pause(0.95)
                verification = self.controller.a2c_verify_service(service_id)
                await self._demo_pause(0.85)
                self._complete_step(
                    task_id,
                    "step-5",
                    (
                        "The NMA invoked controller switch-to-protection and "
                        "verify-service functions; service verification passed."
                    ),
                )
                task["result"] = {
                    "summary": (
                        f"Incident {incident_no} has been resolved and OTN service "
                        f"{service_id} has been restored. The incident status is cleared."
                    ),
                    "affected-resources": [
                        f"incident-{incident_no}",
                        service_id,
                        "NE2",
                        "NE3",
                        "NE2/OTU-1",
                        "NE3/ODU-1",
                    ],
                    "output-data": {
                        **execution,
                        "verification": verification,
                    },
                }
                self._notify(
                    task_id,
                    "step-completed",
                    {
                        "step-completed": {
                            "step-id": "step-5",
                            "observation": (
                                "The controller executed the protection switch and "
                                "the NMA verified that the affected service is up."
                            ),
                        }
                    },
                )
            else:
                constraints = self._structured_constraints(self._intent_for_task(task_id))
                constraints.update(params)
                step = {
                    "step-id": "step-4",
                    "action": "create-service-through-controller",
                    "target": (
                        f"{constraints.get('source', 'NE1')}->"
                        f"{constraints.get('destination', 'NE6')}"
                    ),
                    "status": "running",
                    "started-at": utc_now(),
                }
                task["plan"].append(step)
                self._save()
                service = self.controller.a2c_create_service(constraints)
                await self._demo_pause(1.20)
                self._complete_step(
                    task_id,
                    "step-4",
                    f"Service {service['service-id']} was created by the domain controller.",
                )
                task["result"] = {
                    "summary": f"Transport service {service['service-id']} was created.",
                    "affected-resources": [service["service-id"]],
                    "output-data": service,
                }
                self._notify(
                    task_id,
                    "step-completed",
                    {
                        "step-completed": {
                            "step-id": "step-4",
                            "observation": task["result"]["summary"],
                        }
                    },
                )

            await self._demo_pause(0.75)
            with self.lock:
                self._set_task_state(task_id, "COMPLETED")
                self._notify(
                    task_id,
                    "task-completed",
                    {
                        "task-completed": {
                            "summary": task["result"]["summary"],
                            "affected-resources": task["result"]["affected-resources"],
                        }
                    },
                )
                self._save()
        except RuntimeError as exc:
            if str(exc) == "protection-resource-unavailable":
                self._fail_task(
                    task_id,
                    "A2U-INCIDENT-RESOLVE-001",
                    "The requested incident resolution action cannot be completed "
                    "because the protection resource is unavailable.",
                    details={
                        "incident-resolve-error-info": {
                            "incident-no": 56433218,
                            "reason": "resource-unavailable",
                            "description": (
                                "The protection path required to bypass the affected "
                                "working path is unavailable."
                            ),
                        }
                    },
                )
            else:
                self._fail_task(task_id, "A2U-EXECUTION-001", str(exc))
        except Exception as exc:
            self._fail_task(task_id, "A2U-EXECUTION-002", str(exc))

    def _fail_task(
        self,
        task_id: str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self.lock:
            task = self.state["tasks"].get(task_id)
            if not task:
                return
            failed_step = next((x for x in reversed(task["plan"]) if x["status"] == "running"), None)
            if failed_step:
                failed_step["status"] = "failed"
                failed_step["observation"] = message
                failed_step["completed-at"] = utc_now()
            task["result"] = {
                "summary": message,
                "affected-resources": self._affected_resources(task_id),
                "output-data": {
                    "error-type": "unprocessable-content",
                    "error-code": code,
                    "error-message": message,
                    "retryable": False,
                    "target": "resolve-confirmation.action",
                    **({"details": details} if details else {}),
                },
            }
            self._set_task_state(task_id, "FAILED")
            payload = {"reason": message}
            if failed_step:
                payload["failed-step-id"] = failed_step["step-id"]
            self._notify(task_id, "task-failed", {"task-failed": payload})
            self._save()

    def _notify(self, task_id: str, notification_type: str, payload: dict[str, Any]) -> None:
        task = self.state["tasks"][task_id]
        sequence = self.state["next-notification-sequence"]
        self.state["next-notification-sequence"] += 1
        self.state["notifications"].append(
            {
                "_sequence": sequence,
                "task-id": task_id,
                "intent-id": task["parent-intent-id"],
                "notification-type": notification_type,
                "time": utc_now(),
                "payload": deepcopy(payload),
            }
        )

    def _set_task_state(self, task_id: str, state: str) -> None:
        if state not in TASK_STATES:
            raise ValueError(f"Invalid task state: {state}")
        task = self.state["tasks"][task_id]
        task["state"] = state
        task["updated-at"] = utc_now()
        intent = self.state["intents"].get(task["parent-intent-id"])
        if intent:
            intent["state"] = state

    def _replace_plan(self, task_id: str, steps: list[dict[str, Any]]) -> None:
        with self.lock:
            normalized = []
            for step in steps:
                item = deepcopy(step)
                if item["status"] == "running":
                    item["started-at"] = utc_now()
                normalized.append(item)
            self.state["tasks"][task_id]["plan"] = normalized
            self.state["tasks"][task_id]["updated-at"] = utc_now()
            self._save()

    def _run_step(self, task_id: str, step_id: str) -> None:
        with self.lock:
            step = self._step(task_id, step_id)
            step["status"] = "running"
            step["started-at"] = utc_now()
            self.state["tasks"][task_id]["updated-at"] = utc_now()
            self._save()

    def _complete_step(self, task_id: str, step_id: str, observation: str) -> None:
        with self.lock:
            step = self._step(task_id, step_id)
            step["status"] = "completed"
            step["observation"] = observation
            step.setdefault("started-at", utc_now())
            step["completed-at"] = utc_now()
            self.state["tasks"][task_id]["updated-at"] = utc_now()
            self._save()

    def _step(self, task_id: str, step_id: str) -> dict[str, Any]:
        task = self.state["tasks"][task_id]
        step = next((x for x in task["plan"] if x["step-id"] == step_id), None)
        if not step:
            raise KeyError(f"Plan step {step_id} not found")
        return step

    def _confirmation_step_id(self, task: dict[str, Any]) -> str | None:
        for step in task.get("plan", []):
            if "confirmation" in step.get("action", ""):
                return step["step-id"]
        return None

    def _classify(self, intent: dict[str, Any]) -> str:
        if intent["mode"] == "structured":
            structured = intent["structured"]
            constraints = structured.get("constraints") or {}
            schema = structured.get("constraints-schema", "")
            if (
                structured.get("type") in {"DIAGNOSE", "REMEDIATE", "ASSURE"}
                or schema == INCIDENT_SCHEMA
                or "incident-no" in constraints
            ):
                return "incident"
            if structured.get("type") == "CREATE":
                return "service-create"
            return "query"

        text = intent["natural-language"]["text"].lower()
        if any(
            word in text
            for word in [
                "incident",
                "degradation",
                "alarm",
                "root cause",
                "fault",
                "restore",
                "recovery",
            ]
        ):
            return "incident"
        if any(word in text for word in ["create", "provision", "set up", "setup"]):
            return "service-create"
        return "query"

    def _intent_for_task(self, task_id: str) -> dict[str, Any]:
        task = self.state["tasks"][task_id]
        return self.state["intents"][task["parent-intent-id"]]

    def _structured_constraints(self, intent: dict[str, Any]) -> dict[str, Any]:
        if intent["mode"] == "structured":
            return deepcopy((intent.get("structured") or {}).get("constraints") or {})
        text = intent["natural-language"]["text"]
        nodes = re.findall(r"NE[1-6]", text.upper())
        bandwidth = re.search(r"(\d+)\s*(?:M|MBPS)", text.upper())
        service_type = next(
            (x for x in ["EVPL", "EPL", "ODU", "SDH"] if x in text.upper()),
            "EPL",
        )
        return {
            "service-type": service_type,
            "source": nodes[0] if len(nodes) > 0 else "NE1",
            "destination": nodes[1] if len(nodes) > 1 else "NE6",
            "bandwidth": int(bandwidth.group(1)) if bandwidth else 100,
        }

    def _incident_constraints(self, intent: dict[str, Any]) -> dict[str, Any]:
        if intent["mode"] == "structured":
            constraints = deepcopy((intent.get("structured") or {}).get("constraints") or {})
            constraints.setdefault("incident-no", 56433218)
            constraints.setdefault("service-instance", ["svc-1001"])
            return constraints
        incident = self.controller.get_incident(56433218)
        return deepcopy(incident or {"incident-no": 56433218, "service-instance": ["svc-1001"]})

    def _affected_resources(self, task_id: str) -> list[str]:
        task = self.state["tasks"][task_id]
        resources = (task.get("result") or {}).get("affected-resources")
        if resources:
            return deepcopy(resources)
        scenario = self.state["internal"].get(task_id, {}).get("scenario")
        return ["incident-56433218", "svc-1001"] if scenario == "incident" else []

    def _metadata(self, request: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key in ("request-id", "correlation-id", "tenant-id"):
            if request.get(key) is not None:
                result[key] = request[key]
        return result

    def _sorted_values(self, key: str, timestamp_key: str) -> list[dict[str, Any]]:
        with self.lock:
            values = [deepcopy(x) for x in self.state[key].values()]
        return sorted(values, key=lambda x: str(x.get(timestamp_key, "")), reverse=True)

    def _not_found(self, object_type: str, object_id: str) -> None:
        raise A2UException(
            "not-found",
            f"A2U-{object_type.upper()}-404",
            f"{object_type.capitalize()} {object_id} was not found.",
            status_code=404,
            target=f"a2u.{object_type}",
        )

    def _empty_state(self) -> dict[str, Any]:
        return {
            "intents": {},
            "tasks": {},
            "confirmations": {},
            "notifications": [],
            "next-notification-sequence": 1,
            "internal": {},
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            state = self._empty_state()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            return state
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            for key, default in self._empty_state().items():
                state.setdefault(key, deepcopy(default))
            return state
        except (OSError, json.JSONDecodeError):
            return self._empty_state()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


agent = A2UAgent(controller, Path(__file__).resolve().parent / "data")
