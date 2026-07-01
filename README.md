# Framework and YANG Data Model for the NMA A2U Interface

This repository contains the Internet-Draft and YANG data model for the Agent-to-User (A2U) interface of a Network Management Agent (NMA).

The A2U interface is a user-facing interface through which a non-agent upper-layer system or user, such as an operator's OSS/BSS, orchestrator, management portal, human-facing application, or automation system, interacts with an NMA.

## Current draft

- `draft-zhao-nmop-nma-a2u-interface-00.xml` — xml2rfc source
- `draft-zhao-nmop-nma-a2u-interface-00.txt` — rendered text version
- `yang/ietf-nma-a2u@2026-06-30.yang` — standalone YANG module extracted from the draft

## Scope

The draft defines:

- A2U interface positioning;
- A2U reference framework;
- A2U interaction principles;
- A2U information model;
- a single YANG data model for A2U objects;
- a non-normative HTTP-based protocol binding example.

The A2U interface is not intended for NMA-to-NMA or Agent-to-Agent communication. Such communication is outside the scope of this draft and is expected to use A2A or other Agent-to-Agent interfaces.

## Example scenario

The examples in the draft use an OTN fault handling and service assurance scenario. An OSS detects degradation of an OTN service and invokes the NMA through A2U. The NMA analyzes alarms and performance data, correlates service impact, identifies the likely root cause, generates a recovery plan, requests confirmation, and reports task progress through events.

## Validation

Recommended checks before submission:

```sh
xml2rfc draft-zhao-nmop-nma-a2u-interface-00.xml --text --html
pyang --lint yang/ietf-nma-a2u@2026-06-30.yang
```

