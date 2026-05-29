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
