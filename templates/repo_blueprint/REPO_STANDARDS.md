# Canonical Repository Standards (Rules 101 to 112)

Every repository maintained under the `DontKwo` unified standards follows a consistent structure, licensing model, companion guide set, dual-asset branding, and release pipeline.

## Core Blueprint Files

- [README Template](README_TEMPLATE.md): User-first project overview (`<= 120` lines) with centered logo, top [Download Table](README_TEMPLATE.md#download), real [Screenshots](README_TEMPLATE.md#screenshots), usage overview, features, disclaimers, and ordered documentation index.
- [MIT License](LICENSE_MIT.txt): Canonical MIT License (`Copyright (c) 2026 DontKwo`).
- [Security Policy Template](SECURITY_TEMPLATE.md): Official `main`-only support statement, fork malware warning, OS/mobile prompt bypass discretion notice, and private reporting workflow.
- [Desktop Installation Template](INSTALLATION.md): Per-platform SmartScreen, Gatekeeper (`xattr`), and Linux executable setup instructions.
- [Android APK Installation Template](APK_INSTALLATION.md): Six-step Android sideloading instructions covering Samsung Auto Blocker, Install Unknown Apps, Google Play Protect, and Android 13 to 15 Restricted Settings.
- [Developer uv Installation Template](UV_INSTALLATION.md): Cross-platform developer environment setup for Astral `uv`.
- [OpenFOAM Installation Template](OPENFOAM_INSTALLATION.md): Cross-platform WSL2, native Ubuntu/Debian, and macOS Docker instructions for OpenFOAM.
- [CI & Release Workflow Template](ci-template.yml): Unified four-stage workflow (`lint` -> `test` -> `build` -> `release`) triggering on `main` pushes, `v*` tags, and pull requests, publishing `vX.Y.Z` releases with `prerelease: false` and `make_latest: true`.

## Compliance Summary (Rules 101 to 112)

1. **Repository Hygiene (101)**: Include standard root legal, agent, user, developer, and CI files; remove temporary plan or design notes and compiled root executables.
2. **README Structure (102)**: Keep the main overview concise (`<= 120` lines), place downloads above screenshots and disclaimers, and order documentation User, Developer, AI/Technical, and Legal.
3. **README Purity (103)**: Keep test commands, build scripts, checksums, CI explanations, and clone commands out of the user README and inside developer documentation.
4. **Circular & Clickable Links (104)**: Link every referenced file directly in prose and end every guide under the documentation folder with a `## Related Documentation` footer linking back to [Linter Rules Reference](../../docs/LINTER_RULES.md) or the repository overview.
5. **Minimal Downloads (105)**: List at most one primary release download per OS platform unless compatibility requires a split.
6. **Companion Guides (106)**: Include APK, `uv`, and OpenFOAM guides whenever a repository uses those toolchains.
7. **Dual Branding (107)**: Separate the full wordmark banner from a cropped text-free square application icon.
8. **Single Unified Workflow (108)**: Enforce strict lint, link checks, test suites, executable self-tests, and Semantic Versioning releases inside one workflow file.
9. **License & Security Alignment (109)**: Standardize on MIT licensing and consistent `main`-only fork safety notices.
10. **Explicit Platform Sections (110)**: Use `### Windows`, `### macOS`, and `### Linux` headings in cross-platform guides, or declare single-OS scope in configuration.
11. **Unified GUI Stack (111)**: Build desktop apps on unified HTML/React WebView hosts and native Android apps on Jetpack Compose.
12. **Executable Self-Test (112)**: Implement a headless `--self-test` verification flag in every desktop host and run it in CI.

## Related Documentation

- [Project Overview](../../README.md)
- [Linter Rules Reference](../../docs/LINTER_RULES.md)
- [Developer Guide](../../docs/DEVELOPMENT.md)
- [Security Policy](../../SECURITY.md)
