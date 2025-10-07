import os
import pytest
from sqlalchemy import text

from app.database import SessionLocal, init_db
from app.main import app
from app.models import Domain, Report
from app.services.storage_service import StorageService
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def test_db_dir(tmp_path_factory):
    """Configura un directorio temporal para la base de datos de pruebas."""
    db_dir = tmp_path_factory.mktemp("db")
    os.environ["DB_DIR"] = str(db_dir)
    init_db()
    return db_dir


@pytest.fixture(autouse=True)
def clean_database(test_db_dir):
    """Limpia tablas principales antes y después de cada prueba."""
    with SessionLocal() as session:
        session.execute(text("DELETE FROM comments"))
        session.execute(text("DELETE FROM reports"))
        session.execute(text("DELETE FROM domains"))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(text("DELETE FROM comments"))
        session.execute(text("DELETE FROM reports"))
        session.execute(text("DELETE FROM domains"))
        session.commit()


@pytest.fixture()
def db_session(test_db_dir):
    """Crea una sesión aislada por prueba."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# TODO: exponer una fixture Playwright para escenarios e2e.


@pytest.fixture()
def sample_domain(db_session):
    """Crea un dominio y reporte base para pruebas de integración."""
    report_data = {
        "domain": "http://pytest-example.com",
        "status_code": 200,
        "success": True,
        "seo": {
            "title": "Pytest Site",
            "metaDescription": "",
            "wordCount": 100,
            "links": {"total": 2, "internal": 1, "external": 1, "nofollow": 0},
            "images": {"total": 1, "withoutAlt": 0},
        },
        "tech": {
            "requests": {"count": 5, "total_bytes": 10000},
            "timing": {"ttfb": 50, "dcl": 100, "load": 150},
        },
        "security": {"headers": {}},
        "site": {"pages_crawled": 1, "forms_found": 0},
        "pages": [],
    }

    report = StorageService.save_report(
        db=db_session,
        domain_name="pytest-example.com",
        report_data=report_data,
    )

    yield report.domain, report

    db_session.query(Report).filter(Report.domain_id == report.domain_id).delete()
    db_session.query(Domain).filter(Domain.id == report.domain_id).delete()
    db_session.commit()


@pytest.fixture()
def client(test_db_dir):
    """Cliente de pruebas FastAPI con DB temporal."""
    return TestClient(app)


@pytest.fixture(scope="session")
def base_url():
    """URL base para pruebas e2e."""
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def playwright_browser():
    """Inicializa Playwright si RUN_E2E=1; de lo contrario omite las pruebas."""
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("RUN_E2E no está habilitado; omitiendo pruebas e2e")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=os.getenv("E2E_HEADLESS", "1") == "1"
        )
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture()
def e2e_page(playwright_browser, base_url):
    """Página Playwright aislada para cada prueba e2e."""
    context = playwright_browser.new_context(base_url=base_url)
    page = context.new_page()
    try:
        yield page
    finally:
        page.close()
        context.close()
