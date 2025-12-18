FROM python:3.13-slim

# Install system build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    libcairo2-dev \
    libjpeg-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of your code
COPY . .

# Command to run the app
CMD ["uvicorn", "core.app:app", "--host", "0.0.0.0", "--port", "8000"]
