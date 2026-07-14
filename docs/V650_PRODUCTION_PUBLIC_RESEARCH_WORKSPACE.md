# Research Librarian AI v6.5.0 — Production Public Research Workspace

## Purpose

v6.5.0 turns the calibrated retrieval and citation engine into a finished public research experience. The release keeps the Research Librarian site-scoped: it retrieves Sustainable Catalyst knowledge first, separates evidence from synthesis, and offers only explicit, user-confirmed next actions.

## Research modes

The public workspace provides eight modes:

1. **Auto-detect** — classify the request without requiring the visitor to choose a workflow.
2. **Find a title** — prioritize exact and partial canonical-title matches.
3. **Explore a subject** — connect concepts, series, article maps, and related records.
4. **Build a path** — create an ordered reading and research route.
5. **Find evidence** — foreground passages, headings, pages, and source records.
6. **Analyze** — identify assumptions, variables, methods, formulas, and appropriate analytical tools.
7. **Compare** — organize similarities, differences, evidence, and unresolved questions.
8. **Prepare a decision** — organize alternatives, evidence, uncertainty, and a controlled Decision Studio handoff.

The selected mode is sent to FastAPI as `research_mode`. Auto-detect remains available and uses bounded rule-based classification.

## Public layout

The desktop experience uses a responsive two-pane workspace:

- a focused, sticky question console;
- a larger answer and evidence surface.

At narrower widths the layout becomes one column. The prompt retains the black background, green monospace text, green caret, subdued green placeholder, and visible green focus state. Answer, source, citation, path, and action surfaces remain light.

## Answer-first presentation

The response surface presents:

- the active research mode;
- response type and source count;
- the primary answer;
- verified evidence and citations;
- related records;
- a guided research path;
- controlled platform actions;
- optional retrieval diagnostics.

Diagnostics do not displace the primary answer.

## Session continuity

Short session continuity is bounded to the site-scoped research task. Responses expose:

- `session_id`;
- `session_turns`;
- `follow_up_prompts`;
- `research_mode`;
- a structured `workspace` summary.

`POST /v1/session/reset` clears the backend session. The public interface also clears its local session identifier and hides prior follow-up state when the visitor selects **Reset session**.

## Accessible title suggestions

Indexed-title suggestions support:

- `aria-expanded` state on the question field;
- Arrow Down from the question field into the result list;
- Arrow Up and Arrow Down within results;
- Escape to close and return focus;
- automatic selection of **Find a title** mode when a title is chosen.

## Exports and controlled actions

The public utility panel provides:

- copy answer;
- copy route note;
- Markdown download;
- JSON download;
- editable research-note template;
- print workspace;
- typed handoff download;
- save session;
- helpful and issue feedback.

No external workspace is changed without an explicit visitor action.

## Startup and recovery behavior

The workspace displays startup phase and percentage while the Render service wakes. When a verified WordPress fallback is available, the message says so. Repeated transient notices remain subject to v6.3.1 suppression rules, while permanent failures remain visible.

## Backend contract

The v6.5.0 ask response adds:

```json
{
  "research_mode": "subject",
  "follow_up_prompts": ["..."],
  "workspace": {
    "schema": "sc-research-librarian-public-workspace/1.0",
    "mode": "subject",
    "mode_label": "Explore a subject",
    "source_count": 4,
    "related_count": 3,
    "answer_kind": "generated"
  },
  "session_turns": 2
}
```

The WordPress bridge normalizes the same fields into public responses and route-note metadata.

## Boundaries

- Retrieval precedes generation.
- Generated citations and links must verify against synchronized evidence.
- Weak evidence uses deterministic fallback or clarification.
- Follow-up continuity is short and site-scoped.
- Export and handoff actions remain explicit.
- The release does not modify the separate Research Library page’s Browse by Topic accordion or Featured Knowledge Pathways layout.
