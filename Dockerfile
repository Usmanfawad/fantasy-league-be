# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory in the container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . /app

# Install the necessary packages
# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Expose the port that the app will run on
EXPOSE 8000

# Optional container-level healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,sys,urllib.request; u=os.environ.get('HEALTHCHECK_URL','http://127.0.0.1:8000/healthz');\n\
    \n\
    (lambda: (lambda r: sys.exit(0 if r.getcode()==200 else 1))(urllib.request.urlopen(u,timeout=2)))()" || exit 1

# Run the application when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]