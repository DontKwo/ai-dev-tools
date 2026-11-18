# Meta Astryx Specification & Architecture Reference

## Overview
Meta Astryx is an accessible enterprise design system created for React 19 and StyleX.

## Core Capabilities
- 150+ accessible interactive UI components meeting WCAG AA requirements out-of-the-box.
- Brand-level design tokens with automatic light and dark color scheme support.
- Pre-built responsive layout templates (dashboard, split-view, settings, forms, data tables).
- Built-in AI agent scaffolding CLI (`npx @astryx/cli`) and MCP server support.

## Integration in ai-dev-tools
- Active Skill: `skills/react-astryx/`
- Active Templates: `templates/astryx/`
- Rule Mandate: When creating new frontend React projects, agents evaluate Astryx first rather than generating unstyled JSX or mismatched CSS libraries. Custom CSS is written strictly around Astryx components for domain-specific styling.
