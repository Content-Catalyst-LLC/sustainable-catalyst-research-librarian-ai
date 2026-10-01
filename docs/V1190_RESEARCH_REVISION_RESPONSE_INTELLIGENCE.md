# Research Librarian v11.9.0 — Research Revision & Response Intelligence

v11.9.0 turns revision and response work into a traceable research object rather than a prose-only exchange.

It binds a revision-response project to a v11.8 scholarly critique project, preserves the critique source hash, and maps human-authored response items back to critique IDs and revision requirements. Authors can record claimed changes with before/after refs and hashes; artifact/diff receipts can document observed changes; specialist runtimes can perform approved checks; and reviewers can separately record human resolution judgments.

Core views include the response matrix, change-evidence matrix, unresolved-response register, specialist verification handoffs, structural readiness, assembled response package, Platform Core candidate, and immutable snapshot.

Important governance boundary: an author saying a concern was addressed does not mean a reviewer considered it satisfied. A change claim is not proof of a change until supported by an artifact receipt, and an artifact receipt does not prove the change is correct. No automatic accept/reject, editorial decision, scientific-validity verdict, misconduct inference, specialist execution, or truth promotion occurs.

Persistence: PostgreSQL production with SQLite local/test fallback. Migration 034. Durable job `research-revision-response-intelligence-snapshot`. Unified component type `research-revision-response`.
