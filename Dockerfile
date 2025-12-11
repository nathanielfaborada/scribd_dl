FROM python:3.13-slim

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium

# Copy backend code
COPY src/ .

# Expose port
EXPOSE 8080

# Run FastAPI using Railway PORT
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
