FROM python:3.11-slim

WORKDIR /app

RUN mkdir -p /root/.streamlit && \
    printf '[browser]\ngatherUsageStats = false\n[client]\nshowErrorDetails = true\n' > /root/.streamlit/config.toml

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mcp_server.py ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
