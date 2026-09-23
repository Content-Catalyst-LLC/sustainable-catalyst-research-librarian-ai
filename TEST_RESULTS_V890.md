# Research Librarian AI v8.9.0 Validation

Release: **v8.9.0 — Finding, Claim & Evidence Extraction Pipeline**

## Working-tree validation

- Python backend: **181 passed**
- WordPress/PHP contract & functional suites: **47 passed**
- PHP syntax: **61 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **115 files passed**
- Shell syntax: **37 files passed**
- Python compilation: **passed**
- Secret-pattern scan: **passed**

## v8.9.0 coverage

- Deterministic sentence-level candidate finding/claim extraction
- Exact evidence-passage provenance and v8.7 Core EvidenceRecord binding resolution
- Pending-by-default review state
- Explicit approved + reviewer identity gate before Platform Core promotion
- Proposed-only Core finding/claim registration
- Conservative `contextualizes` evidence-link default unless explicitly overridden
- Uncertainty-cue detection without confidence manufacture
- Platform Core `sc.research.finding-claim-evidence.v1` typed client integration
- v8.8 project-state readiness registration repair
- Platform Core Finding/Claim/Evidence readiness registration
- Durable `research-intelligence-extraction` async job execution
- No automatic truth determination, evidence-strength judgment, contradiction resolution, or publication

## Packaged artifact smoke

- Extracted repository ZIP: **181 Python tests passed**
- Extracted repository ZIP: **47 WordPress/PHP contract suites passed**
- Packaged release identity/files: **passed**
- ZIP integrity: **passed**
