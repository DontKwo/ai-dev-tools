---
name: ux-audit
description: >-
  Proactively audit user interfaces for responsiveness, contrast, accessibility, performance, and interaction friction without waiting for bug reports. Use when building or modifying user-facing apps.
---

# UX Audit

Audit user experiences proactively across screen viewports, visual themes, and accessibility requirements.

## Trigger

Run whenever modifying or introducing user-facing interfaces, components, or screens.

## Audit Workflow

### 1. Viewport & Theme Inspection
Capture screenshots across standard responsive resolutions in both light and dark themes:
- Mobile Phone: 360x640
- Modern Handset: 390x844
- Tablet: 768x1024
- Small Laptop: 1280x800
- Desktop Display: 1920x1080

### 2. Interaction & Visual Checks
- Contrast: Verify WCAG AA contrast (minimum 4.5:1 for normal text, 3:1 for large text).
- Touch Targets: Ensure all interactive targets meet minimum 44x44px dimensions.
- Alignment & Spacing: Check padding consistency and prevent visual collisions.
- Screen States: Confirm empty, loading, and error states exist for every view.
- Form Inputs: Ensure explicit labels, native attributes, and friendly validation error messages.
- Destructive Actions: Implement confirm dialogs or undo mechanisms.
- Focus & Navigation: Verify clean focus rings, tab order, and browser back-button behavior.
- Browser Artifacts: Eliminate default selection boxes and raw outline anomalies.

### 3. Accessibility & Performance
- Automated Accessibility: Scan views using axe-core for WCAG AA compliance.
- Motion: Respect `prefers-reduced-motion` media queries.
- Typography: Verify layout stability under 200% system font scaling.
- Latency & Shifts: Measure startup time, input response, and Cumulative Layout Shift (CLS) under 4x CPU throttle.

### 4. Static Code Checks
- Audit templates and styles for hardcoded color hex values; ensure design tokens are used.
- Detect duplicated layout components, missing loop keys, and missing error boundaries.
- Prune unreferenced visual assets and CSS rules.

## Triage & Defect Reporting

Triage all discovered issues into priority buckets directly in the pull request description:
- **P0**: Core workflow blocker, severe crash, or total illegibility.
- **P1**: Significant usability defect, WCAG failure, or layout overlap.
- **P2**: Minor layout imperfection, missing loading skeleton, or delayed feedback.
- **P3**: Cosmetic polishing, micro-animation refinement, or non-blocking suggestion.

Fix P0 to P2 issues and inexpensive P3 items in the active change. Attach before-and-after screenshots to the PR.
