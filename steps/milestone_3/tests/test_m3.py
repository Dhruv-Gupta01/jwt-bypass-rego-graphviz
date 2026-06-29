"""Tests for milestone 3: Rego reachability over findings and call graph must produce attack_graph.dot."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def _load_findings():
    return json.loads(Path("/app/findings.json").read_text())


def _load_route_calls():
    return json.loads(Path("/app/route_calls.json").read_text())


def _parse_dot(dot_text):
    """Parse DOT file into (nodes, edges) — returns sets for comparison."""
    nodes = set()
    edges = set()
    for line in dot_text.splitlines():
        line = line.strip()
        m_edge = re.match(r'^"([^"]+)"\s*->\s*"([^"]+)"', line)
        if m_edge:
            edges.add((m_edge.group(1), m_edge.group(2)))
            continue
        m_node = re.match(r'^"([^"]+)"\s*\[label="[^"]+"[^\]]*\]', line)
        if m_node:
            nodes.add(m_node.group(1))
    return nodes, edges


def _parse_dot_node_attrs(dot_text):
    """Parse DOT file node lines, returning dict of node -> {label, exposure}."""
    result = {}
    for line in dot_text.splitlines():
        line = line.strip()
        m = re.match(r'^"([^"]+)"\s*\[label="([^"]+)"(?:\s+exposure=(\d+))?\]', line)
        if m:
            result[m.group(1)] = {
                "label": m.group(2),
                "exposure": int(m.group(3)) if m.group(3) is not None else None,
            }
    return result


def _expected_exposure():
    """Compute expected exposure counts from findings and route_calls."""
    findings = _load_findings()
    route_calls = _load_route_calls()
    finding_routes = {f["route"] for f in findings}

    # Per-source 3-hop reachability
    def reachable_from(source):
        reach = {source}
        for _ in range(3):
            new = set(reach)
            for r in reach:
                new.update(route_calls.get(r, []))
            reach = new
        return reach

    all_nodes, _ = _expected_nodes_and_edges()
    exposure = {}
    for node in all_nodes:
        exposure[node] = sum(1 for fr in finding_routes if node in reachable_from(fr))
    return exposure


def _expected_nodes_and_edges():
    """Compute expected attack graph from findings and route_calls via 3-hop bounded reachability."""
    findings = _load_findings()
    route_calls = _load_route_calls()

    finding_routes = {f["route"] for f in findings}

    # Bounded 3-hop reachability
    reachable = set(finding_routes)
    for _ in range(3):
        next_reach = set(reachable)
        for src in reachable:
            for dst in route_calls.get(src, []):
                next_reach.add(dst)
        reachable = next_reach

    edges = set()
    for src in reachable:
        for dst in route_calls.get(src, []):
            if dst in reachable:
                edges.add((src, dst))

    return reachable, edges


class TestMilestone3:
    """Tests for milestone 3: /app/attack_graph.dot must match the bounded reachability attack graph."""

    def test_prerequisite_findings_exists(self):
        """Verify milestone 2 output is available before running milestone 3 tests."""
        assert Path("/app/findings.json").exists(), (
            "findings.json missing — milestone 2 must complete first"
        )

    def test_rego_file_exists(self):
        """Verify attack_graph.rego was written at /app/attack_graph.rego (agent must use Rego, not bypass it)."""
        assert Path("/app/attack_graph.rego").exists(), "attack_graph.rego must exist — implement reachability in Rego"

    def test_rego_is_syntactically_valid(self):
        """Verify attack_graph.rego passes OPA syntax check and defines reachability rules."""
        rego_text = Path("/app/attack_graph.rego").read_text()
        assert "package" in rego_text, "attack_graph.rego must declare a Rego package"
        assert any(kw in rego_text for kw in ("reachable", "nodes", "edges")), (
            "attack_graph.rego must define reachability rules (expected 'reachable', 'nodes', or 'edges')"
        )
        assert "data.findings" in rego_text, (
            "attack_graph.rego must reference data.findings — Rego must read from the input data, not hardcode values"
        )
        result = subprocess.run(
            ["opa", "check", "/app/attack_graph.rego"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"attack_graph.rego has Rego syntax errors:\n{result.stderr}"

    def _opa_eval_graph(self, rule):
        """Helper: run OPA eval for data.attack_graph.<rule> and return the raw value."""
        findings = _load_findings()
        route_calls = _load_route_calls()
        opa_input = {"findings": findings, "route_calls": route_calls}
        fd, input_path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(opa_input, f)
            result = subprocess.run(
                ["opa", "eval", "--format", "json",
                 "--data", input_path,
                 "--data", "/app/attack_graph.rego",
                 f"data.attack_graph.{rule}"],
                capture_output=True, text=True
            )
            assert result.returncode == 0, (
                f"OPA eval of data.attack_graph.{rule} failed:\n{result.stderr}"
            )
            return json.loads(result.stdout)["result"][0]["expressions"][0]["value"]
        finally:
            os.unlink(input_path)

    def test_rego_produces_correct_nodes(self):
        """Verify that OPA evaluation of attack_graph.rego produces the expected reachable node set."""
        rego_text = Path("/app/attack_graph.rego").read_text()
        assert "package attack_graph" in rego_text, (
            "attack_graph.rego must use 'package attack_graph' as instructed"
        )
        opa_nodes = set(self._opa_eval_graph("nodes"))
        expected_nodes, _ = _expected_nodes_and_edges()
        assert opa_nodes == expected_nodes, (
            f"OPA nodes mismatch.\nExpected: {sorted(expected_nodes)}\nOPA: {sorted(opa_nodes)}"
        )

    def test_rego_produces_correct_edges(self):
        """Verify that OPA evaluation of attack_graph.rego produces the correct edge set."""
        opa_raw = self._opa_eval_graph("edges")
        opa_edges = {tuple(e) for e in opa_raw}
        _, expected_edges = _expected_nodes_and_edges()
        assert opa_edges == expected_edges, (
            f"OPA edges mismatch.\nExpected: {sorted(expected_edges)}\nOPA: {sorted(opa_edges)}"
        )

    def test_output_file_exists(self):
        """Verify attack_graph.dot was created at /app/attack_graph.dot."""
        assert Path("/app/attack_graph.dot").exists()

    def test_is_valid_digraph(self):
        """Verify attack_graph.dot declares a digraph named attack_paths."""
        text = Path("/app/attack_graph.dot").read_text()
        assert re.search(r'digraph\s+attack_paths\s*\{', text), (
            "DOT file must declare 'digraph attack_paths {'"
        )
        assert "}" in text, "DOT file must have closing brace"

    def test_nodes_match_reachable_set(self):
        """Verify the nodes in the DOT file exactly match the 3-hop reachable set from finding routes."""
        expected_nodes, _ = _expected_nodes_and_edges()
        actual_nodes, _ = _parse_dot(Path("/app/attack_graph.dot").read_text())
        assert actual_nodes == expected_nodes, (
            f"Node mismatch.\nExpected: {sorted(expected_nodes)}\nActual: {sorted(actual_nodes)}"
        )

    def test_edges_match_call_graph(self):
        """Verify edges in DOT match directed call relationships between reachable nodes."""
        _, expected_edges = _expected_nodes_and_edges()
        _, actual_edges = _parse_dot(Path("/app/attack_graph.dot").read_text())
        assert actual_edges == expected_edges, (
            f"Edge mismatch.\nExpected: {sorted(expected_edges)}\nActual: {sorted(actual_edges)}"
        )

    def test_edges_are_directed_not_symmetric(self):
        """Verify no pair of nodes has edges in both directions — edges must be directed (Trap 4 guard)."""
        _, actual_edges = _parse_dot(Path("/app/attack_graph.dot").read_text())
        for src, dst in actual_edges:
            assert (dst, src) not in actual_edges, (
                f"Symmetric edge detected: both ({src}->{dst}) and ({dst}->{src}) present"
            )

    def test_node_label_matches_id(self):
        """Verify each node declaration has label equal to the node ID: "route" [label="route" exposure=N]."""
        attrs = _parse_dot_node_attrs(Path("/app/attack_graph.dot").read_text())
        assert attrs, "No node declarations found in attack_graph.dot"
        for node_id, a in attrs.items():
            assert a["label"] == node_id, (
                f"Node label must equal node ID. Got id={node_id!r} but label={a['label']!r}"
            )

    def test_exposure_attribute_in_dot(self):
        """Verify each node in attack_graph.dot carries an exposure=N attribute with the correct value."""
        attrs = _parse_dot_node_attrs(Path("/app/attack_graph.dot").read_text())
        expected = _expected_exposure()
        for node, exp_count in expected.items():
            assert node in attrs, f"Node {node} not found in attack_graph.dot"
            assert attrs[node]["exposure"] is not None, (
                f"Node {node} is missing the exposure attribute in its DOT declaration"
            )
            assert attrs[node]["exposure"] == exp_count, (
                f"Node {node}: exposure={attrs[node]['exposure']} but expected {exp_count}"
            )

    def test_rego_produces_correct_exposure(self):
        """Verify OPA evaluation of data.attack_graph.exposure matches the expected per-node exposure counts."""
        opa_exposure = self._opa_eval_graph("exposure")
        expected = _expected_exposure()
        assert opa_exposure == expected, (
            f"OPA exposure mismatch.\nExpected: {expected}\nOPA: {opa_exposure}"
        )

    def test_nodes_sorted_alphabetically(self):
        """Verify node declarations appear in alphabetical order in the DOT file."""
        text = Path("/app/attack_graph.dot").read_text()
        node_decls = list(_parse_dot_node_attrs(text).keys())
        assert node_decls == sorted(node_decls), (
            f"Nodes not in alphabetical order: {node_decls}"
        )

    def test_edges_sorted_by_src_then_dst(self):
        """Verify edge declarations appear sorted by source then destination in the DOT file."""
        text = Path("/app/attack_graph.dot").read_text()
        edge_decls = []
        for line in text.splitlines():
            m = re.match(r'^"([^"]+)"\s*->\s*"([^"]+)"', line.strip())
            if m:
                edge_decls.append((m.group(1), m.group(2)))
        assert edge_decls == sorted(edge_decls), (
            f"Edges not sorted by [src, dst]: {edge_decls}"
        )

    def test_node_declarations_before_edges(self):
        """Verify all node declarations appear before any edge declarations in the DOT file."""
        text = Path("/app/attack_graph.dot").read_text()
        last_node_line = -1
        first_edge_line = float("inf")
        for i, line in enumerate(text.splitlines()):
            s = line.strip()
            if re.match(r'^"[^"]+"\s*\[label=', s):
                last_node_line = i
            elif re.match(r'^"[^"]+"\s*->', s):
                first_edge_line = min(first_edge_line, i)
        if first_edge_line < float("inf"):
            assert last_node_line < first_edge_line, (
                "All node declarations must appear before edge declarations"
            )

    def test_all_finding_routes_are_nodes(self):
        """Verify every route that has a finding is represented as a node in the attack graph."""
        findings = _load_findings()
        finding_routes = {f["route"] for f in findings}
        actual_nodes, _ = _parse_dot(Path("/app/attack_graph.dot").read_text())
        for route in finding_routes:
            assert route in actual_nodes, (
                f"Finding route {route} missing from attack graph nodes"
            )

    def test_reachability_includes_call_targets(self):
        """Verify routes reachable via route_calls from finding routes appear as nodes."""
        findings = _load_findings()
        route_calls = _load_route_calls()
        finding_routes = {f["route"] for f in findings}
        expected_reachable, _ = _expected_nodes_and_edges()
        actual_nodes, _ = _parse_dot(Path("/app/attack_graph.dot").read_text())
        call_targets = {
            dst for src in finding_routes for dst in route_calls.get(src, [])
        }
        for target in call_targets:
            assert target in actual_nodes, (
                f"Route {target} is reachable from a finding route but missing from attack graph"
            )

