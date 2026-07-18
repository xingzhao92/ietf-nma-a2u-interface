"""Domain controller simulator used by the IETF Hackathon demo.

The controller exposes deterministic internal functions to the embedded NMA.
Those calls are recorded as A2C interactions so the demonstration clearly
separates:
- A2U: OSS/BSS to NMA
- A2C: NMA to controller functions
"""
from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NODES = ["NE1", "NE2", "NE3", "NE4", "NE5", "NE6"]
EDGES = [
    ("NE1", "NE2"),
    ("NE2", "NE3"),
    ("NE3", "NE6"),
    ("NE1", "NE4"),
    ("NE4", "NE5"),
    ("NE5", "NE6"),
    ("NE2", "NE4"),
    ("NE3", "NE5"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def default_services() -> list[dict[str, Any]]:
    return [
        {
            "service-id": "svc-1001",
            "name": "OTN Gold Service 1001",
            "service-type": "ODU",
            "source": "NE1",
            "destination": "NE6",
            "bandwidth-mbps": 10,
            "working-path": ["NE1", "NE2", "NE3", "NE6"],
            "protection-path": ["NE1", "NE4", "NE5", "NE6"],
            "active-path": "working",
            "state": "degraded",
            "protection-available": True,
        },
        {
            "service-id": "svc-2001",
            "name": "Ethernet Private Line 2001",
            "service-type": "EPL",
            "source": "NE2",
            "destination": "NE5",
            "bandwidth-mbps": 100,
            "working-path": ["NE2", "NE3", "NE5"],
            "protection-path": ["NE2", "NE4", "NE5"],
            "active-path": "working",
            "state": "up",
            "protection-available": True,
        },
        {
            "service-id": "svc-3001",
            "name": "OTN Silver Service 3001",
            "service-type": "ODU",
            "source": "NE3",
            "destination": "NE4",
            "bandwidth-mbps": 10,
            "working-path": ["NE3", "NE2", "NE4"],
            "protection-path": [],
            "active-path": "working",
            "state": "up",
            "protection-available": False,
        },
    ]


def default_incidents() -> list[dict[str, Any]]:
    now = utc_now()
    return [
        {
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
            "sources": [
                {"source-id": "NE2/OTU-1", "source-type": "network-element"},
                {"source-id": "NE3/ODU-1", "source-type": "network-element"},
            ],
            "probable-causes": [],
            "probable-events": ["OTU_LOF", "ODU_AIS"],
            "events": [
                {
                    "event-id": "alarm-otu-lof-001",
                    "event-type": "OTU_LOF",
                    "resource": "NE2/OTU-1",
                    "severity": "critical",
                },
                {
                    "event-id": "alarm-odu-ais-001",
                    "event-type": "ODU_AIS",
                    "resource": "NE3/ODU-1",
                    "severity": "major",
                },
            ],
            "detail": (
                "OTN service svc-1001 is degraded. OTU_LOF and ODU_AIS "
                "alarm events were observed on the working path."
            ),
            "resolve-advice": (
                "Diagnose the probable root cause and provide recovery suggestions. "
                "Prefer actions that minimize impact on running services."
            ),
            "occur-time": now,
            "raise-time": now,
            "last-updated": now,
        }
    ]


class JsonFile:
    def __init__(self, path: Path, default_factory):
        self.path = path
        self.default_factory = default_factory
        self.lock = threading.RLock()

    def load(self):
        with self.lock:
            if not self.path.exists():
                value = self.default_factory()
                self.save(value)
                return deepcopy(value)
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                value = self.default_factory()
                self.save(value)
                return deepcopy(value)

    def save(self, value) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(value, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)


class VirtualController:
    def __init__(self, data_dir: str | Path = "data"):
        data_dir = Path(data_dir)
        self.services_file = JsonFile(data_dir / "services.json", default_services)
        self.incidents_file = JsonFile(data_dir / "incidents.json", default_incidents)
        self.actions_file = JsonFile(data_dir / "controller-actions.json", list)
        self.lock = threading.RLock()

    # ------------------------------------------------------------------
    # Controller UI / operational data reads (not A2C calls)
    # ------------------------------------------------------------------
    def reset(self) -> dict[str, Any]:
        with self.lock:
            self.services_file.save(default_services())
            self.incidents_file.save(default_incidents())
            self.actions_file.save([])
            return self.snapshot()

    def topology(self) -> dict[str, Any]:
        return {
            "nodes": [{"id": node, "label": node} for node in NODES],
            "links": [{"id": f"{a}-{b}", "source": a, "target": b} for a, b in EDGES],
        }

    def list_services(self) -> list[dict[str, Any]]:
        return self.services_file.load()

    def get_service(self, service_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.list_services() if item["service-id"] == service_id),
            None,
        )

    def list_incidents(self) -> list[dict[str, Any]]:
        return self.incidents_file.load()

    def get_incident(self, incident_no: int | str) -> dict[str, Any] | None:
        incident_no = int(incident_no)
        return next(
            (
                item
                for item in self.list_incidents()
                if int(item["incident-no"]) == incident_no
            ),
            None,
        )

    def list_actions(self) -> list[dict[str, Any]]:
        return self.actions_file.load()

    def snapshot(self) -> dict[str, Any]:
        return {
            "topology": self.topology(),
            "services": self.list_services(),
            "incidents": self.list_incidents(),
            "controller-actions": self.list_actions(),
        }

    def inject_otn_degradation(self) -> dict[str, Any]:
        """Restore the incident scenario even after a successful previous run."""
        with self.lock:
            services = self.list_services()
            for service in services:
                if service["service-id"] == "svc-1001":
                    service["active-path"] = "working"
                    service["state"] = "degraded"
            self.services_file.save(services)

            incidents = [
                item
                for item in self.list_incidents()
                if int(item["incident-no"]) != 56433218
            ]
            incidents.extend(default_incidents())
            self.incidents_file.save(incidents)
            return deepcopy(self.get_incident(56433218))

    # ------------------------------------------------------------------
    # A2C functions invoked by the embedded NMA
    # ------------------------------------------------------------------
    def a2c_get_incident(self, incident_no: int) -> dict[str, Any]:
        request = {"incident-no": int(incident_no)}
        incident = self.get_incident(incident_no)
        if not incident:
            raise KeyError(f"Incident {incident_no} not found")
        response = deepcopy(incident)
        self._record_a2c(
            "get-incident",
            f"incident-{incident_no}",
            request,
            response,
            "Load structured incident context for NMA awareness.",
        )
        return response

    def a2c_get_service(self, service_id: str) -> dict[str, Any]:
        request = {"service-id": service_id}
        service = self.get_service(service_id)
        if not service:
            raise KeyError(f"Service {service_id} not found")
        response = deepcopy(service)
        self._record_a2c(
            "get-service",
            service_id,
            request,
            response,
            "Read service endpoints, working/protection paths, and state.",
        )
        return response

    def a2c_get_alarms(self, incident_no: int) -> list[dict[str, Any]]:
        request = {"incident-no": int(incident_no), "severity": "major-or-higher"}
        incident = self.get_incident(incident_no)
        if not incident:
            raise KeyError(f"Incident {incident_no} not found")
        alarms = deepcopy(incident.get("events", []))
        self._record_a2c(
            "get-alarms",
            f"incident-{incident_no}",
            request,
            {"alarm-count": len(alarms), "alarms": alarms},
            "Retrieve alarm events used by the NMA for root-cause analysis.",
        )
        return alarms

    def a2c_get_topology(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        if not service:
            raise KeyError(f"Service {service_id} not found")
        request = {"service-id": service_id, "scope": "service-path-context"}
        response = {
            "network-topology": self.topology(),
            "working-path": deepcopy(service["working-path"]),
            "protection-path": deepcopy(service["protection-path"]),
            "protection-available": service["protection-available"],
        }
        self._record_a2c(
            "get-topology",
            service_id,
            request,
            response,
            "Retrieve path topology for alarm/resource correlation and planning.",
        )
        return response

    def a2c_update_incident_analysis(
        self,
        incident_no: int,
        probable_causes: list[dict[str, Any]],
        detail: str,
        resolve_advice: str,
    ) -> dict[str, Any]:
        request = {
            "incident-no": int(incident_no),
            "probable-causes": deepcopy(probable_causes),
            "detail": detail,
            "resolve-advice": resolve_advice,
        }
        with self.lock:
            incidents = self.list_incidents()
            incident = next(
                (
                    item
                    for item in incidents
                    if int(item["incident-no"]) == int(incident_no)
                ),
                None,
            )
            if not incident:
                raise KeyError(f"Incident {incident_no} not found")
            incident["status"] = "updated"
            incident["ack-status"] = "acknowledged"
            incident["probable-causes"] = deepcopy(probable_causes)
            incident["detail"] = detail
            incident["resolve-advice"] = resolve_advice
            incident["last-updated"] = utc_now()
            self.incidents_file.save(incidents)
            response = deepcopy(incident)
        self._record_a2c(
            "update-incident-analysis",
            f"incident-{incident_no}",
            request,
            response,
            "Persist NMA-generated diagnosis and recovery advice.",
        )
        return response

    def a2c_switch_to_protection(
        self,
        incident_no: int,
        modified_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        modified_params = modified_params or {}
        incident = self.get_incident(incident_no)
        if not incident:
            raise KeyError(f"Incident {incident_no} not found")
        service_id = incident["service-instance"][0]
        request = {
            "service-id": service_id,
            "requested-path": modified_params.get("requested-path", "protection"),
            "reason": f"resolve incident {incident_no}",
        }
        with self.lock:
            services = self.list_services()
            service = next(
                (item for item in services if item["service-id"] == service_id),
                None,
            )
            if not service:
                raise KeyError(f"Service {service_id} not found")
            if not service.get("protection-available") or not service.get("protection-path"):
                raise RuntimeError("protection-resource-unavailable")
            if request["requested-path"] != "protection":
                raise RuntimeError("unsupported-requested-path")

            service["active-path"] = "protection"
            service["state"] = "up"
            self.services_file.save(services)

            incidents = self.list_incidents()
            for item in incidents:
                if int(item["incident-no"]) == int(incident_no):
                    item["status"] = "cleared"
                    item["ack-status"] = "acknowledged"
                    item["last-updated"] = utc_now()
                    item["detail"] = (
                        f"Service {service_id} was switched to the protection path."
                    )
            self.incidents_file.save(incidents)
            response = {
                "incident-no": int(incident_no),
                "service-id": service_id,
                "active-path": service["active-path"],
                "route": deepcopy(service["protection-path"]),
                "service-state": service["state"],
                "incident-status": "cleared",
            }
        self._record_a2c(
            "switch-to-protection",
            service_id,
            request,
            response,
            "Execute the NMA-approved recovery action on the domain controller.",
        )
        return response

    def a2c_verify_service(self, service_id: str) -> dict[str, Any]:
        request = {
            "service-id": service_id,
            "checks": ["oper-state", "active-path", "continuity"],
        }
        service = self.get_service(service_id)
        if not service:
            raise KeyError(f"Service {service_id} not found")
        response = {
            "service-id": service_id,
            "oper-state": service["state"],
            "active-path": service["active-path"],
            "continuity-check": "passed" if service["state"] == "up" else "failed",
            "verified": service["state"] == "up",
        }
        self._record_a2c(
            "verify-service",
            service_id,
            request,
            response,
            "Verify the result before the NMA reports task completion.",
        )
        return response

    def a2c_list_services(self) -> list[dict[str, Any]]:
        request = {"scope": "all-transport-services"}
        services = self.list_services()
        self._record_a2c(
            "list-services",
            "transport-services",
            request,
            {"service-count": len(services), "services": deepcopy(services)},
            "Fulfil an NMA query task through a controller data function.",
        )
        return services

    def a2c_calculate_path(self, source: str, destination: str) -> dict[str, Any]:
        request = {"source": source, "destination": destination}
        path = self._shortest_path(source, destination)
        if not path:
            raise RuntimeError("route-unavailable")
        response = {"path": path, "hop-count": len(path) - 1, "feasible": True}
        self._record_a2c(
            "calculate-path",
            f"{source}->{destination}",
            request,
            response,
            "Provide path feasibility input for the NMA service plan.",
        )
        return response

    def a2c_create_service(self, constraints: dict[str, Any]) -> dict[str, Any]:
        request = deepcopy(constraints)
        with self.lock:
            source = constraints.get("source", "NE1")
            destination = constraints.get("destination", "NE6")
            service_type = constraints.get("service-type", "EPL")
            bandwidth = constraints.get("bandwidth", 100)
            if isinstance(bandwidth, dict):
                bandwidth = bandwidth.get("value", 100)
            services = self.list_services()
            sequence = 4000 + len(services) + 1
            service_id = f"svc-{sequence}"
            working = self._shortest_path(source, destination)
            if not working:
                raise RuntimeError("route-unavailable")
            service = {
                "service-id": service_id,
                "name": f"{service_type} Service {sequence}",
                "service-type": service_type,
                "source": source,
                "destination": destination,
                "bandwidth-mbps": int(bandwidth),
                "working-path": working,
                "protection-path": [],
                "active-path": "working",
                "state": "up",
                "protection-available": False,
            }
            services.append(service)
            self.services_file.save(services)
            response = deepcopy(service)
        self._record_a2c(
            "create-service",
            service_id,
            request,
            response,
            "Execute the approved service-creation task.",
        )
        return response

    # Compatibility methods retained for external code using the old class API.
    def diagnose_incident(self, incident_no: int) -> dict[str, Any]:
        probable_causes = [
            {
                "cause-id": "pc-001",
                "cause": "fiber-or-line-interface-failure",
                "confidence": 0.96,
                "affected-resources": ["NE2/OTU-1", "NE3/ODU-1"],
            }
        ]
        return self.a2c_update_incident_analysis(
            incident_no,
            probable_causes,
            (
                "Alarm and topology correlation indicates a working-path line "
                "failure between NE2 and NE3."
            ),
            (
                "Switch service svc-1001 to the protection path "
                "NE1-NE4-NE5-NE6, then verify service recovery."
            ),
        )

    def switch_to_protection(
        self,
        incident_no: int,
        modified_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.a2c_switch_to_protection(incident_no, modified_params)

    def create_service(self, constraints: dict[str, Any]) -> dict[str, Any]:
        return self.a2c_create_service(constraints)

    def _shortest_path(self, source: str, destination: str) -> list[str]:
        if source not in NODES or destination not in NODES:
            return []
        if source == destination:
            return [source]
        graph = {node: [] for node in NODES}
        for left, right in EDGES:
            graph[left].append(right)
            graph[right].append(left)
        queue: list[tuple[str, list[str]]] = [(source, [source])]
        visited = {source}
        while queue:
            node, path = queue.pop(0)
            for neighbor in sorted(graph[node]):
                if neighbor == destination:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def _record_a2c(
        self,
        operation: str,
        target: str,
        request: dict[str, Any],
        response: Any,
        purpose: str,
    ) -> None:
        actions = self.list_actions()
        actions.append(
            {
                "call-id": f"a2c-{uuid.uuid4().hex[:8]}",
                "time": utc_now(),
                "interface": "A2C",
                "operation": operation,
                "target": target,
                "purpose": purpose,
                "request": deepcopy(request),
                "response": deepcopy(response),
            }
        )
        self.actions_file.save(actions[-200:])


controller = VirtualController(Path(__file__).resolve().parent / "data")
