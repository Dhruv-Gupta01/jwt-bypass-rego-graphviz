package attack_graph

import future.keywords.contains
import future.keywords.if

# Routes that have at least one finding — these are bypass entry points
finding_routes contains route if {
	f := data.findings[_]
	route := f.route
}

# Reachability via bounded fixpoint — OPA forbids recursive rules so we unroll 3 hops
reachable_0 contains r if {
	finding_routes[r]
}

reachable_1 contains r if {
	reachable_0[r]
}

reachable_1 contains r if {
	reachable_0[s]
	r := data.route_calls[s][_]
}

reachable_2 contains r if {
	reachable_1[r]
}

reachable_2 contains r if {
	reachable_1[s]
	r := data.route_calls[s][_]
}

reachable_3 contains r if {
	reachable_2[r]
}

reachable_3 contains r if {
	reachable_2[s]
	r := data.route_calls[s][_]
}

nodes := reachable_3

edges contains [src, dst] if {
	reachable_3[src]
	dst := data.route_calls[src][_]
	reachable_3[dst]
}

# Per-source reachability — tracks which finding routes (fr) can reach each destination.
# This is a nested dict structure (different from the global fixpoint above).
reachable_from_0[fr][fr] := true if {
	finding_routes[fr]
}

reachable_from_1[fr][dst] := true if {
	reachable_from_0[fr][dst]
}

reachable_from_1[fr][dst] := true if {
	reachable_from_0[fr][src]
	dst := data.route_calls[src][_]
}

reachable_from_2[fr][dst] := true if {
	reachable_from_1[fr][dst]
}

reachable_from_2[fr][dst] := true if {
	reachable_from_1[fr][src]
	dst := data.route_calls[src][_]
}

reachable_from_3[fr][dst] := true if {
	reachable_from_2[fr][dst]
}

reachable_from_3[fr][dst] := true if {
	reachable_from_2[fr][src]
	dst := data.route_calls[src][_]
}

# Exposure count: number of distinct finding routes that can reach each node within 3 hops
exposure[node] := count({fr | reachable_from_3[fr][node]}) if {
	nodes[node]
}
