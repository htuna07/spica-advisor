FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY spica_advisor ./spica_advisor

# GitHub Actions mounts the repository here and requires container actions to run as root.
WORKDIR /github/workspace

ENTRYPOINT ["python", "/app/main.py"]
