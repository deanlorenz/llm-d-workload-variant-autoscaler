#!/usr/bin/env bash
# toc-refresh.sh — regenerate the ## TOC block of a plan document.
#
# Usage: plans/scripts/toc-refresh.sh <plan-file.md>
#
# Rewrites the ## TOC section with:
#   - markdown links using GitHub-style anchors
#   - line ranges L<start>:<end> for each section (inclusive, 1-based)
#   - indentation matching header depth (2 spaces per level)
#
# Anchor algorithm: lowercase → strip non-(alnum|space|hyphen) → spaces to hyphens.
# Matches GitHub-flavored markdown anchor generation.
#
# Convention: run before every handover from planner to coder.
# The script is idempotent.

set -euo pipefail

FILE="${1:?Usage: toc-refresh.sh <plan-file.md>}"
[[ -f "$FILE" ]] || { echo "Error: file not found: $FILE" >&2; exit 1; }

# ── locate ## TOC and first ## content section after it ──────────────────────

TOC_LINE=$(grep -n "^## TOC" "$FILE" | head -1 | cut -d: -f1)
[[ -n "$TOC_LINE" ]] || { echo "Error: no '## TOC' section in $FILE" >&2; exit 1; }

CONTENT_START=$(awk -v toc="$TOC_LINE" 'NR > toc && /^## / { print NR; exit }' "$FILE")
[[ -n "$CONTENT_START" ]] || { echo "Error: no content section (##) found after ## TOC" >&2; exit 1; }

TOTAL=$(wc -l < "$FILE")

# ── collect headers in content area, skipping fenced code blocks ─────────────
# Output: TAB-separated: linenum TAB depth TAB title
# depth 1 = ##, depth 2 = ###, etc.

mapfile -t HDRS < <(awk -v start="$CONTENT_START" '
  NR < start { next }
  /^[[:space:]]*```/ { in_code = !in_code; next }
  in_code { next }
  /^#{2,} / {
    depth = 0; s = $0
    while (substr(s,1,1) == "#") { depth++; s = substr(s,2) }
    sub(/^[[:space:]]+/, "", s)
    print NR "\t" (depth - 1) "\t" s
  }
' "$FILE")

n=${#HDRS[@]}
(( n > 0 )) || { echo "No sections found after ## TOC — nothing to do." >&2; exit 0; }

# ── GitHub-style anchor ───────────────────────────────────────────────────────

anchor() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9 -]//g' \
    | sed 's/ \+/-/g'
}

# ── build TOC lines with line ranges ─────────────────────────────────────────

new_toc=()
for (( i=0; i<n; i++ )); do
  IFS=$'\t' read -r lnum depth title <<< "${HDRS[$i]}"

  # end line = line before next header at same or shallower depth, or EOF
  end=$TOTAL
  for (( j=i+1; j<n; j++ )); do
    IFS=$'\t' read -r nlnum ndepth _ <<< "${HDRS[$j]}"
    if (( ndepth <= depth )); then
      end=$(( nlnum - 1 ))
      break
    fi
  done

  # 2 spaces per level beyond the first
  indent=''
  for (( d=1; d<depth; d++ )); do indent="  $indent"; done

  new_toc+=("${indent}- [${title}](#$(anchor "$title")) L${lnum}:${end}")
done

# ── replace TOC content ───────────────────────────────────────────────────────
# Replaces lines (TOC_LINE+1)..(CONTENT_START-1) with the new entries.
# Preserves the blank line after the ## TOC header.

tmp=$(mktemp)
{
  sed -n "1,${TOC_LINE}p" "$FILE"
  echo ""
  printf '%s\n' "${new_toc[@]}"
  echo ""
  tail -n "+${CONTENT_START}" "$FILE"
} > "$tmp"
mv "$tmp" "$FILE"

echo "Refreshed: ${n} entries → ${FILE}"
