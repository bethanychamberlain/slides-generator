FROM python:3.11-slim-bookworm

# System dependency for PDF-to-image rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only (no docs, tests, configs)
COPY app.py ai.py auth.py cache.py questions.py usage_logger.py \
     export_docx.py export_pdf.py export_html.py export_qti.py \
     icon.png ./

# Create data directory for volume mount
RUN mkdir -p /data

# Streamlit configuration
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    DATA_DIR=/data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
