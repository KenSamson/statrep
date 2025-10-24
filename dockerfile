FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["flet", "run", "statrep_flet_app_v3_prod.py", "--port", "8000", "--web"]