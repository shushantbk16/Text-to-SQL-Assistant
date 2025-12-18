# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Pre-download the embedding model to bake it into the image
RUN python download_model.py

# Expose the port Streamlit runs on
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
