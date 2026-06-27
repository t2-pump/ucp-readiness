# Use the official Python image
FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
COPY . .

# Copy andInstall requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium
RUN sed -i '/<head>/a \
    <meta name="description" content="Audit your product pages for AI-Commerce UCP and GEO compliance."> \
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-5RH0NXCVYT"></script> \
    <script> \
    window.dataLayer = window.dataLayer || []; \
    function gtag(){dataLayer.push(arguments);} \
    gtag("js", new Date()); \
    gtag("config", "G-5RH0NXCVYT", {"send_page_view": true}); \
    </script>' /usr/local/lib/python3.11/site-packages/streamlit/static/index.html
RUN sed -i '/<body>/a \
    <h1 style="display:none;">AI-Commerce UCP & GEO Audit | T2 Digital</h1> \
    <p style="display:none;">Compliance testing for the 2026 Universal Commerce Protocol and Generative Engine Optimization.</p>' \
    /usr/local/lib/python3.11/site-packages/streamlit/static/index.html

# Ensure the .streamlit config folder is included
COPY .streamlit/ .streamlit/

# Streamlit runs on port 8080 by default in Cloud Run
EXPOSE 8080

# Command to run the app using shell form to expand the Render $PORT variable
CMD streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0