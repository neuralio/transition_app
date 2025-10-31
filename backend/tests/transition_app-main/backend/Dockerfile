# Use an official Python runtime as the base image
FROM python:3.13-alpine

# Set the working directory
WORKDIR /backend

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "-m", "uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]

