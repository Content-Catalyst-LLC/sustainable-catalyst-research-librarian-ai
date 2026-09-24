# Research Librarian AI v8.12.0 — Visual Research Intelligence

v8.12.0 connects Research Librarian publications, canonical sources, citations, governed evidence, reviewed findings/claims, arguments, statistical reasoning objects, project state, provenance and timelines to Platform Core's visual-reasoning stack.

## Authority boundary

**Research Librarian owns:** discovery context, source/citation intelligence, evidence references, deterministic visual-plan assembly, source hashes, review state and Core orchestration.

**Platform Core owns:** canonical visual reasoning object IDs, semantic visual elements/layers/relations, immutable visual snapshots, unified research-session visual bindings, renderer-neutral scene semantics and cross-product visual identity.

**Specialist visual runtimes own:** layout algorithms, SVG/Canvas/WebGL/WebGPU rendering, animation, hit-testing, 3D/4D interaction and product-specific visualization execution.

The Librarian does not infer graph edges, infer evidentiary meaning from visual position, render scenes, rank arguments, interpret statistical significance, promote findings/claims, or determine truth.

## Supported visual research kinds

- citation network
- evidence map
- claim map
- finding map
- contradiction map
- argument graph
- statistical result view
- uncertainty view
- provenance graph
- research timeline
- source lineage
- concept map
- generic research view

## Core surfaces used

- `GET /v1/visual-reasoning/readiness`
- `POST /v1/visual-reasoning/objects`
- `POST /v1/visual-reasoning/objects/{visual_entity_id}/layers`
- `POST /v1/visual-reasoning/objects/{visual_entity_id}/elements`
- `POST /v1/visual-reasoning/objects/{visual_entity_id}/relations`
- `POST /v1/visual-reasoning/objects/{visual_entity_id}/snapshots`
- `GET /v1/visual-runtime/unified/readiness`
- `POST /v1/research/unified-runtime/visual-bindings`

Core contracts retained include `sc.visual-runtime.scene.v1`, `sc.visual-runtime.unified-reasoning.v1`, and `sc.visual-runtime.cross-product-integration.v1`.

## Human review

Plans default to `pending`. Core promotion requires `review_decision=approved` and a non-empty reviewer reference. A Core session ID is also required when unified research-session binding is requested.

## Durable execution

`visual-research-plan` is supported by the existing Postgres-backed asynchronous job runtime. This job only prepares the renderer-neutral plan; it does not promote or render it automatically.
