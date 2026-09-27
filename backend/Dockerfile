FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --default-timeout=180 \
    --retries=10 \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    torch==2.13.0+cpu
RUN pip install --no-cache-dir \
    --default-timeout=180 \
    --retries=10 \
    -r requirements.txt
COPY app ./app
RUN mkdir -p /app/data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
