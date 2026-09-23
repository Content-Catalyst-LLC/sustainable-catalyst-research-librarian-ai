Research Librarian AI v8.9.0 — Finding, Claim & Evidence Extraction Pipeline

Order of operations:
1. Run PUSH_RESEARCH_LIBRARIAN_V890_PY312.sh against the repository ZIP.
2. Upload the backend ZIP and v8.9.0 Contabo upgrade script to /tmp.
3. Run the Contabo backend upgrade and wait for version=8.9.0 + ready=true.
4. Confirm Platform Core project-state and sc.research.finding-claim-evidence.v1 readiness.
5. Install the WordPress v8.9.0 ZIP only after backend verification succeeds.

The extraction pipeline creates pending candidates. Core promotion requires explicit approved review state and reviewer identity. Approved registrations remain proposed in Core.
