FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home jrock \
    && mkdir -p /app/data /app/workspace && chown -R jrock:jrock /app/data /app/workspace
USER jrock
CMD ["jrock", "run"]
