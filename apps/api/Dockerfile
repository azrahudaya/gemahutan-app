FROM python:3.11-slim

WORKDIR /app

# Build context is the repository root, so the image also carries ml/ (artefak
# model dan laporan evaluasi) yang dipakai /healthz dan /api/v1/model/info.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./requirements.txt
# Indeks paket dibuat bisa diatur. Di jaringan tempat proyek ini dikerjakan,
# pypi.org terukur 18,9 kB/s sementara mirror Aliyun 1,33 MB/s, jadi build yang
# tidak diarahkan ke mirror bisa menggantung puluhan menit. Nilai bawaannya tetap
# PyPI resmi supaya tidak ada pihak ketiga yang dipakai tanpa disadari.
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt

COPY apps/api/ ./
COPY ml/ /app/ml/

ENV ML_DIR=/app/ml

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
