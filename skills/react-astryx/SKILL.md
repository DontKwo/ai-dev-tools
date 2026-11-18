---
name: react-astryx
description: Scaffold and style frontend React 19 web applications using the Meta Astryx design system, accessible components, and theme tokens.
---

# React Astryx Frontend Design

Design accessible, responsive React 19 web applications using the Meta Astryx enterprise component suite instead of inventing unstyled JSX or ad-hoc CSS.

## When to Use
- Building a new web frontend from scratch when React is evaluated as an appropriate tool.
- Refactoring unstyled HTML/JSX into an accessible, production-ready interface.
- Creating dark and light theme layouts with verified WCAG AA contrast.

## Workflow

1. **Evaluate Tool Selection**:
   - For simple single-file spikes or zero-dependency prototypes, favor plain HTML/JS or the `prototype` skill.
   - For full single-page applications with state management and interactive views, select React 19 + Astryx.

2. **Scaffold Layout via Astryx**:
   - Use Astryx layout templates (`DashboardLayout`, `SplitViewLayout`, `SettingsLayout`).
   - Use core accessible components (`Button`, `TextInput`, `Modal`, `Table`, `Dropdown`) instead of raw unstyled elements.
   - Configure brand theme tokens supporting automatic dark mode switching.

3. **Domain Styling**:
   - Use StyleX for component-scoped styles.
   - Write custom CSS around Astryx components only when specialized domain-specific visuals or custom charts are required.
   - Maintain minimum 44px touch targets and full keyboard operability (Tab and Enter navigation).
