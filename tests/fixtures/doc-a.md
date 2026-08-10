# Doc A

Intro prose that sits before any addressable section.

## Alpha

Alpha body line one.
Alpha body line two.

### Alpha child

A level-3 section nested under Alpha. Fetching `alpha` must include this
heading and its body; fetching `alpha-child` must return only this part.

## Beta

Beta body before the subsection.

#### Beta deep

A level-4 subsection. Fetching `beta` must absorb it — a deeper heading is
part of the section, not a terminator.

More Beta body after the level-4 subsection.

## Set Up

First of the two headings that slug identically.

## set-up

Second of the two headings that slug identically. An id of `set-up` is
ambiguous and must fail loudly rather than resolve to the first match.

### Gamma

Gamma sits at level 3 under the second colliding section.

## Omega

Omega runs to the end of the file with no heading after it. Fetching `omega`
must return everything from here down.

Last line of the document.
