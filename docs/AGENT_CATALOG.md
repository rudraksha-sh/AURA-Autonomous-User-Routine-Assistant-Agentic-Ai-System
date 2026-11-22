# Agent catalog

| Agent | Inputs and outputs | Boundary |
| --- | --- | --- |
| Supervisor | Typed intent to graph route and permission identifiers | Fixed, bounded paths |
| Context | Authenticated tenant and goal ID to owned goal with `aura.goal` provenance | Graph context is local |
| Planner | Owned goal and task count to validated estimates, deadlines and priorities | Rule-based in graph. Existing AI route retains OpenRouter. |
| Scheduler | Proposal, working preferences and local reservations to schedule estimate | Capacity, deadlines, working hours and breaks |
| Memory | Explicit planning preferences to inspect, correct, export and reset | No implicit fact extraction |
| Simulation | Existing what-if input to baseline, scenario and assumptions | Deterministic and read-only |
| Execution | Reviewed proposal or valid grant to local task creation | Allowlisted, tenant-bound operation |
| Verification | Task IDs to owned task evidence | Can recheck after external edits to local data |
| Replanning | Prior owned plan and current goal to comparison and overdue count | Explicit review required |
| Intelligence | Schedule estimate to remaining minutes and feasibility flag | No predictive probabilities |

Agent functions can be called independently. Graph nodes adapt outputs into typed state. Search server logs or use the audit endpoint with the run UUID to inspect agent names, outcomes and timestamps.
