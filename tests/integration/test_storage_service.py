import pytest

from app.models import Domain
from app.services.storage_service import StorageService


@pytest.mark.integration
def test_save_report_creates_domain(db_session):
    data = {
        "domain": "http://pytest-create.com",
        "status_code": 200,
        "success": True,
        "seo": {"title": "Create", "links": {"total": 1}, "images": {"total": 0}},
        "tech": {"requests": {"count": 1, "total_bytes": 123}, "timing": {}},
        "security": {},
        "site": {"pages_crawled": 1, "forms_found": 0},
        "pages": [],
    }

    report = StorageService.save_report(db_session, "pytest-create.com", data)

    domain = db_session.query(Domain).filter_by(domain="pytest-create.com").one()
    assert domain.total_reports == 1
    assert report.domain_id == domain.id


@pytest.mark.integration
def test_get_domain_reports_and_latest(db_session):
    for word_count in (100, 150):
        data = {
            "domain": "http://pytest-history.com",
            "status_code": 200,
            "success": True,
            "seo": {"title": "History", "wordCount": word_count, "links": {"total": 1}, "images": {"total": 0}},
            "tech": {"requests": {"count": 1, "total_bytes": 123}, "timing": {}},
            "security": {},
            "site": {"pages_crawled": 1, "forms_found": 0},
            "pages": [],
        }
        StorageService.save_report(db_session, "pytest-history.com", data)

    reports = StorageService.get_domain_reports(db_session, "pytest-history.com")
    assert len(reports) == 2
    assert reports[0].scraped_at >= reports[1].scraped_at

    latest = StorageService.get_latest_report(db_session, "pytest-history.com")
    assert latest.seo_word_count == 150


@pytest.mark.integration
def test_delete_old_reports_keeps_latest(db_session):
    for idx in range(5):
        data = {
            "domain": "http://pytest-cleanup.com",
            "status_code": 200,
            "success": True,
            "seo": {"title": f"Run {idx}", "links": {"total": 1}, "images": {"total": 0}},
            "tech": {"requests": {"count": 1, "total_bytes": 123}, "timing": {}},
            "security": {},
            "site": {"pages_crawled": 1, "forms_found": 0},
            "pages": [],
        }
        StorageService.save_report(db_session, "pytest-cleanup.com", data)

    deleted = StorageService.delete_old_reports(db_session, "pytest-cleanup.com", keep_latest=2)

    remaining = StorageService.get_domain_reports(db_session, "pytest-cleanup.com")
    assert deleted == 3
    assert len(remaining) == 2
