# cinema-recs

Personal, solo-maintained media/showtime recommendation app. See `.specify/memory/constitution.md`
for the governing principles (Python-first, Docker-native, Unraid-compatible, simplicity-first).

Feature work follows the Spec Kit workflow (`specs/NNN-feature-name/`, driven by the
`speckit-*` skills). Before planning or implementing a feature, consult the graphify
knowledge graph (`graphify-out/`) for architecture/dependency context — see the graphify
skill below.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
