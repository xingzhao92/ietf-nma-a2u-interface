#!/usr/bin/env python3
"""Extract ietf-nma-a2u.yang from the paginated Internet-Draft TXT."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = root / "drafts" / "draft-zhao-nmop-nma-a2u-yang-00.txt"
target = root / "yang" / "ietf-nma-a2u.yang"
raw = source.read_text(encoding="utf-8", errors="replace").splitlines()
start = next(i for i, line in enumerate(raw) if line.startswith("   module ietf-nma-a2u {"))
end = next(i for i, line in enumerate(raw[start + 1 :], start + 1)
           if line.startswith("9.  Security Considerations"))
output = []
blank = 0
for line in raw[start:end]:
    line = line.replace("\f", "")
    if re.match(r"^Zhao, et al\.\s+Expires ", line):
        continue
    if re.match(r"^Internet-Draft\s+NMA A2U Interface\s+July 2026\s*$", line):
        continue
    if line.startswith("   "):
        line = line[3:]
    line = line.rstrip()
    if not line:
        blank += 1
        if blank > 2:
            continue
    else:
        blank = 0
    output.append(line)
target.write_text("\n".join(output).strip() + "\n", encoding="utf-8")
print(f"Wrote {target}")
