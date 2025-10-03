# FastAPI + HTML (Jinja2)

## Requisitos
- Python 3.10+

## Instalación
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar
```bash
uvicorn app.main:app --reload
```

Luego abre: http://127.0.0.1:8000/

## Estructura
```
.
├─ app/
│  └─ main.py
├─ templates/
│  └─ index.html
├─ static/
│  └─ style.css
├─ requirements.txt
└─ README.md
```
