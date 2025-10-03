FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy 
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN playwright install-deps
RUN playwright install chromium
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload"]