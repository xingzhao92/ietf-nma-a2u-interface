# YANG module

`ietf-nma-a2u.yang` is extracted from Section 8.3 of the final Internet-Draft TXT in `../drafts/`.

Regenerate it with:

```bash
python scripts/extract_yang.py
```

Validate with an installed YANG tool, for example:

```bash
pyang -p <ietf-yang-module-path> yang/ietf-nma-a2u.yang
```
