# LiteLLM gateway latency — root cause and open items

**Status: investigation CLOSED 2026-08-09.** Root cause localized to the gateway process.
No client-side fix exists. All remaining work is a ticket to the gateway owners.

## Root cause

`ete-litellm.ai-models.vpc-int.res.ibm.com` stalls **5–57 s on ~30 % of requests**, independent
of anything client-side. Healthy floor is **0.72–1.0 s** total round trip, of which 0.68 s is
DNS+TCP+TLS — so a well proxy adds only ~50–90 ms. Stalls are bimodal, not gradual load.

Two proofs that it is the proxy and not any upstream provider:

1. `/health/liveliness` — returns a static string, calls no model, touches no database —
   stalled **6.44 s**. Nothing upstream can explain that.
2. A one-token `"hi"` (`max_tokens=1`) stalls on *every* provider the gateway fronts:
   GCP `gemini-2.5-flash` **22.8 s**, Bedrock `aws/claude-haiku-4-5` **57.2 s**,
   Azure `azure/gpt-5.5` **9.6 s**. A single token is a sub-second operation everywhere.

Mechanism: **per-request queueing for a worker slot.** ALPN negotiates nothing (HTTP/1.1 only),
so every in-flight request needs its own connection and its own uvicorn worker. Two connections
to the same host at the same instant disagree (13.3 s vs 2.8 s), and a *second* concurrent
connection is systematically worst — 4/12 slow vs 1/12. Bad periods are moments when this
shared multi-tenant gateway's users collectively saturate those slots. Both LB backends
(`9.47.167.232`, `9.47.168.37`) stall together in the same round, so it is not one bad host.
Infra: `server: uvicorn`, `x-litellm-version: 1.85.5`, one deployment per model group, no
fallbacks; Opus routes to Bedrock (`msg_bdrk_…`) while CC logs `dispatching to firstParty`.

Client side: real Claude Code turns measured **11–82 s** to first byte with **zero** retries in
900+ log lines — one request per turn, then a wait. Any retry is inside the gateway.

## Refuted with data — do not re-run any of these

Stream buffering (1024-token output gave TTFB 2.6 s / total 6.7 s); client-side retries (zero
log lines); prefill cost (53 393 input tokens round-tripped in 5.15 s, *faster* than `"hi"`);
broken prompt caching (caching works — 13 247 tokens written then read back); thinking budget
(flat across a 10× sweep); proxy-side token counting (50 k bodies were *faster* and steadier
than tiny ones, ratio 0.6×); pooled-connection death (looked clean at n=4, vanished at n=15 —
a warm connection stalled 11.5 s); one-bad-backend (both equally sick); Postgres (`liveliness`,
which never touches it, stalls while `readiness` does not).

## No client-side mitigation exists

Model choice, context size, connection reuse and cutting background calls are all refuted or
negligible (only 2 of 32 requests in a real session were non-essential). Both timeout knobs are
dead, verified by experiment:

- `CLAUDE_BYTE_STREAM_IDLE_TIMEOUT_MS` **ignores pre-first-byte silence** — an 800 ms setting sat
  through 13 197 ms of silence without firing. The stall *is* that silence.
- `API_TIMEOUT_MS` is a **total** request cap. At 4000 ms a long generation took **236 s across
  13 requests and then failed**, versus 9.3 s and success unset. Catching a 50 s stall needs
  T < 50 s, but legitimate turns need ~100 s (`api=99182ms` observed) — the ranges overlap, so
  no safe value exists. Leave both unset; `API_TIMEOUT_MS` ≥180 s only as a hang-guard.

Aborting on **time-to-first-byte** would work (p50 unchanged 2.1 s, p90 16.1→10.3 s,
p99 47.9→**23.8 s** at an 8 s threshold, retries billed as cache reads so no token doubling),
but no knob watches TTFB. Only a local reverse proxy could — see Declined.

## Artifacts

- `~/gateway-triage/gateway-incident.py` — **the one thing to run.** No flags, ~3 min, writes a
  single `gateway-incident-<UTC>.md` to send. Health probes call no model; completions are
  `max_tokens=1`; nothing hedged. Run it **during a bad window** — a mild window gives weak
  numbers (a 19:17 run got 2/33 over 5 s, worst 8.3 s).
- `~/gateway-triage/evidence/claude-code-real-turn-ttfb.txt` — 49 real CC turns with per-turn
  TTFB (11–82 s) plus the zero-retries finding. The stronger attachment: real turns beat
  synthetic probes. Distilled from the `--debug` log, which was then deleted — the full log
  held local paths and tool-permission rules that must not go to the gateway owners.

## Open items

1. **Send the ticket.** Run `gateway-incident.py` in a bad window; attach its report plus the
   real-turn evidence. Asks for the owners: worker/replica count vs offered concurrency; whether
   the pods are CPU-throttled (event-loop starvation); enable HTTP/2. De-emphasize Postgres.
2. **Second defect for the same ticket:** `generate_session_title` 400s with
   `output_config.format: Extra inputs are not permitted`, so Claude Code auto-naming can never
   work through this proxy — sessions must be renamed explicitly.
3. **`fetch` MCP server is broken** (unrelated, found in passing): `ImportError: cannot import
   name 'McpError' from 'mcp.shared.exceptions'. Did you mean: 'MCPError'?` under python3.14
   from the uv cache. Needs a pinned working pair; not done.
4. **Carried from the round-1 DNS triage:** the `hosts:` nsswitch fix (staged at
   `/tmp/nsswitch.conf.proposed`, recreate if cleaned — must drop `mdns4_minimal` *and*
   `[NOTFOUND=return]` together, since leaving the latter attaches it to `files` and breaks all
   DNS), and `~/.wslconfig` needs `wsl --shutdown` (stops docker and all containers, so only
   with no kind cluster up).

## Declined — do not re-propose

- **Hedging / parallel duplicate requests.** Rejected: doubles token spend on every request.
- **Local TTFB-abort reverse proxy.** Deferred 2026-08-09 ("no proxy for now"). It is the only
  way to realize the p99 47.9→23.8 s gain and needs no token doubling (sequential re-issue,
  retry billed as a cache read), so it is **shelved, not dead**.
