# Framework and YANG Data Model for the NMA A2U Interface

This repository contains the Internet-Draft and YANG data model for the **Agent-to-User (A2U) interface** of a **Network Management Agent (NMA)**.

The current draft is:

```text
draft-zhao-nmop-nma-a2u-interface-00
Framework and YANG Data Model for the NMA A2U Interface
```

This work is intended for discussion in the IETF Network Management Operations (NMOP) context.

## Overview

A Network Management Agent (NMA) is an autonomous or semi-autonomous management entity that can interpret management goals, plan management actions, invoke tools and interfaces, monitor execution, and report results.

The A2U interface is a user-facing interface through which a **non-agent upper-layer system or user** interacts with an NMA. Examples of A2U clients include:

* OSS/BSS systems
* Orchestrators
* Management portals
* Human-facing applications
* Automation systems
* ...

The A2U interface supports:

* NMA capability discovery
* Natural-language or structured intent submission
* Task lifecycle management
* Execution plan exposure
* Human-in-the-loop confirmation
* Event notification
* Consistent error reporting

The YANG data model defined in this repository describes protocol-binding-independent information objects and message structures used by the A2U interface.

## Interface Positioning

A2U is intended for client/server-style interaction between a **non-agent upper-layer system or user** and an NMA.

A2U is **not** used for communication between an upper-layer NMA and a lower-layer NMA. Such communication is Agent-to-Agent communication and is expected to use A2A or other Agent-to-Agent interfaces.

In other words:

```text
Non-agent upper-layer system / user  ---- A2U ---->  NMA
Upper-layer NMA / Agent              ---- A2A ---->  Lower-layer NMA / Agent
```

The A2U interface is distinct from:

* **A2A**: Agent-to-Agent interface between agents or NMAs
* **A2C**: Agent-to-Controller interface between the NMA and controller functions
* **A2N**: Agent-to-Network interface between the NMA and network resources

## Repository Contents

```text
.
├── README.md
├── draft-zhao-nmop-nma-a2u-interface-00.xml
├── draft-zhao-nmop-nma-a2u-interface-00.txt
└── yang/
    └── ietf-nma-a2u@2026-06-30.yang
```

### Files

| File                                       | Description                                     |
| ------------------------------------------ | ----------------------------------------------- |
| `draft-zhao-nmop-nma-a2u-interface-00.xml` | xml2rfc source of the Internet-Draft            |
| `draft-zhao-nmop-nma-a2u-interface-00.txt` | Text rendering of the Internet-Draft            |
| `yang/ietf-nma-a2u@2026-06-30.yang`        | Standalone YANG module extracted from the draft |
| `README.md`                                | Repository overview                             |

## Draft Scope

The draft defines:

* A2U interface positioning
* A2U reference framework
* A2U interaction principles
* A2U information model
* A single YANG data model for A2U objects
* A non-normative HTTP-based protocol binding example

The draft does **not** define:

* A mandatory new transport protocol
* Agent-to-Agent communication
* NMA-to-NMA negotiation or delegation
* Domain-specific service models
* LLM implementation details
* Detailed A2C or A2N protocol mechanisms
* Internal NMA implementation details

## A2U Information Model

The A2U information model contains five core components.

### Agent Capabilities

The `agent-capabilities` object, also called the Agent Card, describes the NMA and its exposed skills. It includes:

* Agent identifier
* Version
* Skill list
* Input schema for each skill
* Confirmation requirement
* Maximum autonomy level
* Optional tags for skill classification and discovery
* Endpoint list
* Global policies

### Intent

The `intent` object represents a user or system goal. It may be expressed as:

* Natural-language input
* Structured input

The structured `intent-type` identifies the high-level operation category. The current model includes:

* `CREATE`
* `DELETE`
* `MODIFY`
* `QUERY`
* `REPORT`
* `DIAGNOSE`
* `REMEDIATE`
* `OPTIMIZE`
* `ASSURE`

Domain-specific details, such as service assurance objectives, fault symptoms, recovery constraints, or optimization policies, are carried in the `constraints` field.

### Task

The `task` object represents the lifecycle of an accepted intent. It includes:

* Task identifier
* Parent intent identifier
* State
* Creation and update timestamps
* Execution plan
* Result
* Audit log

### Confirmation

The `confirmation` object represents a pending or resolved decision point. It is used when a task requires explicit approval, rejection, modification, or escalation.

### Event

The `event` object represents task-related notifications. Events may be delivered by streaming, polling, or other binding-specific mechanisms.

## YANG Data Model

The draft defines one YANG module:

```text
ietf-nma-a2u
```

The module uses the YANG data structure extension defined in RFC 8791. The `sx:structure` statements describe abstract information objects and message bodies exchanged across A2U. They are not configuration datastore nodes.

Top-level A2U structures use the `nma-a2u-` prefix, for example:

```text
nma-a2u-agent-capabilities
nma-a2u-intent
nma-a2u-task
nma-a2u-confirmation
nma-a2u-event
nma-a2u-submit-intent-request
nma-a2u-submit-intent-response
nma-a2u-confirmation-resolution-request
nma-a2u-confirmation-resolution-response
nma-a2u-abort-task-request
nma-a2u-abort-task-response
nma-a2u-error
```

Reusable YANG groupings use the `-object` suffix, such as:

```text
agent-capabilities-object
intent-object
task-object
confirmation-object
event-object
```

This distinguishes reusable object templates from instantiated containers and top-level structures.

## Example HTTP-Based Binding

The draft provides a non-normative HTTP-based binding example. In this example, A2U resources use the `/nma/a2u/*` URI space.

Example operations include:

| Operation               | Example URI                           | Message Structure                                                                      |
| ----------------------- | ------------------------------------- | -------------------------------------------------------------------------------------- |
| Capability discovery    | `GET /nma/a2u/agent-capabilities`     | `nma-a2u-agent-capabilities`                                                           |
| Intent submission       | `POST /nma/a2u/intent`                | `nma-a2u-submit-intent-request` / `nma-a2u-submit-intent-response`                     |
| Task retrieval          | `GET /nma/a2u/tasks/{task-id}`        | `nma-a2u-task`                                                                         |
| Task listing            | `GET /nma/a2u/tasks`                  | `nma-a2u-task-list-response`                                                           |
| Event subscription      | `GET /nma/a2u/tasks/{task-id}/events` | stream of `nma-a2u-event`                                                              |
| Confirmation resolution | `POST /nma/a2u/confirm`               | `nma-a2u-confirmation-resolution-request` / `nma-a2u-confirmation-resolution-response` |
| Task abort              | `POST /nma/a2u/tasks/{task-id}/abort` | `nma-a2u-abort-task-request` / `nma-a2u-abort-task-response`                           |

The HTTP binding is only an example. The A2U YANG model itself is protocol-binding independent.

## Example Scenario

The draft includes a non-normative JSON example for an OTN fault handling and service assurance scenario.

In the example:

1. An OSS detects degradation of an OTN service.
2. The OSS invokes the NMA through A2U.
3. The NMA analyzes alarms and performance data.
4. The NMA correlates topology and service impact.
5. The NMA identifies the likely root cause.
6. The NMA generates a recovery plan.
7. The NMA requests confirmation before executing the recovery action.
8. The NMA reports task progress through events.

This scenario illustrates why A2U is useful for NMA-based intelligent operations, where the interaction is not simply a CRUD configuration operation, but a goal-oriented management process involving analysis, planning, confirmation, and result reporting.

## Build the Draft

The XML source can be rendered using `xml2rfc`.

```sh
xml2rfc draft-zhao-nmop-nma-a2u-interface-00.xml --text
xml2rfc draft-zhao-nmop-nma-a2u-interface-00.xml --html
```

To generate both text and HTML:

```sh
xml2rfc draft-zhao-nmop-nma-a2u-interface-00.xml --text --html
```

The rendered text version is also included in the repository:

```text
draft-zhao-nmop-nma-a2u-interface-00.txt
```

## Validate the YANG Module

The standalone YANG module is located at:

```text
yang/ietf-nma-a2u@2026-06-30.yang
```

It can be checked using `pyang`:

```sh
pyang yang/ietf-nma-a2u@2026-06-30.yang
```

For stricter validation:

```sh
pyang --lint yang/ietf-nma-a2u@2026-06-30.yang
```

Depending on the local `pyang` environment, additional module search paths may be required for imported IETF YANG modules.

## Relationship with Other Work

This draft is related to the broader work on the Network Management Agent (NMA) architecture.

The NMA architecture draft describes the overall NMA concept and architectural relationships. This A2U draft focuses specifically on the user-facing interface through which non-agent upper-layer systems and users consume NMA capabilities.

## Current Status

This repository contains an individual Internet-Draft. It is work in progress and does not represent an IETF standard.

Feedback, issues, and pull requests are welcome.

## Author

**Xing Zhao**
China Academy of Information and Communication Technology
Email: [zhaoxing@caict.ac.cn](mailto:zhaoxing@caict.ac.cn)

## License

This repository contains material intended for contribution to the IETF. The Internet-Draft is subject to the IETF Trust Legal Provisions.
