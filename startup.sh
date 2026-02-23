#!/bin/bash
# Azure App Service startup script for Slide Guide Generator (Streamlit)

# Install poppler-utils (needed by pdf2image for PDF → slide image conversion)
apt-get update -qq && apt-get install -y -qq poppler-utils

# Start Streamlit on the port Azure expects
streamlit run app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
