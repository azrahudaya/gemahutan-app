.PHONY: help up down test test-di-db-dev lint logs train eval clean demo seed migrate health security-check sync-thresholds backup verify

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all images
	docker compose build

test: ## Run API tests (basis data test terpisah, TIDAK menyentuh data dev)
	bash ops/db_test.sh test

test-di-db-dev: ## Test di basis data dev (cara lama, menumpuk data uji di sana)
	docker compose exec api python -m pytest tests/ -v

test-snapshot: ## Run model snapshot test (10 klip gold, drift > 0.10 -> FAIL)
	docker compose exec api python -m pytest tests/test_model_snapshot.py -v

test-worker: ## Run worker tests (konversi audio, penyaring deteksi)
	docker compose exec worker python -m pytest tests/ -q

seed: ## Seed species, lokasi, dan user dasar
	docker compose exec api python -m app.seed

demo: ## Isi 8 rekaman demo dari klip Xeno-canto asli lalu proses lewat worker
	docker compose exec api python -m app.seed_demo --purge-orphans

demo-purge: ## Hapus data demo lama yang berkas audionya tidak ada, lalu seed ulang
	docker compose exec api python -m app.seed_demo --purge --purge-orphans

lint: ## Lint semua kode Python
	docker run --rm -v $(PWD):/src -w /src gemahutan-api:latest python -m ruff check .

security-check: ## Periksa keamanan stack yang sedang hidup (endpoint, token, port, rahasia)
	python3 ops/security_check.py

verify: ## Periksa fitur Fase 2 lewat HTTP, PASS atau GAGAL per butir
	python3 ops/verify_features.py


sync-thresholds: ## Salin ambang hasil kalibrasi ke kolom species.default_threshold
	python3 ops/sync_thresholds.py

backup: ## Dump database dan salin audio ke ops/backups/tanggal
	bash ops/backup.sh

logs: ## Tail all logs
	docker compose logs -f --tail=50

train: ## Run ML training (butuh dataset di ml/data/audio)
	cd ml && python train.py

eval: ## Run ML evaluation
	cd ml && python evaluate.py

model: ## Ekstrak embedding + latih ulang classifier Track B
	cd ml && python data/extract_embeddings.py && python train.py && python evaluate.py

download: ## Download dataset Xeno-canto
	cd ml/data && python download.py

migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

health: ## Check health endpoint
	curl -sf http://localhost:8000/healthz | python -m json.tool

model-produksi: ## Bangun ulang checkpoint produksi lalu bandingkan sha256 dengan MANIFEST
	.venv/bin/python ml/save_logreg.py --emb-dir ml/embeddings_v3 \
		--splits ml/data/splits_v3.json --ckpt-in ml/checkpoints_langka \
		--out-dir ml/runs/reproduksi --report-dir ml/runs/reproduksi/reports \
		--seed 2024 --C 1.0 --maks-negatif 3000
	@echo "Membandingkan sha256 dengan MANIFEST..."
	@.venv/bin/python -c "import json,hashlib; m=json.load(open('ml/checkpoints/MANIFEST.json')); exp=m['files']['best_model.npz']['sha256']; got=hashlib.sha256(open('ml/runs/reproduksi/best_model.npz','rb').read()).hexdigest(); print('expected', exp); print('got     ', got); print('SAMA' if exp==got else 'BERBEDA'); raise SystemExit(0 if exp==got else 1)"
