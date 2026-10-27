FROM python:3.14-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
 && python -m pip uninstall -y pip setuptools wheel

COPY . .

# Unprivileged runtime user. A numeric UID lets Kubernetes enforce runAsNonRoot.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001:10001

CMD ["python", "detector.py"]