# FastAPI + HTML (Jinja2)

## Requisitos
- Python 3.10+

## Instalación
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install playwright==1.48.0
playwright install chromium 
```

## Ejecutar
```bash
uvicorn app.main:app --reload
```
