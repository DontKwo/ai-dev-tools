# Mocking discipline

Use real implementations inside process boundaries and restrict test doubles to external seams you cannot control deterministically.

## Dependency rules

| Dependency category | Test strategy | Example |
| :--- | :--- | :--- |
| In-process pure logic and local helpers | Real implementation | Parsers, validators, domain math |
| Local fast storage | Real temp directory or in-memory/local stand-in | `tempfile.TemporaryDirectory`, SQLite `:memory:` |
| Owned service across network boundary | In-memory port adapter | Queue/RPC interface adapter |
| Third-party API, clock, randomness, OS dialog | Explicit stub or fake at the injected boundary | Payment gateway, HTTP client, `sys.stdin` |

## Rules when writing mocks

1. Never mock internal sibling functions within the module under test; call them directly through the public seam.
2. Never mock simple value objects, dataclasses, or standard data structures.
3. Stub the narrowest external I/O boundary (for example HTTP transport or subprocess runner) and verify the production wrapper parses and handles both success and failure payloads.
4. Keep fakes stateful when testing multi-step flows so invariants hold across calls.
5. Delete brittle call-count mocks whenever code is deepened behind a cleaner interface seam.
