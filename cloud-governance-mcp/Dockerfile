FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 10001 appuser && \
    mkdir -p /home/appuser/.streamlit && \
    printf '[browser]\ngatherUsageStats = false\n[client]\nshowErrorDetails = false\n' > /home/appuser/.streamlit/config.toml

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mcp_server.py ./
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
