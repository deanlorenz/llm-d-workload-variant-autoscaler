# Tool authoring

### convention: tool-explicit-paths
description: Analysis/driver scripts take explicit --in/--out paths, no discovery; one invocation per unit of work; hard error on a missing path; output lands next to the data it describes.
scope: anyone writing an analysis or driver script
trigger: adding a driver or wrapper for an analysis pipeline
status: active
origin: feedback_tools_take_explicit_paths.md

Dean rejects path discovery in analysis tools — the caller already knows where its data is.
Concrete incident: a proposed driver script took a single experiment directory and *discovered*
the results dir and controller log inside it; Dean's correction: "why need discovery. The
benchmark who calls viz knows where the results are. Could be many run_ids."

**The shape wanted:** explicit input and output flags, one invocation per unit of work (per run
id, not per experiment), a hard error on a missing path, and the output directory the only thing
written. Analysis artifacts land **next to the data they describe** — not in the tool's own
repo-local output directory. Dean's own framing: *"I want to run a benchmark and call the viz
tools as a last step after I copy the results over. I want to get the full reports, graphs, HTML
right there with my results."*

**Why:** a discovery step guesses at something the caller already knows for certain, so it can
only add a failure mode (wrong run id silently picked, ambiguity when there are several) without
adding capability. An analysis artifact separated from its inputs stops being self-describing.

**How to apply:** when adding a driver or wrapper for an analysis pipeline, make it a thin
argument-forwarder — no globbing for inputs, no inferring one path from another, no defaults that
resolve to a repo-relative directory. Write the call-site contract into the plan before coding it.
