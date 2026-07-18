import asyncio
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import A2UAgent, INTENT_TYPES
from controller import VirtualController


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        controller = VirtualController(tmp)
        controller.reset()
        agent = A2UAgent(controller, tmp, demo_delay=0.01)

        request = {
            "request-id": "req-test-1",
            "correlation-id": "corr-test-1",
            "tenant-id": "tenant-1",
            "intent": {
                "intent-id": "intent-test-1",
                "mode": "structured",
                "submitter": {"type": "system", "id": "oss-test"},
                "structured": {
                    "type": "DIAGNOSE",
                    "target-resource": "incident-56433218",
                    "constraints-schema": "urn:ietf:params:xml:ns:yang:ietf-incident",
                    "constraints": {
                        "incident-no": 56433218,
                        "service-instance": ["svc-1001"],
                        "domain": "otn",
                        "status": "raised",
                    },
                    "priority": 9,
                },
            },
        }
        accepted = await agent.submit_intent(request)
        task_id = accepted["task-id"]
        task = await agent.wait_for_state(task_id, {"AWAITING_CONFIRMATION"})
        assert task["state"] == "AWAITING_CONFIRMATION"
        assert len(task["plan"]) == 4

        notifications = agent.notifications_for_task(task_id)
        types = [x["notification-type"] for x in notifications]
        assert "plan-generated" in types
        assert "confirmation-required" in types

        confirmation = agent.list_confirmations()[0]
        assert confirmation["context-schema"].endswith("ietf-incident")
        resolved = await agent.resolve_confirmation(
            {
                "request-id": "req-test-2",
                "correlation-id": "corr-test-1",
                "tenant-id": "tenant-1",
                "confirmation-id": confirmation["confirmation-id"],
                "action": "approve",
                "resolved-by": "operator-test",
            }
        )
        assert resolved["task-state"] == "EXECUTING"
        task = await agent.wait_for_state(task_id, {"COMPLETED"})
        assert task["state"] == "COMPLETED"
        assert task["result"]["output-data"]["incident-status"] == "cleared"

        service = controller.get_service("svc-1001")
        assert service["active-path"] == "protection"
        assert service["state"] == "up"

        notifications = agent.notifications_for_task(task_id)
        types = [x["notification-type"] for x in notifications]
        assert "step-completed" in types
        assert "task-completed" in types

        expected_types = {
            "CREATE", "DELETE", "MODIFY", "QUERY", "REPORT",
            "DIAGNOSE", "REMEDIATE", "OPTIMIZE", "ASSURE",
        }
        assert INTENT_TYPES == expected_types
        oss_html = (ROOT / "frontend" / "oss.html").read_text(encoding="utf-8")
        for intent_type in expected_types:
            assert f">{intent_type}</option>" in oss_html or f">{intent_type}</option" in oss_html

        service_request = {
            "request-id": "req-test-3",
            "correlation-id": "corr-test-2",
            "tenant-id": "tenant-1",
            "intent": {
                "intent-id": "intent-test-2",
                "mode": "structured",
                "submitter": {"type": "system", "id": "oss-test"},
                "structured": {
                    "type": "CREATE",
                    "target-resource": "transport-service",
                    "constraints-schema": "urn:demo:otn-service-intent",
                    "constraints": {
                        "service-type": "EPL",
                        "source": "NE1",
                        "destination": "NE6",
                        "bandwidth": {"value": 100, "unit": "Mbps"},
                    },
                    "priority": 5,
                },
            },
        }
        accepted = await agent.submit_intent(service_request)
        service_task_id = accepted["task-id"]
        await agent.wait_for_state(service_task_id, {"AWAITING_CONFIRMATION"})
        service_confirmation = next(
            item for item in agent.list_confirmations()
            if item["task-id"] == service_task_id
        )
        assert "modify-and-approve" in service_confirmation["allowed-actions"]
        await agent.resolve_confirmation(
            {
                "request-id": "req-test-4",
                "correlation-id": "corr-test-2",
                "tenant-id": "tenant-1",
                "confirmation-id": service_confirmation["confirmation-id"],
                "action": "modify-and-approve",
                "modified-params-schema": "urn:demo:otn-service-intent",
                "modified-params": {
                    "bandwidth": {"value": 200, "unit": "Mbps"}
                },
                "resolved-by": "operator-test",
            }
        )
        service_task = await agent.wait_for_state(service_task_id, {"COMPLETED"})
        assert service_task["result"]["output-data"]["bandwidth-mbps"] == 200

        print(
            "PASS: incident workflow, full intent-type enum coverage, "
            "operational objects, notifications, and modify-and-approve"
        )


if __name__ == "__main__":
    asyncio.run(main())
