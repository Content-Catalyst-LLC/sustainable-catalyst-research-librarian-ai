from fastapi.testclient import TestClient

from app.main import _follow_up_prompts, _resolve_research_mode, _workspace_summary, app
from app.models import RetrievedSource


client = TestClient(app)


def source(title: str = "Systems Thinking") -> RetrievedSource:
    return RetrievedSource(
        id="systems-thinking",
        title=title,
        url="https://sustainablecatalyst.com/library/systems-thinking/",
        summary="Feedback, structure, resilience, and complex change.",
        score=10.0,
        exact_title_match=True,
        citation_label="SC1",
    )


def test_explicit_research_mode_is_preserved() -> None:
    assert _resolve_research_mode("Find evidence for this claim", "compare") == "compare"


def test_auto_mode_classifies_common_tasks() -> None:
    assert _resolve_research_mode("Find the article titled Systems Thinking", "auto") == "title"
    assert _resolve_research_mode("Compare two governance approaches", "auto") == "compare"
    assert _resolve_research_mode("Prepare a decision brief", "auto") == "decision"
    assert _resolve_research_mode("Build a reading path", "auto") == "path"


def test_follow_up_prompts_are_site_scoped() -> None:
    prompts = _follow_up_prompts("evidence", source(), [])
    assert len(prompts) >= 2
    assert all("Systems Thinking" in item or "record" in item for item in prompts)


def test_session_reset_endpoint() -> None:
    response = client.post(
        "/v1/session/reset",
        headers={"X-SC-RL-Key": "test-key"},
        json={"session_id": "workspace-session"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "6.7.0"
    assert body["session_id"] == "workspace-session"
    assert body["removed_turns"] >= 0


def test_workspace_schema_advertises_accessibility_and_staged_rendering() -> None:
    workspace = _workspace_summary("subject", [source()], [], False, {"ok": True})
    assert workspace["schema"] == "sc-research-librarian-public-workspace/1.2"
    assert workspace["accessibility_profile"] == "wcag-focused-v6.5.1"
    assert workspace["rendering_profile"] == "staged-v6.5.1"
