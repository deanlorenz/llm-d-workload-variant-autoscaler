# results/ — published bundles

Nothing here yet. This file exists to hold the directory open: git cannot track an
empty directory, so a `results/` that is "tracked and empty" is not a state git can
represent — it is just an absent directory, which is what this was until 2026-08-07.

## What lands here

One directory per published run:

```
results/<YYYYMMDD>-<label>/
  bundle.json        # the extract — complete input to every panel
  coverage.json      # which panels and calibrations this run supports
  provenance.json    # run id, harness, model, namespace, cluster,
                     #   extractor git sha, extraction time
  panels.png         # rendered output, so a result is browsable without
                     #   running anything
```

A published result measures 300–400 kB, so this directory stays small even at
tens of runs. That is the whole reason results live in a directory on this branch
rather than in a separate orphan branch — one clone gets you the tools *and* the
results, with no second fetch.

## Rules

- **Bundles only, never raw.** Nothing over 20 MB, no `metrics/raw/`, no
  per-request source files.
- **No prompt or response text, in any form.** This is a rule, not a size budget:
  guidellm embeds the full prompt in every record, and on a real workload that
  could be sensitive. The extractor never copies it; do not add it by hand.
- **`provenance.json` is mandatory.** A bundle whose extractor version is unknown
  is not reusable — the parsing rules have already changed once.
- **Append-only.** Never rewrite an existing result directory; a re-extract lands
  as a new dated one.
- **Publishing never pushes.** Staging and validation are the default, the commit
  needs a second explicit flag, and the push is a separate human action.

## Publishing is not wired up yet

`publish_result.sh` still targets the retired `viz-results` orphan branch, so its
`--commit` path would recreate a branch that was deliberately archived. Its
*validation* half is good and worth keeping. Until that is fixed, add a result by
hand: create the dated directory, copy the four files in, and commit.

Full reasoning: [`../real-trace-viz-plan.md`](../real-trace-viz-plan.md) §15.
