#!/usr/bin/env python3
"""Lightweight repository consistency checks without external dependencies."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
draft = root / "drafts" / "draft-zhao-nmop-nma-a2u-yang-00.txt"
yang = root / "yang" / "ietf-nma-a2u.yang"
required = [
    root / "IETF126-hackathon-demo" / "app.py",
    root / "IETF126-hackathon-demo" / "agent.py",
    root / "IETF126-hackathon-demo" / "controller.py",
    root / "docs" / "images" / "oss-a2u-client.png",
    root / "docs" / "images" / "domain-controller.png",
]
for path in [draft, yang, *required]:
    assert path.exists(), f"Missing: {path.relative_to(root)}"
text = yang.read_text(encoding="utf-8")
for token in [
    "module ietf-nma-a2u", "rpc submit-intent", "rpc resolve-confirmation",
    "rpc abort-task", "notification a2u-task-notification",
    "enum CREATE", "enum DELETE", "enum MODIFY", "enum QUERY",
    "enum REPORT", "enum DIAGNOSE", "enum REMEDIATE", "enum OPTIMIZE",
    "enum ASSURE",
]:
    assert token in text, f"Missing YANG token: {token}"
# Basic balanced-brace check outside quoted strings.
count = 0
in_string = False
escaped = False
for ch in text:
    if in_string:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            in_string = False
        continue
    if ch == '"':
        in_string = True
    elif ch == "{":
        count += 1
    elif ch == "}":
        count -= 1
        assert count >= 0, "Unexpected closing brace"
assert count == 0, f"Unbalanced braces: {count}"
print("PASS: draft, YANG module, demo code, screenshots, enums, RPCs, and notification are present")
