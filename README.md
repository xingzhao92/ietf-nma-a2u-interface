# Framework and YANG Data Model for NMA A2U Interface

[![IETF Draft](https://img.shields.io/badge/IETF-Draft-yellow)](https://datatracker.ietf.org/doc/draft-zhao-nmop-nma-a2u-framework/)
[![License](https://img.shields.io/badge/License-BSD%202--Clause-blue.svg)](LICENSE)

This repository contains the IETF Internet-Draft for the **Network Management Agent (NMA) A2U (Agent-to-User) Interface** framework and YANG data models.

## Overview

The A2U interface defines a standardized northbound interface for NMAs to expose capabilities to upper-layer systems (OSS/BSS). It includes:

- **Architecture framework** with dual-plane design (`/restconf/*` vs `/nma/*`)
- **Unified information model** with 6 YANG modules covering capabilities, intents, tasks, confirmations, and events
- **7 HTTP interface primitives** supporting dual-modal input (natural language + structured)
- **SSE streaming** for real-time event notification
- **Human-in-the-loop confirmation** mechanism for safe autonomous operations

## Interface Positioning: A2U vs A2A

This section clarifies the precise scope of the A2U interface and its relationship with Agent-to-Agent (A2A) protocols.

### Core Design Principle

**The A2U interface is exclusively designed for scenarios where the upper-layer system does NOT possess Agent capabilities.**

In the A2U interaction model:
- The **upper-layer system** (OSS, BSS, orchestrator, or human operator) always acts as a **Client/User** at the protocol level
- The **NMA** always acts as the **Server/Agent** providing services
- There is **no peer-to-peer Agent negotiation** between the two parties

### When to Use A2U

Use the A2U interface when:
- An OSS/BSS system needs to invoke NMA capabilities (e.g., create an OTN service via natural language or structured API call)
- A human operator interacts with the NMA through a chat interface or management portal
- The caller does not implement the Agent lifecycle (intent parsing, task planning, tool calling, etc.) itself

### When NOT to Use A2U (Use A2A Instead)

If the upper-layer system **is itself an Agent** (equipped with LLM reasoning, task planning, and tool invocation capabilities), it should interact with the lower-layer NMA through an **A2A (Agent-to-Agent) protocol** rather than A2U.

In A2A scenarios:
- Both parties are **peer Agents** with equal protocol status
- Bidirectional intent submission, capability negotiation, and commitment mechanisms are required
- Cross-domain collaboration (e.g., cross-operator, cross-vendor, IP/optical coordination) falls into this category

### Comparison Summary

| Dimension | **A2U (This Document)** | **A2A (e.g., A2A-T)** |
|:---|:---|:---|
| **Role Relationship** | Client-Server (User → Agent) | Peer-to-Peer (Agent ↔ Agent) |
| **Upper-Layer System** | OSS/BSS, orchestrator, human operator | Another NMA or autonomous system |
| **Upper-Layer Capability** | Does NOT need Agent capabilities | MUST possess Agent capabilities |
| **Protocol Semantics** | Intent submission, task query, confirmation, event streaming | Capability negotiation, task delegation, result aggregation, trust establishment |
| **Typical Use Case** | OSS calls vendor NMA to provision a service | Operator A's NMA delegates a sub-task to Operator B's NMA |
| **Standardization Body** | IETF (NMOP WG) | TMF (IG1453 A2A-T) or future IETF work |

### Relationship with A2A-T

The A2U interface and TMF IG1453 (A2A-T) are **complementary** rather than competing:

- **A2U** provides the **service access point** for non-Agent systems to consume Agent capabilities
- **A2A-T** provides the **collaboration channel** between peer Agents across administrative domains

An upper-layer system MAY contain an internal Agent, but when it invokes a lower-layer NMA through the A2U interface, it adopts the standardized **intent-task-confirmation-event** primitives defined herein, not A2A negotiation semantics.

## Repository Structure

```
.
├── draft-zhao-nmop-nma-a2u-framework-00.xml   # Main IETF draft (XML)
├── yang/                                       # YANG data models
│   ├── ietf-nma-a2u-common.yang
│   ├── ietf-nma-a2u-capabilities.yang
│   ├── ietf-nma-a2u-intent.yang
│   ├── ietf-nma-a2u-tasks.yang
│   ├── ietf-nma-a2u-confirmations.yang
│   └── ietf-nma-a2u-events.yang
├── Makefile                                    # Build automation
├── README.md                                   # This file
├── CONTRIBUTING.md                             # Contribution guidelines
└── LICENSE                                     # BSD 2-Clause License
```

## Building

### Prerequisites

```bash
pip install xml2rfc
```

### Generate Draft Outputs

```bash
make                    # Generate all formats (txt, html, pdf)
make text               # Generate text only
make html               # Generate HTML only
make clean              # Clean generated files
```

Generated files will be placed in the `build/` directory.

## YANG Modules

| Module | Description |
|:---|:---|
| `ietf-nma-a2u-common` | Common types, enumerations, and groupings |
| `ietf-nma-a2u-capabilities` | Agent capability discovery (Agent Card) |
| `ietf-nma-a2u-intent` | Unified intent model (NL / Structured dual-modal) |
| `ietf-nma-a2u-tasks` | Task lifecycle, plan, result, audit log |
| `ietf-nma-a2u-confirmations` | Human-in-the-loop confirmation |
| `ietf-nma-a2u-events` | Event notifications |

## Relationship to Other Work

- **NMA Architecture**: [draft-zhao-nmop-network-management-agent](https://datatracker.ietf.org/doc/draft-zhao-nmop-network-management-agent/)
- **A2A Protocol**: TMF IG1453 (A2A-T) for peer-to-peer agent collaboration
- **Intent-Based Networking**: [RFC 9315](https://www.rfc-editor.org/rfc/rfc9315.html)
- **YANG Automation**: [RFC 8969](https://www.rfc-editor.org/rfc/rfc8969.html)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues, proposing changes, and YANG model updates.

## License

This work is licensed under the BSD 2-Clause License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 IETF Trust and the persons identified as authors of the code.
