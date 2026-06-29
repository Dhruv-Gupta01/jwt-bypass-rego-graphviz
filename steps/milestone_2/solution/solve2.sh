#!/bin/bash
set -euo pipefail

ORACLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$ORACLE_DIR/findings.rego" /app/findings.rego

python3 -c "
import json
policies = json.loads(open('/app/route_policies.json').read())
logs = [json.loads(line) for line in open('/app/access_logs.ndjson') if line.strip()]
route_calls = json.loads(open('/app/route_calls.json').read())
data = {'route_policies': policies, 'access_logs': logs, 'route_calls': route_calls}
open('/app/opa_input_m2.json', 'w').write(json.dumps(data))
"

opa eval \
    --format json \
    --data /app/opa_input_m2.json \
    --data /app/findings.rego \
    'data.jwt_bypass.findings' \
| python3 -c "
import json, sys
result = json.load(sys.stdin)
findings = result['result'][0]['expressions'][0]['value']
findings_list = sorted(findings, key=lambda f: (f['route'], f['finding_type']))
print(json.dumps(findings_list, indent=2))
" > /app/findings.json

NFINDINGS=$(python3 -c "import json; print(len(json.load(open('/app/findings.json'))))")
echo "Wrote $NFINDINGS findings to /app/findings.json"
