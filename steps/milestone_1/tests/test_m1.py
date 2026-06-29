"""Tests for milestone 1: parse Flask source and route metadata to produce route_policies.json."""

import ast
import json
from pathlib import Path

def _parse_flask_routes():
    """Re-parse routes.py independently to compute expected decorator assignments."""
    src = Path("/app/api/routes.py").read_text()
    tree = ast.parse(src)
    entries = {}
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
            elif isinstance(dec, ast.Name) and dec.id in (
                "require_auth",
                "require_admin",
            ):
                auth_dec = dec.id
        if route_path:
            entries[route_path] = {"method": method, "decorator": auth_dec}
    return entries


def _load_metadata():
    return {
        m["route"]: m for m in json.loads(Path("/app/route_metadata.json").read_text())
    }


class TestMilestone1:
    """Tests for milestone 1: /app/route_policies.json must be created from Flask source + metadata."""

    def test_output_file_exists(self):
        """Verify route_policies.json was created at /app/route_policies.json."""
        assert Path("/app/route_policies.json").exists()

    def test_output_is_valid_json(self):
        """Verify /app/route_policies.json contains valid JSON."""
        text = Path("/app/route_policies.json").read_text()
        data = json.loads(text)
        assert isinstance(data, list)

    def test_all_routes_present(self):
        """Verify every route declared in routes.py appears in route_policies.json."""
        expected_routes = set(_parse_flask_routes().keys())
        actual = json.loads(Path("/app/route_policies.json").read_text())
        actual_routes = {p["route"] for p in actual}
        assert expected_routes == actual_routes

    def test_required_fields_present(self):
        """Verify each policy entry has route, method, decorator, required_claims, middleware_enforced."""
        policies = json.loads(Path("/app/route_policies.json").read_text())
        required = {
            "route",
            "method",
            "decorator",
            "required_claims",
            "middleware_enforced",
        }
        for p in policies:
            missing = required - set(p.keys())
            assert not missing, f"Policy for {p.get('route')} missing fields: {missing}"

    def test_decorator_values_match_source(self):
        """Verify decorator field in each policy matches the decorator in routes.py."""
        expected = _parse_flask_routes()
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            route = p["route"]
            assert route in expected, f"Unexpected route {route}"
            assert p["decorator"] == expected[route]["decorator"], (
                f"{route}: expected decorator={expected[route]['decorator']}, got {p['decorator']}"
            )

    def test_method_values_match_source(self):
        """Verify method field in each policy matches the HTTP method in routes.py."""
        expected = _parse_flask_routes()
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            route = p["route"]
            assert p["method"] == expected[route]["method"], (
                f"{route}: expected method={expected[route]['method']}, got {p['method']}"
            )

    def test_middleware_enforced_matches_metadata(self):
        """Verify middleware_enforced in each policy matches route_metadata.json."""
        meta = _load_metadata()
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            route = p["route"]
            assert route in meta, f"Route {route} not in route_metadata.json"
            assert p["middleware_enforced"] == meta[route]["middleware_enforced"], (
                f"{route}: middleware_enforced mismatch"
            )

    def test_required_claims_for_auth_routes(self):
        """Verify routes with require_auth or require_admin have exactly {role, sub} as required_claims."""
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            if p["decorator"] in ("require_auth", "require_admin"):
                assert p["required_claims"] == ["role", "sub"], (
                    f"{p['route']}: required_claims must be exactly ['role', 'sub'] sorted alphabetically, got {p['required_claims']}"
                )

    def test_required_claims_empty_for_public_routes(self):
        """Verify routes with no decorator have an empty required_claims list."""
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            if p["decorator"] == "none":
                assert p["required_claims"] == [], (
                    f"{p['route']}: public route should have empty required_claims"
                )

    def test_sorted_by_route(self):
        """Verify route_policies.json entries are sorted alphabetically by route path."""
        policies = json.loads(Path("/app/route_policies.json").read_text())
        routes = [p["route"] for p in policies]
        assert routes == sorted(routes), "Policies must be sorted by route path"

    def test_mismatch_route_api_profile(self):
        """Verify /api/profile has decorator=require_auth but middleware_enforced=false (key mismatch case)."""
        policies = {
            p["route"]: p
            for p in json.loads(Path("/app/route_policies.json").read_text())
        }
        assert "/api/profile" in policies
        p = policies["/api/profile"]
        assert p["decorator"] == "require_auth"
        assert p["middleware_enforced"] is False

    def test_mismatch_route_api_report(self):
        """Verify /api/report has decorator=require_auth but middleware_enforced=false (second mismatch-not-enforced case)."""
        policies = {
            p["route"]: p
            for p in json.loads(Path("/app/route_policies.json").read_text())
        }
        assert "/api/report" in policies
        p = policies["/api/report"]
        assert p["decorator"] == "require_auth"
        assert p["middleware_enforced"] is False

    def test_mismatch_route_internal_status(self):
        """Verify /internal/status has decorator=none but middleware_enforced=true (shadow enforcement case)."""
        policies = {
            p["route"]: p
            for p in json.loads(Path("/app/route_policies.json").read_text())
        }
        assert "/internal/status" in policies
        p = policies["/internal/status"]
        assert p["decorator"] == "none"
        assert p["middleware_enforced"] is True

    def test_no_extra_fields(self):
        """Verify no unexpected extra fields appear in policy entries."""
        allowed = {
            "route",
            "method",
            "decorator",
            "required_claims",
            "middleware_enforced",
        }
        policies = json.loads(Path("/app/route_policies.json").read_text())
        for p in policies:
            extra = set(p.keys()) - allowed
            assert not extra, (
                f"Unexpected fields in policy for {p.get('route')}: {extra}"
            )
