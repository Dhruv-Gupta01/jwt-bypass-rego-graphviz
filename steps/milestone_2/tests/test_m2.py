"""Tests for milestone 2: Rego rules over route policies and access logs must produce findings.json."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def _load_findings():
    return json.loads(Path("/app/findings.json").read_text())


def _load_policies():
    return json.loads(Path("/app/route_policies.json").read_text())


def _load_logs():
    lines = [
        line
        for line in Path("/app/access_logs.ndjson").read_text().splitlines()
        if line.strip()
    ]
    return [json.loads(line) for line in lines]


def _load_route_calls():
    return json.loads(Path("/app/route_calls.json").read_text())


class TestMilestone2:
    """Tests for milestone 2: /app/findings.json must identify all six JWT bypass finding types."""

    def test_prerequisite_route_policies_exists(self):
        """Verify milestone 1 output is available before running milestone 2 tests."""
        assert Path("/app/route_policies.json").exists(), (
            "route_policies.json missing — milestone 1 must complete first"
        )

    def test_rego_file_exists(self):
        """Verify findings.rego was written at /app/findings.rego (agent must use Rego, not bypass it)."""
        assert Path("/app/findings.rego").exists(), "findings.rego must exist — implement the rules in Rego"

    def test_rego_is_syntactically_valid(self):
        """Verify findings.rego passes OPA syntax check and declares the required package and rule."""
        rego_text = Path("/app/findings.rego").read_text()
        assert "package jwt_bypass" in rego_text, "findings.rego must declare 'package jwt_bypass'"
        assert "findings" in rego_text, "findings.rego must define a 'findings' rule"
        result = subprocess.run(
            ["opa", "check", "/app/findings.rego"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"findings.rego has Rego syntax errors:\n{result.stderr}"

    def test_rego_produces_correct_findings(self):
        """Verify that evaluating findings.rego with OPA produces output that matches findings.json exactly."""
        rego_text = Path("/app/findings.rego").read_text()
        assert "package jwt_bypass" in rego_text, (
            "findings.rego must use 'package jwt_bypass' as instructed"
        )
        policies = _load_policies()
        logs = _load_logs()
        route_calls = _load_route_calls()
        opa_input = {"route_policies": policies, "access_logs": logs, "route_calls": route_calls}

        fd, input_path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(opa_input, f)
            result = subprocess.run(
                ["opa", "eval", "--format", "json",
                 "--data", input_path,
                 "--data", "/app/findings.rego",
                 "data.jwt_bypass.findings"],
                capture_output=True, text=True
            )
            assert result.returncode == 0, (
                f"OPA eval of findings.rego failed — Rego must evaluate without errors:\n{result.stderr}"
            )
            opa_result = json.loads(result.stdout)
            opa_findings = opa_result["result"][0]["expressions"][0]["value"]
            opa_sorted = sorted(opa_findings, key=lambda f: (f["route"], f["finding_type"]))
            file_findings = _load_findings()
            assert opa_sorted == file_findings, (
                f"OPA eval output does not match /app/findings.json — findings.json must be produced by the Rego rules.\n"
                f"OPA produced {len(opa_sorted)} findings; file has {len(file_findings)} findings."
            )
        finally:
            os.unlink(input_path)

    def test_output_file_exists(self):
        """Verify findings.json was created at /app/findings.json."""
        assert Path("/app/findings.json").exists()

    def test_output_is_valid_json_list(self):
        """Verify /app/findings.json contains a valid JSON array."""
        data = json.loads(Path("/app/findings.json").read_text())
        assert isinstance(data, list)

    def test_required_finding_fields(self):
        """Verify every finding has route, finding_type, and evidence fields."""
        findings = _load_findings()
        assert findings, "findings.json must not be empty"
        for f in findings:
            assert "route" in f, f"Missing 'route' in finding: {f}"
            assert "finding_type" in f, f"Missing 'finding_type' in finding: {f}"
            assert "evidence" in f, f"Missing 'evidence' in finding: {f}"

    def test_sorted_by_route_then_type(self):
        """Verify findings are sorted by [route, finding_type] in ascending order."""
        findings = _load_findings()
        keys = [(f["route"], f["finding_type"]) for f in findings]
        assert keys == sorted(keys), (
            "findings.json must be sorted by [route, finding_type]"
        )

    def test_decorator_middleware_mismatch_auth_not_enforced(self):
        """Verify DECORATOR_MIDDLEWARE_MISMATCH is emitted when decorator requires auth but middleware_enforced is false."""
        policies = {p["route"]: p for p in _load_policies()}
        expected_mismatches = {
            r
            for r, p in policies.items()
            if p["decorator"] != "none" and not p["middleware_enforced"]
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected_mismatches:
            assert (route, "DECORATOR_MIDDLEWARE_MISMATCH") in findings, (
                f"{route}: expected DECORATOR_MIDDLEWARE_MISMATCH (has decorator but not enforced)"
            )

    def test_decorator_middleware_mismatch_shadow_enforcement(self):
        """Verify DECORATOR_MIDDLEWARE_MISMATCH is emitted when no decorator but middleware_enforced is true."""
        policies = {p["route"]: p for p in _load_policies()}
        expected_shadow = {
            r
            for r, p in policies.items()
            if p["decorator"] == "none" and p["middleware_enforced"]
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected_shadow:
            assert (route, "DECORATOR_MIDDLEWARE_MISMATCH") in findings, (
                f"{route}: expected DECORATOR_MIDDLEWARE_MISMATCH (shadow enforcement)"
            )

    def test_scope_not_checked_from_logs(self):
        """Verify SCOPE_NOT_CHECKED is emitted for each auth route where middleware_enforced=true and logs show jwt_valid=true but scope_checked=false."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        routes_with_scope_issue = {
            log["route"]
            for log in logs
            if log["jwt_valid"]
            and not log["scope_checked"]
            and policies.get(log["route"], {}).get("decorator", "none") != "none"
            and policies.get(log["route"], {}).get("middleware_enforced", False)
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in routes_with_scope_issue:
            assert (route, "SCOPE_NOT_CHECKED") in findings, (
                f"{route}: expected SCOPE_NOT_CHECKED (jwt_valid=true but scope_checked=false in logs, middleware_enforced=true)"
            )

    def test_scope_not_checked_not_emitted_when_middleware_not_enforced(self):
        """Verify SCOPE_NOT_CHECKED is NOT emitted for routes where middleware_enforced=false — those get DECORATOR_MIDDLEWARE_MISMATCH instead."""
        policies = {p["route"]: p for p in _load_policies()}
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route, p in policies.items():
            if p["decorator"] != "none" and not p["middleware_enforced"]:
                assert (route, "SCOPE_NOT_CHECKED") not in findings, (
                    f"{route}: SCOPE_NOT_CHECKED must NOT fire when middleware_enforced=false"
                )

    def test_scope_not_checked_not_emitted_when_scope_verified(self):
        """Verify SCOPE_NOT_CHECKED is NOT emitted for routes where all log entries show scope_checked=true (Trap guard)."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        routes_always_checked = {
            r
            for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and not any(
                log["route"] == r and log["jwt_valid"] and not log["scope_checked"]
                for log in logs
            )
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in routes_always_checked:
            assert (route, "SCOPE_NOT_CHECKED") not in findings, (
                f"{route}: SCOPE_NOT_CHECKED should NOT be emitted — scope was always checked in logs"
            )

    def test_role_not_validated_emitted_for_non_admin_access(self):
        """Verify ROLE_NOT_VALIDATED is emitted for require_admin routes (enforced) with log entries where jwt_valid=true, scope_checked=false, and claims.role != 'admin'."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        expected_rnv = {
            log["route"]
            for log in logs
            if log["jwt_valid"]
            and not log["scope_checked"]
            and log.get("claims", {}).get("role") != "admin"
            and policies.get(log["route"], {}).get("decorator") == "require_admin"
            and policies.get(log["route"], {}).get("middleware_enforced", False)
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected_rnv:
            assert (route, "ROLE_NOT_VALIDATED") in findings, (
                f"{route}: expected ROLE_NOT_VALIDATED (non-admin role accessing admin route with scope unchecked)"
            )

    def test_role_not_validated_not_emitted_when_role_is_admin(self):
        """Verify ROLE_NOT_VALIDATED is NOT emitted for require_admin routes where all scope-unchecked log entries have claims.role='admin' (Trap guard)."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        admin_only_routes = {
            r
            for r, p in policies.items()
            if p["decorator"] == "require_admin"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
            and all(
                log.get("claims", {}).get("role") == "admin"
                for log in logs
                if log["route"] == r and log["jwt_valid"] and not log["scope_checked"]
            )
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in admin_only_routes:
            assert (route, "ROLE_NOT_VALIDATED") not in findings, (
                f"{route}: ROLE_NOT_VALIDATED must NOT fire when all scope-unchecked entries have claims.role='admin'"
            )

    def test_role_not_validated_not_emitted_for_require_auth_routes(self):
        """Verify ROLE_NOT_VALIDATED is NOT emitted for require_auth routes — only require_admin routes qualify (Trap guard)."""
        policies = {p["route"]: p for p in _load_policies()}
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route, p in policies.items():
            if p["decorator"] == "require_auth":
                assert (route, "ROLE_NOT_VALIDATED") not in findings, (
                    f"{route}: ROLE_NOT_VALIDATED must NOT fire for require_auth routes (only require_admin)"
                )

    def test_privileged_scope_bypass_emitted_for_admin_only_bypasses(self):
        """Verify PRIVILEGED_SCOPE_BYPASS is emitted for routes with middleware_enforced=true where all scope-unchecked log entries have claims.role='admin'."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        expected_psb = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
            and all(
                log.get("claims", {}).get("role") == "admin"
                for log in logs
                if log["route"] == r and log["jwt_valid"] and not log["scope_checked"]
            )
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected_psb:
            assert (route, "PRIVILEGED_SCOPE_BYPASS") in findings, (
                f"{route}: expected PRIVILEGED_SCOPE_BYPASS (all scope-unchecked entries have role=admin)"
            )

    def test_privileged_scope_bypass_not_emitted_when_non_admin_bypasses(self):
        """Verify PRIVILEGED_SCOPE_BYPASS is NOT emitted when any scope-unchecked entry has a non-admin role (Trap guard — ROLE_NOT_VALIDATED fires instead)."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        has_non_admin_bypass = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(
                log["route"] == r and log["jwt_valid"] and not log["scope_checked"]
                and log.get("claims", {}).get("role") != "admin"
                for log in logs
            )
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in has_non_admin_bypass:
            assert (route, "PRIVILEGED_SCOPE_BYPASS") not in findings, (
                f"{route}: PRIVILEGED_SCOPE_BYPASS must NOT fire when any scope-unchecked entry has role != 'admin'"
            )

    def test_privileged_scope_bypass_not_emitted_when_no_scope_bypass_in_logs(self):
        """Verify PRIVILEGED_SCOPE_BYPASS is NOT emitted for enforced routes with no scope-unchecked log entries at all (Trap guard)."""
        logs = _load_logs()
        policies = {p["route"]: p for p in _load_policies()}
        no_bypass_routes = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and not any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in no_bypass_routes:
            assert (route, "PRIVILEGED_SCOPE_BYPASS") not in findings, (
                f"{route}: PRIVILEGED_SCOPE_BYPASS must NOT fire when no scope-unchecked log entries exist"
            )

    def test_evidence_privileged_scope_bypass_complete(self):
        """Verify PRIVILEGED_SCOPE_BYPASS evidence includes admin_bypass_count matching the actual log count."""
        logs = _load_logs()
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "PRIVILEGED_SCOPE_BYPASS":
                ev = f["evidence"]
                assert "admin_bypass_count" in ev, (
                    f"PRIVILEGED_SCOPE_BYPASS evidence for {f['route']} must include 'admin_bypass_count'"
                )
                expected_count = sum(
                    1 for log in logs
                    if log["route"] == f["route"] and log["jwt_valid"] and not log["scope_checked"]
                )
                assert ev["admin_bypass_count"] == expected_count, (
                    f"{f['route']}: admin_bypass_count={ev['admin_bypass_count']} but logs show {expected_count} entries"
                )

    def test_cascading_bypass_emitted_for_mismatch_to_scope_unchecked(self):
        """Verify CASCADING_BYPASS is emitted for SCOPE_NOT_CHECKED routes that are directly called by a DECORATOR_MIDDLEWARE_MISMATCH route."""
        policies = {p["route"]: p for p in _load_policies()}
        logs = _load_logs()
        route_calls = _load_route_calls()

        mismatch_routes = {
            r for r, p in policies.items()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        }
        scope_not_checked_routes = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
        }
        expected_cascading = {
            downstream
            for upstream in mismatch_routes
            for downstream in route_calls.get(upstream, [])
            if downstream in scope_not_checked_routes
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected_cascading:
            assert (route, "CASCADING_BYPASS") in findings, (
                f"{route}: expected CASCADING_BYPASS (reachable from mismatch route and has scope-not-checked)"
            )

    def test_cascading_bypass_not_emitted_for_non_scope_checked_targets(self):
        """Verify CASCADING_BYPASS is NOT emitted for routes called by mismatch routes that do NOT have SCOPE_NOT_CHECKED (Trap guard)."""
        policies = {p["route"]: p for p in _load_policies()}
        logs = _load_logs()
        route_calls = _load_route_calls()

        mismatch_routes = {
            r for r, p in policies.items()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        }
        scope_not_checked_routes = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
        }
        non_scope_targets = {
            downstream
            for upstream in mismatch_routes
            for downstream in route_calls.get(upstream, [])
            if downstream not in scope_not_checked_routes
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in non_scope_targets:
            assert (route, "CASCADING_BYPASS") not in findings, (
                f"{route}: CASCADING_BYPASS must NOT fire for routes called by mismatch routes that lack SCOPE_NOT_CHECKED"
            )

    def test_cascading_bypass_not_emitted_without_mismatch_upstream(self):
        """Verify CASCADING_BYPASS is NOT emitted for SCOPE_NOT_CHECKED routes that are not called by any DECORATOR_MIDDLEWARE_MISMATCH route (Trap guard)."""
        policies = {p["route"]: p for p in _load_policies()}
        logs = _load_logs()
        route_calls = _load_route_calls()

        mismatch_routes = {
            r for r, p in policies.items()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        }
        called_by_mismatch = {
            downstream
            for upstream in mismatch_routes
            for downstream in route_calls.get(upstream, [])
        }
        scope_not_checked_routes = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
        }
        isolated_scope_routes = scope_not_checked_routes - called_by_mismatch
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in isolated_scope_routes:
            assert (route, "CASCADING_BYPASS") not in findings, (
                f"{route}: CASCADING_BYPASS must NOT fire for SCOPE_NOT_CHECKED routes with no mismatch upstream"
            )

    def test_unenforced_sensitive_admin_routes(self):
        """Verify UNENFORCED_SENSITIVE_ROUTE is emitted for /admin/* routes with no decorator and not enforced."""
        policies = {p["route"]: p for p in _load_policies()}
        expected = {
            r
            for r, p in policies.items()
            if p["decorator"] == "none"
            and not p["middleware_enforced"]
            and r.startswith("/admin/")
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected:
            assert (route, "UNENFORCED_SENSITIVE_ROUTE") in findings, (
                f"{route}: expected UNENFORCED_SENSITIVE_ROUTE"
            )

    def test_unenforced_sensitive_internal_routes(self):
        """Verify UNENFORCED_SENSITIVE_ROUTE is emitted for /internal/* routes with no decorator and not enforced."""
        policies = {p["route"]: p for p in _load_policies()}
        expected = {
            r
            for r, p in policies.items()
            if p["decorator"] == "none"
            and not p["middleware_enforced"]
            and r.startswith("/internal/")
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in expected:
            assert (route, "UNENFORCED_SENSITIVE_ROUTE") in findings, (
                f"{route}: expected UNENFORCED_SENSITIVE_ROUTE"
            )

    def test_unenforced_not_emitted_for_non_sensitive_paths(self):
        """Verify UNENFORCED_SENSITIVE_ROUTE is NOT emitted for routes outside /admin/* and /internal/* (Trap guard)."""
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "UNENFORCED_SENSITIVE_ROUTE":
                assert f["route"].startswith("/admin/") or f["route"].startswith("/internal/"), (
                    f"UNENFORCED_SENSITIVE_ROUTE emitted for non-sensitive path: {f['route']}"
                )

    def test_no_false_positive_for_enforced_auth_route(self):
        """Verify routes with matching decorator and middleware_enforced do NOT produce DECORATOR_MIDDLEWARE_MISMATCH."""
        policies = {p["route"]: p for p in _load_policies()}
        correct_routes = {
            r
            for r, p in policies.items()
            if p["decorator"] != "none" and p["middleware_enforced"]
        }
        findings = {(f["route"], f["finding_type"]) for f in _load_findings()}
        for route in correct_routes:
            assert (route, "DECORATOR_MIDDLEWARE_MISMATCH") not in findings, (
                f"{route}: should NOT have DECORATOR_MIDDLEWARE_MISMATCH (decorator and middleware agree)"
            )

    def test_evidence_mismatch_contains_decorator_and_enforcement(self):
        """Verify DECORATOR_MIDDLEWARE_MISMATCH evidence includes decorator and middleware_enforced with correct values."""
        policies = {p["route"]: p for p in _load_policies()}
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "DECORATOR_MIDDLEWARE_MISMATCH":
                ev = f["evidence"]
                p = policies[f["route"]]
                assert "decorator" in ev, f"Missing 'decorator' in evidence for {f['route']}"
                assert "middleware_enforced" in ev, f"Missing 'middleware_enforced' in evidence for {f['route']}"
                assert ev["decorator"] == p["decorator"], (
                    f"{f['route']}: evidence decorator={ev['decorator']!r} but policy has {p['decorator']!r}"
                )
                assert ev["middleware_enforced"] == p["middleware_enforced"], (
                    f"{f['route']}: evidence middleware_enforced={ev['middleware_enforced']} but policy has {p['middleware_enforced']}"
                )

    def test_evidence_scope_not_checked_complete(self):
        """Verify SCOPE_NOT_CHECKED evidence includes jwt_valid=true, scope_checked=false, and exact observed_count matching logs."""
        logs = _load_logs()
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "SCOPE_NOT_CHECKED":
                ev = f["evidence"]
                assert "jwt_valid" in ev and ev["jwt_valid"] is True, (
                    f"SCOPE_NOT_CHECKED evidence for {f['route']} must have jwt_valid=true"
                )
                assert "scope_checked" in ev and ev["scope_checked"] is False, (
                    f"SCOPE_NOT_CHECKED evidence for {f['route']} must have scope_checked=false"
                )
                assert "observed_count" in ev, f"Missing 'observed_count' in evidence for {f['route']}"
                expected_count = sum(
                    1 for log in logs
                    if log["route"] == f["route"] and log["jwt_valid"] and not log["scope_checked"]
                )
                assert ev["observed_count"] == expected_count, (
                    f"{f['route']}: observed_count={ev['observed_count']} but logs show {expected_count} entries"
                )
                assert "affected_subs" in ev, f"Missing 'affected_subs' in SCOPE_NOT_CHECKED evidence for {f['route']}"
                expected_subs = sorted({
                    log["claims"]["sub"] for log in logs
                    if log["route"] == f["route"] and log["jwt_valid"] and not log["scope_checked"]
                })
                assert ev["affected_subs"] == expected_subs, (
                    f"{f['route']}: affected_subs={ev['affected_subs']} but expected {expected_subs}"
                )

    def test_evidence_role_not_validated_contains_non_admin_count(self):
        """Verify ROLE_NOT_VALIDATED evidence includes non_admin_count matching the actual log count of non-admin entries."""
        logs = _load_logs()
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "ROLE_NOT_VALIDATED":
                ev = f["evidence"]
                assert "non_admin_count" in ev, f"Missing 'non_admin_count' in evidence for {f['route']}"
                expected_count = sum(
                    1 for log in logs
                    if log["route"] == f["route"]
                    and log["jwt_valid"]
                    and not log["scope_checked"]
                    and log.get("claims", {}).get("role") != "admin"
                )
                assert ev["non_admin_count"] == expected_count, (
                    f"{f['route']}: non_admin_count={ev['non_admin_count']} but logs show {expected_count} entries"
                )
                assert "non_admin_subs" in ev, f"Missing 'non_admin_subs' in ROLE_NOT_VALIDATED evidence for {f['route']}"
                expected_subs = sorted({
                    log["claims"]["sub"] for log in logs
                    if log["route"] == f["route"]
                    and log["jwt_valid"]
                    and not log["scope_checked"]
                    and log.get("claims", {}).get("role") != "admin"
                })
                assert ev["non_admin_subs"] == expected_subs, (
                    f"{f['route']}: non_admin_subs={ev['non_admin_subs']} but expected {expected_subs}"
                )

    def test_evidence_cascading_bypass_contains_upstream_routes(self):
        """Verify CASCADING_BYPASS evidence includes upstream_mismatch_routes as a non-empty sorted list."""
        policies = {p["route"]: p for p in _load_policies()}
        route_calls = _load_route_calls()
        findings = _load_findings()

        mismatch_routes = {
            r for r, p in policies.items()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        }
        for f in findings:
            if f["finding_type"] == "CASCADING_BYPASS":
                ev = f["evidence"]
                assert "upstream_mismatch_routes" in ev, (
                    f"CASCADING_BYPASS evidence for {f['route']} must include 'upstream_mismatch_routes'"
                )
                upstreams = ev["upstream_mismatch_routes"]
                assert isinstance(upstreams, list) and len(upstreams) > 0, (
                    f"{f['route']}: upstream_mismatch_routes must be a non-empty list"
                )
                assert upstreams == sorted(upstreams), (
                    f"{f['route']}: upstream_mismatch_routes must be sorted alphabetically"
                )
                for upstream in upstreams:
                    assert upstream in mismatch_routes, (
                        f"{f['route']}: upstream {upstream} is not a DECORATOR_MIDDLEWARE_MISMATCH route"
                    )
                    assert f["route"] in route_calls.get(upstream, []), (
                        f"{f['route']}: upstream {upstream} does not call this route in route_calls.json"
                    )
                assert "upstream_mismatch_types" in ev, (
                    f"CASCADING_BYPASS evidence for {f['route']} must include 'upstream_mismatch_types'"
                )
                mismatch_types = ev["upstream_mismatch_types"]
                assert isinstance(mismatch_types, dict), (
                    f"{f['route']}: upstream_mismatch_types must be an object"
                )
                assert set(mismatch_types.keys()) == set(upstreams), (
                    f"{f['route']}: upstream_mismatch_types keys must match upstream_mismatch_routes"
                )
                for upstream, mtype in mismatch_types.items():
                    p = policies[upstream]
                    if p["decorator"] != "none" and not p["middleware_enforced"]:
                        expected_type = "auth_not_enforced"
                    else:
                        expected_type = "shadow_enforcement"
                    assert mtype == expected_type, (
                        f"{f['route']}: upstream_mismatch_types[{upstream!r}]={mtype!r} but expected {expected_type!r}"
                    )

    def test_evidence_unenforced_complete(self):
        """Verify UNENFORCED_SENSITIVE_ROUTE evidence includes decorator='none', middleware_enforced=false, and path_pattern."""
        findings = _load_findings()
        for f in findings:
            if f["finding_type"] == "UNENFORCED_SENSITIVE_ROUTE":
                ev = f["evidence"]
                assert "decorator" in ev and ev["decorator"] == "none", (
                    f"UNENFORCED_SENSITIVE_ROUTE evidence for {f['route']} must have decorator='none'"
                )
                assert "middleware_enforced" in ev and ev["middleware_enforced"] is False, (
                    f"UNENFORCED_SENSITIVE_ROUTE evidence for {f['route']} must have middleware_enforced=false"
                )
                assert "path_pattern" in ev and ev["path_pattern"] in ("/admin/*", "/internal/*"), (
                    f"path_pattern must be '/admin/*' or '/internal/*', got {ev.get('path_pattern')!r}"
                )

    def test_no_duplicate_findings(self):
        """Verify no (route, finding_type) pair appears more than once in findings.json."""
        findings = _load_findings()
        seen = {}
        for f in findings:
            key = (f["route"], f["finding_type"])
            assert key not in seen, f"Duplicate finding: {key}"
            seen[key] = True

    def test_total_finding_count(self):
        """Verify the total number of findings matches the independently computed expected count."""
        policies = {p["route"]: p for p in _load_policies()}
        logs = _load_logs()
        route_calls = _load_route_calls()

        mismatch_count = sum(
            1
            for p in policies.values()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        )
        mismatch_routes = {
            r for r, p in policies.items()
            if (p["decorator"] != "none" and not p["middleware_enforced"])
            or (p["decorator"] == "none" and p["middleware_enforced"])
        }
        scope_routes = {
            log["route"]
            for log in logs
            if log["jwt_valid"]
            and not log["scope_checked"]
            and policies.get(log["route"], {}).get("decorator", "none") != "none"
            and policies.get(log["route"], {}).get("middleware_enforced", False)
        }
        rnv_routes = {
            log["route"]
            for log in logs
            if log["jwt_valid"]
            and not log["scope_checked"]
            and log.get("claims", {}).get("role") != "admin"
            and policies.get(log["route"], {}).get("decorator") == "require_admin"
            and policies.get(log["route"], {}).get("middleware_enforced", False)
        }
        cascading_routes = {
            downstream
            for upstream in mismatch_routes
            for downstream in route_calls.get(upstream, [])
            if downstream in scope_routes
        }
        psb_routes = {
            r for r, p in policies.items()
            if p["decorator"] != "none"
            and p["middleware_enforced"]
            and any(log["route"] == r and log["jwt_valid"] and not log["scope_checked"] for log in logs)
            and all(
                log.get("claims", {}).get("role") == "admin"
                for log in logs
                if log["route"] == r and log["jwt_valid"] and not log["scope_checked"]
            )
        }
        unenforced_count = sum(
            1
            for r, p in policies.items()
            if p["decorator"] == "none"
            and not p["middleware_enforced"]
            and (r.startswith("/admin/") or r.startswith("/internal/"))
        )
        expected_total = mismatch_count + len(scope_routes) + len(rnv_routes) + len(cascading_routes) + len(psb_routes) + unenforced_count

        findings = _load_findings()
        assert len(findings) == expected_total, (
            f"Expected {expected_total} findings, got {len(findings)}"
        )
