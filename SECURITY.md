# Security Policy

## Supported Versions & Official Releases

| Version / Branch | Supported | Notes |
| :--- | :--- | :--- |
| `main` (Latest `vX.Y.Z` Release) | Yes | Actively maintained official release stream |
| Forks, Mirrors, and Older Tags | No | Unverified and unsupported |

Official binaries and installers are distributed exclusively from the primary `DontKwo/ai-dev-tools` repository on GitHub (`main` branch and official [Releases](https://github.com/DontKwo/ai-dev-tools/releases/latest)).

- **Fork Safety Warning**: Do **not** download or run executables from forked repositories or third-party mirrors unless you have verified the source code yourself and confirmed they contain no malware. Only `DontKwo/ai-dev-tools` `main` builds are maintained by the author.
- **OS Security Prompts**: Because `AI-Dev-Tools` is published independently without paid commercial code-signing certificates, Windows SmartScreen and macOS Gatekeeper may warn that the download is unrecognized or potentially unsafe. Review [Desktop Installation Guide](docs/INSTALLATION.md) and bypass security prompts strictly at your own discretion.

## Warranty & Liability Disclaimer

`AI-Dev-Tools` modifies AI assistant instruction files, skill folders, MCP configurations, and git hook files inside workspaces you select. It is provided "AS IS" under the [MIT License](LICENSE), without warranty of any kind. The author assumes zero responsibility or liability for configuration changes, overwritten files, or damages arising from using this software. Review previews before applying changes and use strictly at your own discretion.

## Reporting a Vulnerability

If you discover a security issue in `DontKwo/ai-dev-tools`:

1. **Do not** disclose exploit details or credentials in a public GitHub Issue.
2. Open a [Private Vulnerability Report](https://github.com/DontKwo/ai-dev-tools/security/advisories/new) on GitHub (or contact `@DontKwo` on GitHub if private advisories are unavailable).
3. Include reproduction steps, affected operating system or version, and any suggested fix.

## Related Documentation

- [Project Overview](README.md)
- [User Guide](docs/USER_GUIDE.md)
- [Desktop Installation Guide](docs/INSTALLATION.md)
- [Developer Guide](docs/DEVELOPMENT.md)
- [License](LICENSE)
