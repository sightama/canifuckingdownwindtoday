# WHY Button Redesign

## Problem

The WHY button is too hidden. It sits in the top-right corner, away from the natural content flow. Users' eyes follow a vertical path (title → score → description), so the corner button gets overlooked — especially on mobile.

This matters because the WHY dialog contains the app's most useful information: live conditions, the crayon graph, equipment recommendations, and live cams.

## Solution

Move the WHY button into the main content flow, directly below the snarky description.

### New Layout Order

1. Title — "CAN I FUCKING DOWNWIND TODAY"
2. Toggle — SUP Foil / Parawing
3. Score — "8/10"
4. Description — Snarky AI commentary
5. **WHY Button** — "EXPLAIN YOURSELF" ← new position
6. Timestamp — Last updated

## Visual Design

### Button Styling

Match the existing toggle aesthetic:

- **Border:** 2px solid black
- **Background:** White
- **Text:** Black, bold, uppercase
- **Padding:** ~5-10px vertical, ~15-20px horizontal
- **Positioning:** Centered, with ~20-30px vertical margin

### Hover State

Colors invert on hover:

- **Background:** Black
- **Text:** White
- **Border:** 2px solid black (unchanged)
- **Cursor:** Pointer

### Label

**"EXPLAIN YOURSELF"** — confrontational, on-brand with the app's snarky tone.

## Implementation

### Changes Required

1. Remove the absolutely-positioned WHY button from top-right corner
2. Add new button in content flow after description, before timestamp
3. Apply toggle-matching styles with hover inversion
4. Update button text from "WHY" to "EXPLAIN YOURSELF"

### No Changes

- Dialog content and functionality stays the same
- Click handler logic unchanged
- Dialog responsive behavior unchanged

### Files Affected

- `app/main.py` — WHY button definition (~lines 193-210) and main content column structure
