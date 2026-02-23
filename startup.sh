#!/bin/bash
# Azure App Service startup script for Slide Guide Generator (Streamlit)

streamlit run app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
