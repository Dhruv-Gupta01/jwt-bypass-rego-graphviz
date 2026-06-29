#!/bin/bash
set -euo pipefail

python3 - << 'PYEOF'
import ast
import json
from pathlib import Path

src = Path("/app/api/routes.py").read_text()
tree = ast.parse(src)

entries = []
for node in ast.walk(tree):
    if not isinstance(node, ast.FunctionDef):
        continue

    route_path = None
    method = "GET"
    auth_dec = "none"

    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Attribute) and func.attr == "route":
                if dec.args:
                    route_path = ast.literal_eval(dec.args[0])
                for kw in dec.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, ast.List):
                        method = ast.literal_eval(kw.value.elts[0])
        elif isinstance(dec, ast.Name) and dec.id in ("require_auth", "require_admin"):
            auth_dec = dec.id

    if route_path:
        entries.append({"route": route_path, "method": method, "decorator": auth_dec})

metadata = json.loads(Path("/app/route_metadata.json").read_text())
meta_map = {m["route"]: m for m in metadata}

claim_map = {
    "require_auth": ["role", "sub"],
    "require_admin": ["role", "sub"],
    "none": [],
}

policies = []
for e in entries:
    meta = meta_map.get(e["route"], {})
    policies.append(
        {
            "route": e["route"],
            "method": e["method"],
            "decorator": e["decorator"],
            "required_claims": claim_map[e["decorator"]],
            "middleware_enforced": meta.get("middleware_enforced", False),
        }
    )

policies.sort(key=lambda p: p["route"])
Path("/app/route_policies.json").write_text(json.dumps(policies, indent=2))
print(f"Wrote {len(policies)} route policies to /app/route_policies.json")
PYEOF
