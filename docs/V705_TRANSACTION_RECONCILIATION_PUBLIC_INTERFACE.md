# Research Librarian AI v7.0.5

## Transaction Reconciliation and Public Interface Repair

v7.0.5 repairs the production failure in which WordPress completed 23 of 24 replacement batches but the Python backend did not commit the final transaction. The complete WordPress JSONL staging file remains the recovery source, so the repair does not need to rediscover more than 2,000 public records.

### Recovery workflow

1. WordPress queries the authenticated backend transaction-status endpoint.
2. The backend reports expected, received, and missing batch numbers.
3. When the original backend staging state is missing or incomplete, WordPress assigns a new backend transaction ID.
4. WordPress replays its durable local staging file in the existing bounded batch size.
5. The previous committed index remains active until the replay transaction commits and the replacement index is verified.
6. Recovery stops after a bounded number of attempts and preserves the staging file for diagnosis.

The v7.0.4 failure can be resumed using **Repair and Resume Commit**. Cancelling the old job is not required.

### Backend endpoints

- `GET /v1/knowledge/sync/jobs/{job_id}` — reports transaction state, received batches, missing batches, staged records, rejection counts, and commit state.
- `DELETE /v1/knowledge/sync/jobs/{job_id}` — clears an incomplete backend transaction while refusing to delete an already committed transaction.

### Public interface repair

The public assistant no longer depends on a narrow two-pane terminal treatment. v7.0.5 provides:

- one readable vertical workflow;
- eight visible research-mode cards with plain-language descriptions;
- a light, high-contrast question field;
- a full-width maroon **Start Research** action;
- secondary save/export/review controls behind progressive disclosure;
- visible example questions;
- a separate answer surface with compact visitor-facing service status;
- responsive two-column and one-column mode layouts for smaller screens.

The plugin repairs the Research Librarian assistant block. Long explanatory sections placed directly in the WordPress page remain page content and can be shortened separately without changing the assistant runtime.
