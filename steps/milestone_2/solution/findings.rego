package jwt_bypass

import future.keywords.contains
import future.keywords.if

policies := data.route_policies

logs := data.access_logs

# DECORATOR_MIDDLEWARE_MISMATCH — decorator declares auth but middleware does not enforce it
findings contains finding if {
	policy := policies[_]
	policy.decorator != "none"
	policy.middleware_enforced == false
	finding := {
		"route": policy.route,
		"finding_type": "DECORATOR_MIDDLEWARE_MISMATCH",
		"evidence": {
			"decorator": policy.decorator,
			"middleware_enforced": false,
		},
	}
}

# DECORATOR_MIDDLEWARE_MISMATCH — no decorator but middleware enforces (shadow enforcement)
findings contains finding if {
	policy := policies[_]
	policy.decorator == "none"
	policy.middleware_enforced == true
	finding := {
		"route": policy.route,
		"finding_type": "DECORATOR_MIDDLEWARE_MISMATCH",
		"evidence": {
			"decorator": "none",
			"middleware_enforced": true,
		},
	}
}

# Count log entries per route where JWT is valid but scope was not checked
scope_not_checked_count[route] := cnt if {
	route := policies[_].route
	cnt := count({i | logs[i].route == route; logs[i].jwt_valid == true; logs[i].scope_checked == false})
	cnt > 0
}

# SCOPE_NOT_CHECKED — route requires auth AND middleware enforces it, but logs show scope was never verified
# Routes where middleware_enforced=false already have DECORATOR_MIDDLEWARE_MISMATCH; don't double-count.
findings contains finding if {
	policy := policies[_]
	policy.decorator != "none"
	policy.middleware_enforced == true
	cnt := scope_not_checked_count[policy.route]
	affected_subs := sort({sub | logs[i].route == policy.route; logs[i].jwt_valid == true; logs[i].scope_checked == false; sub := logs[i].claims.sub})
	finding := {
		"route": policy.route,
		"finding_type": "SCOPE_NOT_CHECKED",
		"evidence": {
			"jwt_valid": true,
			"scope_checked": false,
			"observed_count": cnt,
			"affected_subs": affected_subs,
		},
	}
}

# Count log entries per route where require_admin route sees a non-admin role with scope unchecked
role_not_validated_count[route] := cnt if {
	route := policies[_].route
	cnt := count({i | logs[i].route == route; logs[i].jwt_valid == true; logs[i].scope_checked == false; logs[i].claims.role != "admin"})
	cnt > 0
}

# ROLE_NOT_VALIDATED — require_admin route with scope unchecked AND non-admin role in token
findings contains finding if {
	policy := policies[_]
	policy.decorator == "require_admin"
	policy.middleware_enforced == true
	cnt := role_not_validated_count[policy.route]
	non_admin_subs := sort({sub | logs[i].route == policy.route; logs[i].jwt_valid == true; logs[i].scope_checked == false; logs[i].claims.role != "admin"; sub := logs[i].claims.sub})
	finding := {
		"route": policy.route,
		"finding_type": "ROLE_NOT_VALIDATED",
		"evidence": {
			"non_admin_count": cnt,
			"non_admin_subs": non_admin_subs,
		},
	}
}

# Count log entries per route where scope is skipped but role IS admin
privileged_scope_bypass_count[route] := cnt if {
	route := policies[_].route
	cnt := count({i | logs[i].route == route; logs[i].jwt_valid == true; logs[i].scope_checked == false})
	cnt > 0
}

# PRIVILEGED_SCOPE_BYPASS — scope is silently skipped, but exclusively by admin tokens.
# Mutually exclusive with ROLE_NOT_VALIDATED: if any non-admin token bypasses scope,
# that is ROLE_NOT_VALIDATED, not PRIVILEGED_SCOPE_BYPASS.
findings contains finding if {
	policy := policies[_]
	policy.decorator != "none"
	policy.middleware_enforced == true
	cnt := privileged_scope_bypass_count[policy.route]
	# All scope-unchecked entries have role=admin (no non-admin bypass)
	non_admin := count({i | logs[i].route == policy.route; logs[i].jwt_valid == true; logs[i].scope_checked == false; logs[i].claims.role != "admin"})
	non_admin == 0
	finding := {
		"route": policy.route,
		"finding_type": "PRIVILEGED_SCOPE_BYPASS",
		"evidence": {
			"admin_bypass_count": cnt,
		},
	}
}

# Helper: classify a DECORATOR_MIDDLEWARE_MISMATCH route by its sub-type
upstream_type(route) := "auth_not_enforced" if {
	some j
	policies[j].route == route
	policies[j].decorator != "none"
	policies[j].middleware_enforced == false
}

upstream_type(route) := "shadow_enforcement" if {
	some j
	policies[j].route == route
	policies[j].decorator == "none"
	policies[j].middleware_enforced == true
}

# Intermediate sets used by CASCADING_BYPASS — derived from policies, not from `findings`,
# to avoid a circular reference that OPA would reject.
mismatch_routes contains route if {
	policy := policies[_]
	policy.decorator != "none"
	policy.middleware_enforced == false
	route := policy.route
}

mismatch_routes contains route if {
	policy := policies[_]
	policy.decorator == "none"
	policy.middleware_enforced == true
	route := policy.route
}

scope_not_checked_routes contains route if {
	policy := policies[_]
	policy.decorator != "none"
	policy.middleware_enforced == true
	scope_not_checked_count[route]
}

# Aggregate all mismatch upstreams per downstream scope-not-checked route
cascading_bypass_upstreams[downstream] := sorted_upstreams if {
	downstream := scope_not_checked_routes[_]
	upstreams := {upstream | mismatch_routes[upstream]; data.route_calls[upstream][_] == downstream}
	count(upstreams) > 0
	sorted_upstreams := sort(upstreams)
}

# CASCADING_BYPASS — a SCOPE_NOT_CHECKED route is directly reachable from a DECORATOR_MIDDLEWARE_MISMATCH
# route via route_calls. The mismatch allows bypassing auth, then the downstream skips scope validation.
findings contains finding if {
	cascading_bypass_upstreams[downstream]
	upstreams := cascading_bypass_upstreams[downstream]
	mismatch_types := {u: upstream_type(u) | u := upstreams[_]}
	finding := {
		"route": downstream,
		"finding_type": "CASCADING_BYPASS",
		"evidence": {
			"upstream_mismatch_routes": upstreams,
			"upstream_mismatch_types": mismatch_types,
		},
	}
}

# UNENFORCED_SENSITIVE_ROUTE — /admin/* path with no decorator and no middleware enforcement
findings contains finding if {
	policy := policies[_]
	policy.decorator == "none"
	policy.middleware_enforced == false
	startswith(policy.route, "/admin/")
	finding := {
		"route": policy.route,
		"finding_type": "UNENFORCED_SENSITIVE_ROUTE",
		"evidence": {
			"decorator": "none",
			"middleware_enforced": false,
			"path_pattern": "/admin/*",
		},
	}
}

# UNENFORCED_SENSITIVE_ROUTE — /internal/* path with no decorator and no middleware enforcement
findings contains finding if {
	policy := policies[_]
	policy.decorator == "none"
	policy.middleware_enforced == false
	startswith(policy.route, "/internal/")
	finding := {
		"route": policy.route,
		"finding_type": "UNENFORCED_SENSITIVE_ROUTE",
		"evidence": {
			"decorator": "none",
			"middleware_enforced": false,
			"path_pattern": "/internal/*",
		},
	}
}
