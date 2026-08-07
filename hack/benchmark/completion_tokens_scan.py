#!/usr/bin/env python3
"""
completion_tokens_scan.py — the only thing we need out of the multi-GB
per-request file, extracted where the file already is.

Why this exists
---------------
inference-perf derives `output_len` by re-tokenizing the generated text, which
with random prompts and `ignore_eos` inflates it (1.77x on the 2026-08-03
staircase) along with every output-token-derived metric. The true count is the
server's own `usage.completion_tokens`, carried per record as
`info.response_info.server_usage.completion_tokens`.

Correcting the reports needs that and nothing else: the correction rebuilds the
output-length distribution from the *sorted vector* of those values, and applies
one run-wide vector to every stage report. So 4 GB of prompts, responses and
per-token timings reduce to a flat list of integers -- about 40 KB for a
7919-request run.

That is why this runs in the pod that already mounts the results PVC, and why
the rest of the correction does not. Only the vector crosses the wire.

Design constraints (this executes inside an image we do not control)
-------------------------------------------------------------------
  * standard library only -- no yaml, no ijson, nothing to install
  * reads the file in fixed-size chunks; never json.load()s it. The existing
    per_request_plots.py does load it whole and silently OOM-skips, which is the
    failure this avoids.
  * script arrives on stdin, result leaves on stdout, progress goes to stderr:
    nothing is written inside the pod and nothing is left behind
  * no knowledge of pod names, namespaces, models or run ids

Usage
-----
  # in-pod, the intended path
  kubectl exec -i -n <ns> <pod> -c rsync -- python3 - <remote-file> \
      > server_completion_tokens.json

  # on a local copy, for validation
  python3 completion_tokens_scan.py <per_request_lifecycle_metrics.json>

Output is a JSON object, not a bare array, so a reader can tell a successful
empty scan from a truncated file:

  {"source": "...", "n": 7919, "sum": 4055321, "completion_tokens": [512, ...]}
"""

from __future__ import annotations

import json
import re
import sys

# Matched on bytes: the file is read binary so a multi-byte character in prompt
# text can never split a codepoint mid-decode.
CT_RE = re.compile(rb'"completion_tokens"\s*:\s*(\d+)')

CHUNK = 1 << 20  # 1 MiB reads: large enough to amortise syscalls, small enough
                 # that peak memory stays flat regardless of file size.

# Must exceed the longest possible single match. `"completion_tokens": ` plus a
# token count is well under 64 bytes; 4 KiB is paranoia that costs nothing.
OVERLAP = 4096


def scan(path: str, progress_every: int = 512 << 20):
    """Stream every completion_tokens value out of the file in constant memory.

    Carries a small overlap between chunks so a value straddling a read boundary
    is neither missed nor counted twice. This mirrors the logic in the fork's
    output_token_correction.py, deliberately: if the two ever disagree, the
    corrected reports and the fetched vector would silently diverge.
    """
    vals: list[int] = []
    carry = b""
    read = 0
    next_note = progress_every

    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                # Final flush: at EOF nothing can straddle, so take every match.
                for m in CT_RE.finditer(carry):
                    vals.append(int(m.group(1)))
                break

            read += len(chunk)
            data = carry + chunk
            boundary = len(data) - OVERLAP

            for m in CT_RE.finditer(data):
                if m.end() <= len(data) - OVERLAP:
                    vals.append(int(m.group(1)))
                else:
                    # First match reaching into the overlap tail: defer it, and
                    # everything after it, by carrying from its start. Matches
                    # are position-ordered, so the rest lie further right.
                    boundary = m.start()
                    break

            carry = data[boundary:]

            if read >= next_note:
                print(
                    f"  scanned {read / 1e9:.1f} GB, {len(vals)} values",
                    file=sys.stderr,
                )
                next_note += progress_every

    return vals, read


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: completion_tokens_scan.py <per-request-file>",
            file=sys.stderr,
        )
        return 2

    path = sys.argv[1]
    try:
        vals, read = scan(path)
    except FileNotFoundError:
        print(f"error: no such file: {path}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: could not read {path}: {exc}", file=sys.stderr)
        return 1

    if not vals:
        # An empty result is reported rather than written as a valid-looking
        # empty vector: downstream, "no values" and "zero output tokens" must
        # not be confusable.
        print(
            f"error: no completion_tokens found in {path} "
            f"({read / 1e9:.2f} GB read) -- wrong file, or a harness that does "
            f"not record server usage",
            file=sys.stderr,
        )
        return 1

    json.dump(
        {
            "source": path,
            "field": "info.response_info.server_usage.completion_tokens",
            "bytes_scanned": read,
            "n": len(vals),
            "sum": sum(vals),
            "mean": sum(vals) / len(vals),
            "completion_tokens": vals,
        },
        sys.stdout,
        separators=(",", ":"),
    )
    print(
        f"  {len(vals)} values, mean {sum(vals) / len(vals):.1f}, "
        f"from {read / 1e9:.2f} GB",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
