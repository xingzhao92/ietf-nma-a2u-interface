# GitHub Update Notes

This package is prepared from the confirmed XML/TXT draft files.

## Files to add or replace

Copy these files into the root of the GitHub repository:

- `draft-zhao-nmop-nma-a2u-interface-00.xml`
- `draft-zhao-nmop-nma-a2u-interface-00.txt`
- `README.md`

Copy this file into the `yang/` directory:

- `yang/ietf-nma-a2u@2026-06-30.yang`

## Old files to remove, if present

The model has been consolidated into a single YANG module. Remove the old split modules if they still exist:

- `yang/ietf-nma-a2u-common.yang`
- `yang/ietf-nma-a2u-capabilities.yang`
- `yang/ietf-nma-a2u-intent.yang`
- `yang/ietf-nma-a2u-tasks.yang`
- `yang/ietf-nma-a2u-confirmations.yang`
- `yang/ietf-nma-a2u-events.yang`

Also remove or archive older draft filenames if present, such as:

- `draft-zhao-nmop-nma-a2u-framework-00.xml`
- `draft-zhao-nmop-nma-a2u-framework-00.txt`

## Suggested Git commands

```sh
# from the repository root
cp /path/to/update/draft-zhao-nmop-nma-a2u-interface-00.xml .
cp /path/to/update/draft-zhao-nmop-nma-a2u-interface-00.txt .
cp /path/to/update/README.md .
mkdir -p yang
cp /path/to/update/yang/ietf-nma-a2u@2026-06-30.yang yang/

git rm -f   yang/ietf-nma-a2u-common.yang   yang/ietf-nma-a2u-capabilities.yang   yang/ietf-nma-a2u-intent.yang   yang/ietf-nma-a2u-tasks.yang   yang/ietf-nma-a2u-confirmations.yang   yang/ietf-nma-a2u-events.yang 2>/dev/null || true

git add draft-zhao-nmop-nma-a2u-interface-00.xml         draft-zhao-nmop-nma-a2u-interface-00.txt         README.md         yang/ietf-nma-a2u@2026-06-30.yang

git commit -m "Update NMA A2U interface draft and YANG model"
git push
```

