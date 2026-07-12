from app.models import KnowledgeRecord
from app.retrieval import retrieve


def record(record_id: str, title: str, summary: str = "", series: str = "") -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=title,
        url=f"https://sustainablecatalyst.com/{record_id}/",
        slug=record_id,
        summary=summary,
        series=series,
    )


def test_exact_title_beats_generic_platform() -> None:
    records = [
        record("platform", "Platform", "General architecture page."),
        record("rank-nullity", "Rank, Nullity, and Structural Dependence", "Linear algebra article.", "Linear Algebra for Systems Modeling"),
    ]
    results = retrieve("Rank, Nullity, and Structural Dependence", records, 5)
    assert results[0].title == "Rank, Nullity, and Structural Dependence"
    assert results[0].exact_title_match is True


def test_series_context_supports_article_retrieval() -> None:
    records = [
        record("stability", "Stability Analysis with Eigenvalues", "System stability article.", "Linear Algebra for Systems Modeling"),
        record("platform", "Platform", "General platform page."),
    ]
    results = retrieve("linear algebra systems modeling stability", records, 5)
    assert results[0].title == "Stability Analysis with Eigenvalues"
