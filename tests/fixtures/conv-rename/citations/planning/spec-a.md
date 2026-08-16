# Spec A

Fixture file, standing in for a planning document that cites conventions from a
step manifest line.

## S1 — a step that cites two conventions

**conventions** — old-name, other-name

A manifest line is one of the two citation shapes: bare names in a
comma-separated list, no markdown around them.

## S2 — a step that cites a near-miss

**conventions** — old-name-extended

That is a different convention whose name merely begins with the same
characters as the one S1 cites. Whole-token matching is the only thing standing
between a rename and mangled neighbours, so this line has to come out
unchanged.

Old-Name, capitalized, is not a citation either: names are lowercase by
construction and matching is case-sensitive, so a capitalized spelling is a
typo for a reader to fix rather than a token for a tool to rewrite.
