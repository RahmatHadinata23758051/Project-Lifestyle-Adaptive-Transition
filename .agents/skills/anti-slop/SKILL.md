---
name: anti-slop
description: Enforce zero AI slop across UI design, code quality, copywriting, error handling, and eliminate hallucinations.
---

# Anti-Slop Audit & Quality Enforcement Skill

Use this skill whenever generating, reviewing, or refactoring code, UI layouts, copy, or system logic to guarantee zero AI slop, zero emoji pollution, zero hallucinated APIs, and zero silent failures.

---

## 1. Trigger Scenarios
Invoke this skill when:
- Creating or editing mobile UI screens, widgets, or themes.
- Writing backend services, models, and calculation engines.
- Reviewing PRs, code diffs, or committing changes.
- Writing user-facing microcopy, logs, or documentation.

---

## 2. Core Audit Routine

### Phase 1: Visual & UI Slop Scan
1. **Color & Gradients**:
   - Check if any component uses purple-to-cyan/pink gradients or glowing borders. Replace with semantic color tokens.
2. **Surface & Card Structures**:
   - Verify there are no side-tab borders on rounded cards (`border-left` + `border-radius`).
   - Eliminate cards nested inside cards (max 1 layer of card elevation).
   - Ensure corner radii do not exceed 16px for card containers (no blob cards).
   - Remove any unnecessary backdrop blur/glassmorphism effects.
3. **Typography & Layout**:
   - Remove uppercase eyebrow/kicker labels above titles.
   - Verify font hierarchy has a scale ratio of at least 1.25x between headings and body text.
   - Ensure interactive icons are aligned naturally without floating squircle icon boxes.

### Phase 2: Copy & Text Cleanliness
1. **Emoji Stripping**:
   - Scan and remove all emojis from code variables, UI labels, button text, error messages, and commit messages.
2. **AI Buzzword Removal**:
   - Remove phrases such as *"seamlessly elevate"*, *"unleash potential"*, *"next-gen"*, or sycophantic greetings.
3. **Non-Judgmental Tone**:
   - Ensure failed targets are presented as objective inputs for adaptation (e.g. *"Target adjusted based on actual time"* instead of *"You failed"*).

### Phase 3: Code & Engineering Rigor
1. **Hallucination & Import Check**:
   - Verify every imported library, function signature, and method against the official documentation or package definition.
2. **Error Handling & Resilience**:
   - Ensure there are no empty `catch` blocks or unhandled promise rejections.
   - Verify all temporal calculations handle midnight rollover (e.g., bedtime 02:30 AM vs wake time 10:00 AM).
3. **Real Implementation Verification**:
   - Eliminate fake static mock arrays masquerading as working database or calculation routines.

---

## 3. Strict Prohibitions
- DO NOT use emojis in code, UI copy, or commits.
- DO NOT leave half-baked `// TODO` stubs in core flow.
- DO NOT write redundant UI helper text that duplicates label content.
- DO NOT suppress errors silently.
