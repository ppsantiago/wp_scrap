"""Service for AI-powered report generation."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import Report, ReportPrompt, ReportGenerationLog, GeneratedReport
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class ReportGenerationError(Exception):
    """Domain-specific error for report generation."""


class ReportGenerationService:
    """Encapsulates orchestration logic for AI report generation workflows."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "technical": (
            "You are an expert technical SEO and web performance consultant. "
            "Analyze the following scraped data and deliver a concise, actionable technical report.\n\n"
            "## Context\n"
            "- Domain: {domain}\n"
            "- Report ID: {report_id}\n"
            "- Scraped at: {scraped_at}\n"
            "- Status code: {status_code}\n"
            "- Success: {success}\n\n"
            "## Data\n"
            "SEO metrics: {seo_metrics}\n"
            "Technical metrics: {tech_metrics}\n"
            "Security headers: {security_headers}\n"
            "Site summary: {site_summary}\n"
            "Key pages: {pages_summary}\n\n"
            "## Instructions\n"
            "- Use Markdown.\n"
            "- Include headings: Overview, Technical Findings, SEO Findings, Security & Risks, Recommendations.\n"
            "- Prioritize actionable insights with bullet points.\n"
            "- Highlight any missing critical elements."
        ),
        "commercial": (
            "You are a sales engineer preparing a commercial brief for stakeholders.\n\n"
            "Summarize the website's business positioning and opportunities based on the provided data.\n\n"
            "## Context\n"
            "Domain: {domain}\nReport ID: {report_id}\nScraped at: {scraped_at}\n\n"
            "## Guidance\n"
            "- Use Markdown with sections: Executive Summary, Audience & Positioning, Differentiators, Conversion Opportunities, Recommended Next Steps.\n"
            "- Keep tone persuasive yet factual.\n"
            "- Highlight quick wins for commercial teams.\n"
            "- Use bullet points and short paragraphs.\n\n"
            "## Key Signals\n"
            "Business highlights: {business_summary}\n"
            "Calls to action: {cta_summary}\n"
            "Lead capture forms: {forms_summary}\n"
            "Social proof & testimonials: {testimonials}\n"
        ),
        "deliverable": (
            "Create a client-facing deliverable summarizing the domain assessment.\n\n"
            "## Requirements\n"
            "- Format as Markdown with clear headings and tables when helpful.\n"
            "- Sections: Introduction, Site Snapshot, Strengths, Risks, Suggested Plan.\n"
            "- Keep language accessible for non-technical stakeholders.\n"
            "- Provide prioritized roadmap with time horizon (short, medium, long term).\n\n"
            "## Inputs\n"
            "Domain: {domain}\n"
            "Report ID: {report_id}\n"
            "Scraped at: {scraped_at}\n"
            "SEO metrics: {seo_metrics}\n"
            "Technical metrics: {tech_metrics}\n"
            "Security headers: {security_headers}\n"
            "Business summary: {business_summary}\n"
            "Forms overview: {forms_summary}\n"
        ),
    }

    SUPPORTED_TYPES = tuple(DEFAULT_PROMPTS.keys())

    @classmethod
    def _normalize_type(cls, report_type: str) -> str:
        normalized = (report_type or "").strip().lower()
        if normalized not in cls.DEFAULT_PROMPTS:
            raise ReportGenerationError(
                f"Tipo de reporte '{report_type}' no soportado. Opciones: {', '.join(cls.DEFAULT_PROMPTS)}"
            )
        return normalized

    @classmethod
    def ensure_default_prompts(cls, db: Session) -> None:
        """Seed default prompt templates when missing."""
        now = datetime.utcnow()
        for prompt_type, template in cls.DEFAULT_PROMPTS.items():
            existing = (
                db.query(ReportPrompt)
                .filter(ReportPrompt.type == prompt_type)
                .first()
            )
            if existing:
                continue
            logger.info("Seeding default prompt template for '%s'", prompt_type)
            db.add(
                ReportPrompt(
                    type=prompt_type,
                    prompt_template=template,
                    updated_at=now,
                    updated_by="system",
                )
            )
        db.commit()

    @classmethod
    def list_prompts(cls, db: Session) -> list[dict[str, Any]]:
        prompts = db.query(ReportPrompt).order_by(ReportPrompt.type.asc()).all()
        if not prompts:
            cls.ensure_default_prompts(db)
            prompts = db.query(ReportPrompt).order_by(ReportPrompt.type.asc()).all()
        return [prompt.to_dict() for prompt in prompts]

    @classmethod
    def upsert_prompts(cls, db: Session, updates: list[dict[str, Any]], updated_by: Optional[str] = None) -> list[dict[str, Any]]:
        if not updates:
            return cls.list_prompts(db)

        for payload in updates:
            report_type = cls._normalize_type(payload.get("type", ""))
            template = payload.get("prompt_template")
            if not template or not template.strip():
                raise ReportGenerationError("El prompt_template no puede estar vacío")

            prompt = (
                db.query(ReportPrompt)
                .filter(ReportPrompt.type == report_type)
                .first()
            )
            if not prompt:
                prompt = ReportPrompt(type=report_type)
                db.add(prompt)

            prompt.prompt_template = template
            prompt.updated_by = payload.get("updated_by") or updated_by
            prompt.updated_at = datetime.utcnow()

        db.commit()
        return cls.list_prompts(db)

    @classmethod
    def _fetch_report(cls, db: Session, report_id: int) -> Report:
        report = StorageService.get_report_by_id(db, report_id)
        if not report:
            raise ReportGenerationError(f"Reporte {report_id} no encontrado")
        return report

    @classmethod
    def _get_prompt(cls, db: Session, report_type: str) -> ReportPrompt:
        prompt = (
            db.query(ReportPrompt)
            .filter(ReportPrompt.type == report_type)
            .first()
        )
        if not prompt:
            cls.ensure_default_prompts(db)
            prompt = (
                db.query(ReportPrompt)
                .filter(ReportPrompt.type == report_type)
                .first()
            )
        if not prompt:
            raise ReportGenerationError(f"Prompt para tipo '{report_type}' no encontrado")
        return prompt

    @classmethod
    def _build_context(cls, report: Report) -> Dict[str, Any]:
        frontend_data = report.to_frontend_format()
        metrics = report.to_dict(include_full_data=False).get("metrics", {})
        site = report.get_json_data("site_data") or {}
        pages = report.get_json_data("pages_data") or []

        pages_summary = [
            {
                "url": page.get("url"),
                "type": page.get("type"),
                "title": page.get("title"),
            }
            for page in pages[:10]
        ]

        forms = site.get("forms", {}) if isinstance(site.get("forms"), dict) else {}
        forms_overview = {
            "total": forms.get("count"),
            "integrations": forms.get("integrations"),
        }
        business = site.get("business_summary") or {}
        ctas = site.get("cta_highlights") or []
        testimonials = business.get("testimonials") if isinstance(business, dict) else []

        return {
            "domain": frontend_data.get("domain"),
            "report_id": report.id,
            "scraped_at": report.scraped_at.isoformat() if report.scraped_at else None,
            "status_code": frontend_data.get("status_code"),
            "success": frontend_data.get("success"),
            "seo_metrics": json.dumps(metrics, ensure_ascii=False, indent=2) if metrics else "{}",
            "tech_metrics": json.dumps(frontend_data.get("tech"), ensure_ascii=False, indent=2)
            if frontend_data.get("tech")
            else "{}",
            "security_headers": json.dumps(frontend_data.get("security"), ensure_ascii=False, indent=2)
            if frontend_data.get("security")
            else "{}",
            "site_summary": json.dumps(site, ensure_ascii=False, indent=2) if site else "{}",
            "pages_summary": json.dumps(pages_summary, ensure_ascii=False, indent=2) if pages_summary else "[]",
            "business_summary": json.dumps(business, ensure_ascii=False, indent=2) if business else "{}",
            "forms_summary": json.dumps(forms_overview, ensure_ascii=False, indent=2) if forms_overview else "{}",
            "cta_summary": json.dumps(ctas, ensure_ascii=False, indent=2) if ctas else "[]",
            "testimonials": json.dumps(testimonials, ensure_ascii=False, indent=2) if testimonials else "[]",
        }

    @classmethod
    def _render_prompt(cls, template: str, context: Dict[str, Any]) -> str:
        try:
            return template.format(**context)
        except KeyError as exc:
            missing = exc.args[0]
            raise ReportGenerationError(
                f"Variable '{missing}' ausente en el contexto del prompt"
            ) from exc

    @classmethod
    def _cache_lookup(
        cls,
        db: Session,
        report_id: int,
        report_type: str,
    ) -> Optional[ReportGenerationLog]:
        ttl_minutes = settings.report_generation_cache_ttl_minutes
        if ttl_minutes <= 0:
            return None
        cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
        return (
            db.query(ReportGenerationLog)
            .filter(
                ReportGenerationLog.report_id == report_id,
                ReportGenerationLog.type == report_type,
                ReportGenerationLog.status == "success",
                ReportGenerationLog.created_at >= cutoff,
                ReportGenerationLog.markdown_output.isnot(None),
            )
            .order_by(ReportGenerationLog.created_at.desc())
            .first()
        )

    @classmethod
    async def _call_provider(cls, prompt_text: str) -> dict[str, Any]:
        payload = {
            "model": settings.lmstudio_model,
            "messages": [
                {"role": "system", "content": "You are an expert AI writing assistant."},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": settings.report_generation_temperature,
            "stream": False,
        }

        headers = {"Content-Type": "application/json"}
        if settings.lmstudio_api_key:
            headers["Authorization"] = f"Bearer {settings.lmstudio_api_key}"

        timeout = settings.report_generation_timeout
        base_url = settings.lmstudio_base_url.rstrip("/")
        endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url

        logger.debug("Sending prompt to LMStudio endpoint %s", endpoint)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    @classmethod
    def _parse_response(cls, response: dict[str, Any]) -> Dict[str, Any]:
        choices = response.get("choices") or []
        if not choices:
            raise ReportGenerationError("Respuesta del proveedor IA sin contenido")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise ReportGenerationError("No se encontró contenido generado en la respuesta IA")

        usage = response.get("usage", {})
        tokens = usage.get("total_tokens") or usage.get("completion_tokens")

        return {"markdown": content, "tokens": tokens, "raw": response}

    @classmethod
    async def generate_report(
        cls,
        db: Session,
        report_id: int,
        report_type: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        normalized_type = cls._normalize_type(report_type)
        report = cls._fetch_report(db, report_id)

        if not force_refresh:
            cached = cls._cache_lookup(db, report_id, normalized_type)
            if cached:
                logger.info(
                    "Returning cached report generation for report=%s type=%s", report_id, normalized_type
                )
                return {
                    "report_id": report_id,
                    "type": normalized_type,
                    "cached": True,
                    "markdown": cached.markdown_output,
                    "generated_at": cached.created_at.isoformat() if cached.created_at else None,
                    "tokens_used": cached.tokens_used,
                    "duration_ms": cached.duration_ms,
                }

        prompt = cls._get_prompt(db, normalized_type)
        context = cls._build_context(report)
        prompt_text = cls._render_prompt(prompt.prompt_template, context)

        start = time.perf_counter()
        metadata: Dict[str, Any] = {
            "report_type": normalized_type,
            "report_id": report_id,
        }

        try:
            response = await cls._call_provider(prompt_text)
            result = cls._parse_response(response)
            duration_ms = int((time.perf_counter() - start) * 1000)

            log_entry = ReportGenerationLog(
                report_id=report_id,
                prompt_id=prompt.id,
                type=normalized_type,
                status="success",
                duration_ms=duration_ms,
                tokens_used=result.get("tokens"),
                cached=False,
                markdown_output=result.get("markdown"),
                metadata=json.dumps(metadata | {"provider_response_id": response.get("id")}, ensure_ascii=False),
            )
            db.add(log_entry)
            generated_output = cls._save_generated_report(
                db=db,
                report=report,
                report_type=normalized_type,
                markdown=result.get("markdown"),
                metadata=result.get("raw"),
            )
            db.commit()

            return {
                "report_id": report_id,
                "type": normalized_type,
                "cached": False,
                "markdown": generated_output.get("markdown"),
                "generated_at": generated_output.get("updated_at") or generated_output.get("created_at"),
                "tokens_used": log_entry.tokens_used,
                "duration_ms": log_entry.duration_ms,
                "tags": generated_output.get("tags"),
                "metadata": generated_output.get("metadata"),
            }

        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            db.add(
                ReportGenerationLog(
                    report_id=report_id,
                    prompt_id=prompt.id,
                    type=normalized_type,
                    status="error",
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    cached=False,
                    error_message=str(exc),
                    metadata=json.dumps(metadata, ensure_ascii=False),
                )
            )
            db.commit()
            logger.exception("HTTP error while generating report %s type %s", report_id, normalized_type)
            raise ReportGenerationError(f"Error comunicándose con el proveedor IA: {exc}") from exc
        except ReportGenerationError:
            raise
        except Exception as exc:  # pragma: no cover - unexpected errors
            db.add(
                ReportGenerationLog(
                    report_id=report_id,
                    prompt_id=prompt.id,
                    type=normalized_type,
                    status="error",
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    cached=False,
                    error_message=str(exc),
                    metadata=json.dumps(metadata, ensure_ascii=False),
                )
            )
            db.commit()
            logger.exception("Unexpected error while generating report %s type %s", report_id, normalized_type)
            raise ReportGenerationError("Ocurrió un error inesperado generando el reporte IA") from exc

    @classmethod
    def _save_generated_report(
        cls,
        db: Session,
        report: Report,
        report_type: str,
        markdown: str,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        if not markdown:
            raise ReportGenerationError("La respuesta del proveedor IA no contiene markdown")

        normalized_type = cls._normalize_type(report_type)

        row = (
            db.query(GeneratedReport)
            .filter(
                GeneratedReport.report_id == report.id,
                GeneratedReport.type == normalized_type,
            )
            .first()
        )

        if not row:
            row = GeneratedReport(report_id=report.id, type=normalized_type)
            db.add(row)

        row.markdown = markdown
        row.set_metadata(metadata)
        row.set_tags(tags)

        db.flush()
        return row.to_dict()

    @classmethod
    def save_generated_report(
        cls,
        db: Session,
        report_id: int,
        report_type: str,
        markdown: str,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        report = cls._fetch_report(db, report_id)
        data = cls._save_generated_report(
            db=db,
            report=report,
            report_type=report_type,
            markdown=markdown,
            metadata=metadata,
            tags=tags,
        )
        db.commit()
        return data

    @classmethod
    def list_generated_reports(
        cls,
        db: Session,
        report_id: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = (
            db.query(GeneratedReport)
            .filter(GeneratedReport.report_id == report_id)
            .order_by(GeneratedReport.created_at.desc())
            .limit(limit)
            .all()
        )
        return [row.to_dict() for row in rows]

    @classmethod
    def get_generated_report(
        cls,
        db: Session,
        report_id: int,
        report_type: str,
    ) -> dict[str, Any]:
        normalized_type = cls._normalize_type(report_type)
        row = (
            db.query(GeneratedReport)
            .filter(
                GeneratedReport.report_id == report_id,
                GeneratedReport.type == normalized_type,
            )
            .first()
        )
        if not row:
            raise ReportGenerationError(
                f"No hay reporte IA guardado para report_id={report_id} tipo={normalized_type}"
            )
        return row.to_dict()


__all__ = ["ReportGenerationService", "ReportGenerationError"]
