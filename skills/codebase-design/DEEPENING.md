# Deepening modules safely

Follow this playbook when merging shallow pass-through wrappers into a single deep module whose interface owns the real complexity. Assumes the vocabulary in [SKILL.md](SKILL.md).

## Classify dependencies behind the seam

| Category | Characteristics | Testing approach at the seam |
| :--- | :--- | :--- |
| 1. In-process | Pure computation or in-memory transforms, zero I/O | Merge modules and test directly through the public interface; zero adapters needed |
| 2. Local-substitutable | Filesystem, SQLite, or local stand-in | Run against temp directory or in-memory DB directly inside the test suite |
| 3. Remote but owned | Internal services or RPC queues | Define an injected port at the seam with production transport and in-memory test adapter |
| 4. True external | Third-party SaaS APIs, system clock, OS GUI dialogs | Inject narrow boundary port and supply explicit fake/stub in tests |

## Seam discipline

- **Two real adapters justify a port**: Only introduce an abstract interface when both production and test (or two production transports) genuinely need distinct implementations. A single-adapter port is empty indirection.
- **Keep internal seams private**: Helper functions inside the deep module stay unexported. Expose only the stable public interface.
- **Replace shallow tests instead of layering**: Once tests cover the new deep interface thoroughly, delete obsolete unit tests targeting the dissolved wrapper functions.
