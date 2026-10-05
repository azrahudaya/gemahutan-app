FROM python:3.11-slim

WORKDIR /app

# Build context is the repository root. ml/ wajib ikut karena engine cascade
# (BirdNET + classifier Track B) dan threshold per spesies ada di sana.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY apps/worker/requirements.txt ./requirements.txt
# tensorflow-cpu sendiri 274 MB, dan unduhan dari PyPI di jaringan kampus sering
# terputus di tengah. Cache BuildKit membuat percobaan ulang melanjutkan dari
# wheel yang sudah selesai, bukan mengunduh ulang semuanya.
ENV PIP_RETRIES=10 \
    PIP_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# Indeks paket dibuat bisa diatur, sama seperti image api. Di jaringan ini
# pypi.org terukur 18,9 kB/s sedangkan mirror Aliyun 1,33 MB/s, dan tensorflow-cpu
# sendiri 274 MB, jadi tanpa pengarahan ini build bisa menggantung lama.
# Nilai bawaannya tetap PyPI resmi.
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url "$PIP_INDEX_URL" -r requirements.txt

COPY apps/worker/worker.py ./worker.py
COPY apps/worker/healthcheck_worker.py ./healthcheck_worker.py
COPY ml/ /app/ml/

# Test logika worker (konversi audio, penyaringan deteksi) dijalankan di image ini
# lewat `make test-worker`. pytest hanya dipakai untuk itu.
COPY apps/worker/pytest.ini ./pytest.ini
COPY apps/worker/tests/ ./tests/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "pytest>=8.0,<9"

ENV ML_DIR=/app/ml
ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python healthcheck_worker.py || exit 1

CMD ["arq", "worker.WorkerSettings"]
