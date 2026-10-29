# syntax=docker/dockerfile:1.7
#
# CarWebScraper — obraz uruchomieniowy.
# Zawiera Chromium (Playwright, scraping Otomoto) i Camoufox (Firefox, mobile.de + enrichment).
# Dane i konfiguracja są poza obrazem: /data (volume) i /config (queries.json, preferences.json).

FROM python:3.13-slim-bookworm

ARG VERSION=dev
ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="carwebscraper" \
      org.opencontainers.image.description="Scraper ogłoszeń samochodowych ze scoringiem, enrichmentem, LLM i powiadomieniami" \
      org.opencontainers.image.source="https://github.com/MaciejSz89/car-web-scraper" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    CARSCRAPER_HEADLESS=1 \
    CARSCRAPER_DATA_DIR=/data \
    CARSCRAPER_CONFIG_DIR=/config

COPY --from=ghcr.io/astral-sh/uv:0.10.8 /uv /uvx /bin/

WORKDIR /app

# 1. Zależności Pythona (warstwa cache'owana, dopóki nie zmieni się uv.lock)
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Chromium + jego biblioteki systemowe; biblioteki dla Camoufox (Firefox)
RUN playwright install --with-deps chromium \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 libx11-xcb1 fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

# 3. Użytkownik bez uprawnień root; Camoufox pobierany do jego cache
#    (`camoufox fetch` zapisuje też bazę GeoIP do katalogu pakietu, stąd chown)
RUN useradd --create-home --uid 1000 app \
 && mkdir -p /data /config \
 && chown app:app /data /config \
 && chown -R app:app /opt/venv/lib/python3.13/site-packages/camoufox
USER app
RUN python -m camoufox fetch

# 4. Kod aplikacji (najczęściej zmieniana warstwa — na końcu)
COPY --chown=app:app otomoto-scraper ./otomoto-scraper
COPY --chown=app:app analyze.py ./

VOLUME ["/data"]

ENTRYPOINT ["python", "otomoto-scraper/main.py"]
CMD ["--run-enrichment", "--run-notifications", "--loop"]
