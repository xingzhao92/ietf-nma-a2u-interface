from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app


schema = app.openapi()
paths = set(schema["paths"])

assert paths
assert all("ietf-nma-a2u" in path for path in paths)
assert not any("/api/demo/" in path for path in paths)
assert not any("/nma/" in path for path in paths)
assert not any("subscribed-notifications" in path for path in paths)
assert not any("/subscriptions/" in path for path in paths)

for path in (
    "/restconf/operations/ietf-nma-a2u:submit-intent",
    "/restconf/operations/ietf-nma-a2u:resolve-confirmation",
    "/restconf/operations/ietf-nma-a2u:abort-task",
):
    request_body = schema["paths"][path]["post"]["requestBody"]
    media = request_body["content"]["application/json"]
    assert "examples" in media and media["examples"]

print("PASS: A2U-only OpenAPI paths and pre-populated RPC examples")

submit_media = schema["paths"][
    "/restconf/operations/ietf-nma-a2u:submit-intent"
]["post"]["requestBody"]["content"]["application/json"]
submit_examples = submit_media["examples"]
assert "natural-language-incident" in submit_examples
assert "structured-incident" in submit_examples
assert submit_examples["natural-language-incident"]["value"]["intent"]["mode"] == "natural-language"
assert "natural-language" in submit_examples["natural-language-incident"]["value"]["intent"]
assert submit_examples["structured-incident"]["value"]["intent"]["mode"] == "structured"
