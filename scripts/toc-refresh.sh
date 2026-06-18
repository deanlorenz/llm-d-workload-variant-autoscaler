#!/usr/bin/env bash
# toc-refresh.sh — refresh a plan document's TOC and back-to-TOC links.
#
# Usage: plans/scripts/toc-refresh.sh <plan-file.md>
#
# Does three things in order:
#   1. Adds missing [↑ TOC](#toc) links at the end of sections (see rules below)
#   2. Regenerates ## TOC with GitHub-style anchors and L<start>:<end> ranges
#   3. Re-runs step 2 once to stabilize line numbers after TOC size change
#
# Back-to-TOC placement rules:
#   - Added before a sibling or parent header (same or shallower depth)
#   - NOT added between a section intro and its first child sub-section
#   - Placed after the last non-blank, non-separator content line of the section
#   - Idempotent: if [↑ TOC](#toc) already exists in the section, nothing is added
#
# Anchor algorithm (matches GitHub-flavored markdown):
#   lowercase → strip non-(alnum|space|hyphen) → each space to hyphen (no collapsing)
#   "Type 1 — Foo" → "type-1--foo"   (em dash leaves two spaces → double hyphen)

set -euo pipefail

FILE="${1:?Usage: toc-refresh.sh <plan-file.md>}"
[[ -f "$FILE" ]] || { echo "Error: file not found: $FILE" >&2; exit 1; }

# ── GitHub-style anchor ───────────────────────────────────────────────────────

anchor() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9 -]//g' \
    | tr ' ' '-'
}

# ── locate ## TOC and first ## content section ────────────────────────────────

find_toc_line() {
  grep -n "^## TOC" "$1" | head -1 | cut -d: -f1
}

find_content_start() {
  local f="$1" toc_line="$2"
  awk -v toc="$toc_line" 'NR > toc && /^## / { print NR; exit }' "$f"
}

# ── step 1: add missing [↑ TOC](#toc) links ──────────────────────────────────
#
# Processes the content area (after ## TOC) section by section.
# Flushes each section's buffer when the next header arrives:
#   - Same or shallower depth (sibling/parent): flush with back-to-toc if missing
#   - Deeper depth (child): flush as-is (intro content, link not appropriate here)
# Last section is always flushed with back-to-toc.

add_backtoc() {
  local f="$1" cs="$2"
  local tmp
  tmp=$(mktemp)
  awk -v start="$cs" '
    BEGIN { sec=0; buf_n=0; cur_depth=0; in_code=0 }

    NR < start { print; next }
    /^[[:space:]]*```/ { in_code = !in_code }

    !in_code && /^#{2,} / {
      # Compute depth of this new header (1 = ##, 2 = ###, ...)
      new_d = 0; s = $0
      while (substr(s,1,1) == "#") { new_d++; s = substr(s,2) }
      new_d -= 1

      if (sec > 0) {
        need_bt = (new_d <= cur_depth)  # sibling or parent: add link
        has_bt  = 0
        for (i = 1; i <= buf_n; i++)
          if (buf[i] ~ /^\[↑ TOC\]/) { has_bt = 1; break }

        if (need_bt && !has_bt) {
          # Insertion point: just after last non-blank, non-"---" line
          ins = buf_n + 1
          for (i = buf_n; i >= 1; i--) {
            if (buf[i] !~ /^[[:space:]]*$/ && buf[i] !~ /^---$/) {
              ins = i + 1; break
            }
          }
          for (i = 1; i < ins; i++) print buf[i]
          print ""
          print "[↑ TOC](#toc)"
          for (i = ins; i <= buf_n; i++) print buf[i]
        } else {
          for (i = 1; i <= buf_n; i++) print buf[i]
        }
        delete buf; buf_n = 0
      }

      cur_depth = new_d
      sec++
      buf[++buf_n] = $0
      next
    }

    { buf[++buf_n] = $0; next }

    END {
      if (sec == 0) { for (i = 1; i <= buf_n; i++) print buf[i]; exit }
      # Last section always gets a back-to-toc
      has_bt = 0
      for (i = 1; i <= buf_n; i++)
        if (buf[i] ~ /^\[↑ TOC\]/) { has_bt = 1; break }
      if (!has_bt) {
        ins = buf_n + 1
        for (i = buf_n; i >= 1; i--) {
          if (buf[i] !~ /^[[:space:]]*$/ && buf[i] !~ /^---$/) {
            ins = i + 1; break
          }
        }
        for (i = 1; i < ins; i++) print buf[i]
        print ""
        print "[↑ TOC](#toc)"
        for (i = ins; i <= buf_n; i++) print buf[i]
      } else {
        for (i = 1; i <= buf_n; i++) print buf[i]
      }
    }
  ' "$f" > "$tmp"
  mv "$tmp" "$f"
}

# ── step 2: regenerate ## TOC block ──────────────────────────────────────────

regen_toc() {
  local f="$1"
  local toc_line cs total
  toc_line=$(find_toc_line "$f")
  [[ -n "$toc_line" ]] || { echo "Error: no '## TOC' in $f" >&2; return 1; }
  cs=$(find_content_start "$f" "$toc_line")
  [[ -n "$cs" ]] || { echo "Error: no content ## after ## TOC" >&2; return 1; }
  total=$(wc -l < "$f")

  mapfile -t HDRS < <(awk -v start="$cs" '
    NR < start { next }
    /^[[:space:]]*```/ { in_code = !in_code; next }
    in_code { next }
    /^#{2,} / {
      depth = 0; s = $0
      while (substr(s,1,1) == "#") { depth++; s = substr(s,2) }
      sub(/^[[:space:]]+/, "", s)
      print NR "\t" (depth - 1) "\t" s
    }
  ' "$f")

  local n=${#HDRS[@]}
  (( n > 0 )) || return 0

  local new_toc=() lnum depth title end indent nlnum ndepth
  for (( i=0; i<n; i++ )); do
    IFS=$'\t' read -r lnum depth title <<< "${HDRS[$i]}"
    end=$total
    for (( j=i+1; j<n; j++ )); do
      IFS=$'\t' read -r nlnum ndepth _ <<< "${HDRS[$j]}"
      if (( ndepth <= depth )); then end=$(( nlnum - 1 )); break; fi
    done
    indent=''
    for (( d=1; d<depth; d++ )); do indent="  $indent"; done
    new_toc+=("${indent}- [${title}](#$(anchor "$title")) L${lnum}:${end}")
  done

  local tmp
  tmp=$(mktemp)
  {
    sed -n "1,${toc_line}p" "$f"
    echo ""
    printf '%s\n' "${new_toc[@]}"
    echo ""
    tail -n "+${cs}" "$f"
  } > "$tmp"
  mv "$tmp" "$f"
}

# ── main ──────────────────────────────────────────────────────────────────────

TOC_LINE=$(find_toc_line "$FILE")
[[ -n "$TOC_LINE" ]] || { echo "Error: no '## TOC' section in $FILE" >&2; exit 1; }
CS=$(find_content_start "$FILE" "$TOC_LINE")
[[ -n "$CS" ]] || { echo "Error: no content section after ## TOC" >&2; exit 1; }

add_backtoc "$FILE" "$CS"
regen_toc "$FILE"
regen_toc "$FILE"  # second pass: stabilizes after TOC line-count change

n=$(grep -c "^## " "$FILE" || true)
echo "Done: ${n} top-level sections → ${FILE}"
