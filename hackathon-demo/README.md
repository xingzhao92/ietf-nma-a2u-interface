# NMA A2U Hackathon Demo

This project demonstrates the Network Management Agent (NMA) concept and the
A2U YANG model described in:

- `draft-zhao-nmop-network-management-agent`
- `draft-zhao-nmop-nma-a2u-yang-00`

The main scenario is an OTN network incident:

1. The OSS/BSS simulator discovers NMA capabilities.
2. It invokes the `submit-intent` RPC using natural-language or structured input.
3. The NMA creates an intent and a task, perceives the incident, analyzes alarms
   and topology, and generates an execution plan.
4. The NMA sends `plan-generated` and `confirmation-required` YANG notifications.
5. The OSS retrieves the full confirmation object and invokes the
   `resolve-confirmation` RPC.
6. The NMA invokes the controller, switches `svc-1001` to its protection path,
   and sends `step-completed` and `task-completed` notifications.
7. The OSS may retrieve the final task object and result.

The original service-creation scenario is retained as a second demo.

## OSS demonstration UI

The OSS/BSS page gives the `submit-intent` RPC the largest workspace and exposes
all nine `intent-type` enumeration values defined by the draft: `CREATE`,
`DELETE`, `MODIFY`, `QUERY`, `REPORT`, `DIAGNOSE`, `REMEDIATE`, `OPTIMIZE`, and
`ASSURE`. The deterministic live workflows focus on incident diagnosis/remediation,
service creation, and query; the remaining values are exposed for YANG schema
coverage.

The page also exposes request/correlation/tenant metadata, provides one-click GET
access to the created intent, task, and confirmation operational-state objects,
keeps a history of received A2U YANG notifications, and dynamically presents the
confirmation actions allowed by each confirmation object, including
`modify-and-approve` when supported.

## Run

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open:

- Controller and embedded NMA: `http://127.0.0.1:8000/`
- OSS/BSS A2U client: `http://127.0.0.1:8000/oss`
- OpenAPI: `http://127.0.0.1:8000/docs`

The demo is deterministic and does not require an external LLM or Internet
connection.


## Demonstration pacing

The live server deliberately pauses between intent acceptance, context acquisition,
incident analysis, plan generation, confirmation, controller execution, and final
feedback. Intermediate plan steps are reported with `step-completed` notifications,
so the OSS can refresh the task without periodic polling and the audience can observe
the workflow. The default base interval is 1.25 seconds and can be changed before
starting the server:

```bash
# Faster
A2U_DEMO_DELAY_SECONDS=0.7 python app.py

# Slower
A2U_DEMO_DELAY_SECONDS=1.8 python app.py
```

On Windows PowerShell, set `$env:A2U_DEMO_DELAY_SECONDS="1.8"` before running
`python app.py`. Tests use an explicit short delay and are not slowed down.

## A2U paths implemented

| Purpose | Method and path |
|---|---|
| Capability discovery | `GET /restconf/data/ietf-nma-a2u:a2u/agent-capabilities` |
| Intent state | `GET /restconf/data/ietf-nma-a2u:a2u/intent={intent-id}` |
| Task state | `GET /restconf/data/ietf-nma-a2u:a2u/task={task-id}` |
| Confirmation state | `GET /restconf/data/ietf-nma-a2u:a2u/confirmation={confirmation-id}` |
| Submit intent | `POST /restconf/operations/ietf-nma-a2u:submit-intent` |
| Resolve confirmation | `POST /restconf/operations/ietf-nma-a2u:resolve-confirmation` |
| Abort task | `POST /restconf/operations/ietf-nma-a2u:abort-task` |
| Establish notification subscription | `POST /restconf/operations/ietf-subscribed-notifications:establish-subscription` |
| Activate an accepted RESTCONF dynamic subscription | `GET /restconf/subscriptions/{id}` (one long-lived SSE connection) |

Notification subscription and delivery reuse RFC 8639 and RFC 8650. The establish-subscription RPC returns an id and URI; one long-lived SSE connection to that URI activates the subscription, after which the publisher pushes RFC 8040-encoded YANG notification messages. A2U defines the a2u-task-notification content and does not define a separate notification transport.

## Model alignment

The exposed operational-state objects contain only fields from the draft's
`agent-capabilities`, `intent`, `task`, and `confirmation` objects. The RPC
messages use the draft metadata and input/output fields. Incident information is
carried in `constraints` and confirmation `context` using an
`ietf-incident` schema URI; A2U does not redefine the incident model.

The `/api/demo/*` endpoints and controller JSON files are implementation support
for the Hackathon UI and are not A2U interfaces.

## Smoke test

```bash
python tests/smoke_test.py
```


## OpenAPI view

`/docs` intentionally shows only the A2U operational-state resources and the three A2U RPCs. Each RPC has a pre-populated request-body example. The submit-intent operation provides separate selectable examples for natural-language and structured intents. Subscription transport and `/api/demo/*` support endpoints are hidden because they are reused transport or implementation support, not nodes in the `ietf-nma-a2u` module.

## Task refresh behavior

The OSS does not periodically poll the task object. It performs an initial GET after intent acceptance, refreshes the task after each publisher-pushed notification, refreshes after confirmation resolution, and supports an explicit manual GET button.

## A2C demonstration

The Domain Controller page records the NMA-to-controller function sequence. The incident scenario invokes get-incident, get-service, get-alarms, get-topology, update-incident-analysis, switch-to-protection, and verify-service. The NMA performs correlation, root-cause analysis, decision, and plan generation; the controller supplies data and execution functions.
