# WHY Button Redesign - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the WHY button from the hidden top-right corner into the main content flow (below the description), restyle it to match the toggle, and rename it to "EXPLAIN YOURSELF"

**Architecture:** Single-file change to `app/main.py`. Remove the absolutely-positioned button wrapper, add the button inline after the description element, apply toggle-matching styles with hover inversion.

**Tech Stack:** NiceGUI (Python web framework), inline CSS styling

---

## Background for Engineers New to This Codebase

### What This Project Is

A snarky weather app for downwind SUP foiling in Jupiter, FL. It shows a score (1-10), a profanity-laden AI-generated description, and a "WHY" button that reveals detailed weather conditions.

### How NiceGUI Works

NiceGUI is a Python web framework where UI elements are created with functions like `ui.button()`, `ui.label()`, `ui.html()`. Styling is done via `.style('css: value;')` chains. Elements appear in the order you create them in the code (like HTML document flow).

Example:
```python
ui.label('First')   # Appears first
ui.button('Click')  # Appears second
ui.label('Last')    # Appears third
```

### Key File

- `app/main.py` - The entire UI lives here. This is the only file you'll edit.

### How to Run the App Locally

```bash
cd c:\projects\canifuckingdownwindtoday
.venv\Scripts\activate
python -m app.main
```

Then open http://localhost:8080 in a browser. You'll see the score, description, and the WHY button.

### How to Run Tests

```bash
cd c:\projects\canifuckingdownwindtoday
.venv\Scripts\activate
pytest tests/ -v
```

Or run specific test file:
```bash
pytest tests/ui/test_why_button.py -v
```

### Testing Pattern in This Codebase

UI tests in this project read the source file and assert on its contents. This is because NiceGUI doesn't have easy unit testing for rendered output. Example from existing tests:

```python
def test_loading_text_is_loading(self):
    with open('app/main.py', 'r') as f:
        content = f.read()
    assert 'LOADING' in content
```

---

## Current Code Structure (What You're Changing)

In `app/main.py`, the relevant sections are:

| Lines | What It Does |
|-------|--------------|
| 189 | Main column container starts |
| 191 | Title "CAN I FUCKING DOWNWIND TODAY" |
| **193-199** | **OLD WHY button (absolutely positioned) ← DELETE THIS** |
| 201-244 | WHY dialog definition (keep this) |
| 245-305 | `show_why()` function (keep this) |
| **307** | **Click handler `why_button.on('click', show_why)` ← DELETE THIS** |
| 309-314 | Toggle (SUP Foil / Parawing) |
| 317 | `rating_label` |
| 318 | `description_label` ← **NEW BUTTON GOES AFTER HERE** |
| 321 | `timestamp_label` |

---

## Task 1: Write Failing Tests

**Files:**
- Create: `tests/ui/test_why_button.py`

### Step 1.1: Create test file with all tests

Create file `tests/ui/test_why_button.py` with this content:

```python
# ABOUTME: Tests for WHY button styling and positioning
# ABOUTME: Verifies button text, styles, and placement in content flow


class TestWhyButton:
    """Tests for the EXPLAIN YOURSELF button"""

    def test_button_text_is_explain_yourself(self):
        """Button should say 'EXPLAIN YOURSELF' not 'WHY'"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert "EXPLAIN YOURSELF" in content
        # Old text should NOT be present as a button label
        assert "ui.button('WHY')" not in content

    def test_button_not_absolutely_positioned(self):
        """Button should NOT be in an absolutely positioned container"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # The old pattern had a div with absolute positioning
        # This pattern should no longer exist
        assert "position: absolute; top: 20px; right: 20px;" not in content

    def test_button_has_border_style(self):
        """Button should have black border (matching toggle style)"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Should have border style like the toggle
        assert "border: 2px solid black" in content

    def test_button_appears_after_description(self):
        """Button should appear in content flow after description, before timestamp"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Find positions of key elements
        description_pos = content.find('description_label = ')
        button_pos = content.find("EXPLAIN YOURSELF")
        timestamp_pos = content.find('timestamp_label = ')

        assert description_pos != -1, "Could not find description_label"
        assert button_pos != -1, "Could not find EXPLAIN YOURSELF button"
        assert timestamp_pos != -1, "Could not find timestamp_label"

        # Button should come after description and before timestamp
        assert description_pos < button_pos < timestamp_pos, \
            f"Button should be between description and timestamp. " \
            f"Found: description={description_pos}, button={button_pos}, timestamp={timestamp_pos}"

    def test_button_has_hover_behavior(self):
        """Button should invert colors on hover"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Should have mouseover handler for hover effect
        assert "mouseover" in content or "hover" in content.lower()
```

### Step 1.2: Run tests to verify they fail

```bash
pytest tests/ui/test_why_button.py -v
```

**Expected output:** All 5 tests FAIL:
- `test_button_text_is_explain_yourself` - FAIL (button says 'WHY')
- `test_button_not_absolutely_positioned` - FAIL (has absolute positioning)
- `test_button_has_border_style` - FAIL (no border style)
- `test_button_appears_after_description` - FAIL (button is before description)
- `test_button_has_hover_behavior` - FAIL (no hover handlers)

### Step 1.3: Commit the failing tests

```bash
git add tests/ui/test_why_button.py
git commit -m "test: add failing tests for WHY button redesign

Tests verify:
- Button text is 'EXPLAIN YOURSELF'
- Button is not absolutely positioned
- Button has border style matching toggle
- Button appears after description in content flow
- Button has hover color inversion"
```

---

## Task 2: Remove Old WHY Button

**Files:**
- Modify: `app/main.py`

### Step 2.1: Delete the old button code (lines 193-199)

Open `app/main.py` and find this block (around lines 193-199):

```python
        # WHY button in top-right corner
        with ui.element('div').style('position: absolute; top: 20px; right: 20px;'):
            why_button = ui.button('WHY').style(
                'font-size: 18px; font-weight: bold; padding: 10px 20px; '
                'background: black; color: white; border: none; '
                'border-radius: 25px; cursor: pointer;'
            ).props('flat')
```

**DELETE these 7 lines entirely.**

### Step 2.2: Delete the old click handler (line 307)

Find this line (around line 307, but line numbers shifted after deletion):

```python
        why_button.on('click', show_why)
```

**DELETE this 1 line.** (We'll add the click handler with the new button.)

### Step 2.3: Run tests to check progress

```bash
pytest tests/ui/test_why_button.py::TestWhyButton::test_button_not_absolutely_positioned -v
```

**Expected:** This test now PASSES (absolute positioning is gone).

### Step 2.4: Do NOT commit yet

The app is currently broken (no button exists). Continue to Task 3.

---

## Task 3: Add New WHY Button in Content Flow

**Files:**
- Modify: `app/main.py`

### Step 3.1: Find the insertion point

In `app/main.py`, find this line (was line 318, now shifted due to deletions):

```python
        description_label = ui.html('<div class="description">Loading conditions...</div>', sanitize=False)
```

### Step 3.2: Add new button code immediately AFTER description_label

Insert this code block right after the `description_label` line:

```python
        # WHY button - styled to match toggle, positioned in content flow
        why_button = ui.button('EXPLAIN YOURSELF').style(
            'font-size: 16px; font-weight: bold; padding: 8px 20px; '
            'background: white; color: black; border: 2px solid black; '
            'cursor: pointer; margin-top: 20px;'
        ).props('flat')

        def on_hover_enter():
            why_button.style('background: black; color: white;')

        def on_hover_leave():
            why_button.style(
                'background: white; color: black; border: 2px solid black;'
            )

        why_button.on('mouseover', on_hover_enter)
        why_button.on('mouseout', on_hover_leave)
        why_button.on('click', show_why)
```

### Step 3.3: Run all tests

```bash
pytest tests/ui/test_why_button.py -v
```

**Expected:** All 5 tests PASS.

### Step 3.4: Run the full test suite

```bash
pytest tests/ -v
```

**Expected:** All tests pass. If any fail, investigate before continuing.

### Step 3.5: Commit the implementation

```bash
git add app/main.py
git commit -m "feat: move WHY button to content flow with new style

- Remove absolutely positioned button from top-right corner
- Add button below description, before timestamp
- Rename from 'WHY' to 'EXPLAIN YOURSELF'
- Style to match toggle (black border, white background)
- Add hover effect (colors invert on mouseover)"
```

---

## Task 4: Manual Testing

### Step 4.1: Start the app

```bash
python -m app.main
```

### Step 4.2: Verify in browser

Open http://localhost:8080 and check:

1. **Button visibility:** "EXPLAIN YOURSELF" button should be clearly visible below the snarky description
2. **Button style:** Should have black border, white background (matching the toggle above)
3. **Hover effect:** Mouse over the button - it should turn black with white text
4. **Click behavior:** Click the button - the WHY dialog should open with weather details and live cams
5. **Mobile view:** Resize browser to mobile width - button should remain centered and visible

### Step 4.3: Document any issues

If anything looks wrong, note the issue and fix it before final commit.

---

## Task 5: Final Verification and Commit

### Step 5.1: Run full test suite one more time

```bash
pytest tests/ -v
```

All tests must pass.

### Step 5.2: Check git status

```bash
git status
```

Should show clean working tree (everything committed).

### Step 5.3: Review the changes

```bash
git log --oneline -3
git diff HEAD~2..HEAD
```

Verify the changes look correct.

---

## Summary of Changes

| What | Before | After |
|------|--------|-------|
| Button text | "WHY" | "EXPLAIN YOURSELF" |
| Position | Absolute, top-right corner | In content flow, after description |
| Background | Black | White |
| Text color | White | Black |
| Border | None (pill shape) | 2px solid black |
| Hover | None | Colors invert |
| Visibility | Easy to miss | Prominent, in reading flow |

---

## Troubleshooting

### "why_button is not defined" error

You probably deleted the old button but forgot to add the new one, or added it in the wrong place. The new button must be created BEFORE `show_why` is referenced.

### Hover effect not working

Make sure you have both `mouseover` and `mouseout` handlers. The `mouseout` handler must restore the border style too.

### Button appears in wrong place

Check the line order in main.py. The content flow should be:
1. Title
2. Toggle
3. Rating
4. Description
5. **WHY Button** ← HERE
6. Timestamp

### Tests still failing

Re-read the test assertions. Common issues:
- Typo in "EXPLAIN YOURSELF"
- Missing "border: 2px solid black" (exact string match)
- Button code inserted in wrong location
