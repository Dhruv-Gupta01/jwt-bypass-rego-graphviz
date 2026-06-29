#!/bin/bash
set -euo pipefail

ORACLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$ORACLE_DIR/attack_graph.rego" /app/attack_graph.rego

python3 -c "
import json
findings = json.loads(open('/app/findings.json').read())
route_calls = json.loads(open('/app/route_calls.json').read())
data = {'findings': findings, 'route_calls': route_calls}
open('/app/opa_input_m3.json', 'w').write(json.dumps(data))
"

opa eval \
    --format json \
    --data /app/opa_input_m3.json \
    --data /app/attack_graph.rego \
    'data.attack_graph.nodes' > /tmp/ag_nodes.json

opa eval \
    --format json \
    --data /app/opa_input_m3.json \
    --data /app/attack_graph.rego \
    'data.attack_graph.edges' > /tmp/ag_edges.json

opa eval \
    --format json \
    --data /app/opa_input_m3.json \
    --data /app/attack_graph.rego \
    'data.attack_graph.exposure' > /tmp/ag_exposure.json

python3 - << 'PYEOF'
import json

nodes = json.loads(open("/tmp/ag_nodes.json").read())['result'][0]['expressions'][0]['value']
edges = json.loads(open("/tmp/ag_edges.json").read())['result'][0]['expressions'][0]['value']
exposure = json.loads(open("/tmp/ag_exposure.json").read())['result'][0]['expressions'][0]['value']

nodes_sorted = sorted(nodes)
edges_sorted = sorted([tuple(e) for e in edges])

lines = ["digraph attack_paths {"]
for n in nodes_sorted:
    exp = exposure.get(n, 0)
    lines.append(f'"{n}" [label="{n}" exposure={exp}]')
for src, dst in edges_sorted:
    lines.append(f'"{src}" -> "{dst}"')
lines.append("}")

with open("/app/attack_graph.dot", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote attack graph: {len(nodes_sorted)} nodes, {len(edges_sorted)} edges")
PYEOF
