import httpx
import pytest

from app.config.settings import settings
from app.models import GeneratedReport, ReportGenerationLog
from app.services.report_generation_service import (
    ReportGenerationError,
    ReportGenerationService,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_report_success_and_cache(db_session, sample_domain, monkeypatch):
    _, report = sample_domain

    call_counter = {"count": 0}

    async def fake_call(cls, prompt_text):
        call_counter["count"] += 1
        current = call_counter["count"]
        return {
            "id": f"fake-response-{current}",
            "choices": [
                {
                    "message": {
                        "content": f"# Markdown {current}\nContenido generado"
                    }
                }
            ],
            "usage": {"total_tokens": 128 + current},
        }

    monkeypatch.setattr(
        ReportGenerationService,
        "_call_provider",
        classmethod(fake_call),
    )
    monkeypatch.setattr(settings, "report_generation_max_retries", 0)

    result = await ReportGenerationService.generate_report(
        db=db_session,
        report_id=report.id,
        report_type="technical",
        force_refresh=False,
    )

    assert result["cached"] is False
    assert result["markdown"].startswith("# Markdown 1")
    assert call_counter["count"] == 1

    stored_reports = db_session.query(GeneratedReport).all()
    assert len(stored_reports) == 1
    assert stored_reports[0].markdown.startswith("# Markdown 1")

    cached = await ReportGenerationService.generate_report(
        db=db_session,
        report_id=report.id,
        report_type="technical",
        force_refresh=False,
    )

    assert cached["cached"] is True
    assert cached["markdown"] == result["markdown"]
    assert call_counter["count"] == 1

    refreshed = await ReportGenerationService.generate_report(
        db=db_session,
        report_id=report.id,
        report_type="technical",
        force_refresh=True,
    )

    assert refreshed["cached"] is False
    assert refreshed["markdown"].startswith("# Markdown 2")
    assert call_counter["count"] == 2

    db_session.refresh(stored_reports[0])
    assert stored_reports[0].markdown.startswith("# Markdown 2")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_report_provider_error_records_log(db_session, sample_domain, monkeypatch):
    _, report = sample_domain

    async def failing_call(cls, prompt_text):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(
        ReportGenerationService,
        "_call_provider",
        classmethod(failing_call),
    )
    monkeypatch.setattr(settings, "report_generation_max_retries", 0)

    with pytest.raises(ReportGenerationError):
        await ReportGenerationService.generate_report(
            db=db_session,
            report_id=report.id,
            report_type="technical",
            force_refresh=False,
        )

    logs = db_session.query(ReportGenerationLog).all()
    assert len(logs) == 1
    assert logs[0].status == "error"
    assert "boom" in (logs[0].error_message or "")


@pytest.mark.unit
def test_save_generated_report_persists_tags_and_metadata(db_session, sample_domain):
    _, report = sample_domain

    data = ReportGenerationService.save_generated_report(
        db=db_session,
        report_id=report.id,
        report_type="commercial",
        markdown="# Informe IA",
        tags=["cta", "prioridad"],
        metadata={"model": "lmstudio-test", "latency_ms": 1200},
    )

    assert data["type"] == "commercial"
    assert data["markdown"].startswith("# Informe IA")
    assert data["tags"] == ["cta", "prioridad"]
    assert data["metadata"]["model"] == "lmstudio-test"

    # Segundo guardado actualiza la misma fila sin duplicar
    updated = ReportGenerationService.save_generated_report(
        db=db_session,
        report_id=report.id,
        report_type="commercial",
        markdown="# Informe IA actualizado",
        tags=["cta"],
        metadata={"model": "lmstudio-test", "latency_ms": 800},
    )

    assert updated["markdown"].startswith("# Informe IA actualizado")
    assert updated["tags"] == ["cta"]
    assert updated["metadata"]["latency_ms"] == 800

    rows = db_session.query(GeneratedReport).filter(GeneratedReport.type == "commercial").all()
    assert len(rows) == 1
