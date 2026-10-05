"""Test endpoint baca: healthz, recordings, species, stats, sites, model, errors."""
import pytest


@pytest.mark.anyio
async def test_healthz_ok_when_services_up(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    for service in ("db", "redis", "storage"):
        assert data["services"][service] == "up"
    # Status model harus berasal dari artefak/heartbeat, bukan konstanta "pending".
    assert data["services"]["model"] in ("up", "degraded", "unavailable")
    assert "model_detail" in data


@pytest.mark.anyio
async def test_recordings_requires_auth(client):
    resp = await client.get("/api/v1/recordings")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_recordings_list_shape(client, auth_headers):
    resp = await client.get("/api/v1/recordings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data and "total" in data
    for item in data["items"]:
        assert "detection_count" in item
        assert "site_name" in item


@pytest.mark.anyio
async def test_species_list_and_detail(client, auth_headers):
    resp = await client.get("/api/v1/species", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    species = resp.json()
    assert isinstance(species, list)
    assert len(species) > 0
    assert "scientific_name" in species[0]

    sp_id = species[0]["id"]
    resp = await client.get(f"/api/v1/species/{sp_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == sp_id

    resp = await client.get("/api/v1/species/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats_endpoints(client, peneliti_headers):
    resp = await client.get("/api/v1/stats/overview", headers=peneliti_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    for key in ("recordings", "detections", "species_detected", "sites"):
        assert key in data

    resp = await client.get("/api/v1/stats/species", headers=peneliti_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = await client.get("/api/v1/stats/timeline", headers=peneliti_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_sites_crud(client, admin_headers):
    import uuid

    name = f"Lokasi Uji {uuid.uuid4().hex[:6]}"

    resp = await client.post("/api/v1/sites", headers=admin_headers, json={
        "name": name,
        "latitude": -6.55,
        "longitude": 106.75,
        "location": "Bogor, Jawa Barat",
        "habitat_type": "tropical_rainforest",
        "elevation_m": 850,
        "description": "Lokasi uji otomatis",
    })
    assert resp.status_code == 201, resp.text
    site = resp.json()
    assert site["name"] == name
    assert site["latitude"] == pytest.approx(-6.55)
    assert site["longitude"] == pytest.approx(106.75)
    assert site["elevation_m"] == 850
    assert site["recordings_count"] == 0
    assert site["status"] in ("active", "inactive")
    site_id = site["id"]

    # Nama duplikat ditolak
    resp = await client.post("/api/v1/sites", headers=admin_headers, json={"name": name})
    assert resp.status_code == 409

    # Latitude tanpa longitude ditolak
    resp = await client.post("/api/v1/sites", headers=admin_headers, json={
        "name": f"{name} b",
        "latitude": -6.1,
    })
    assert resp.status_code == 400

    resp = await client.get(f"/api/v1/sites/{site_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == site_id

    resp = await client.get("/api/v1/sites", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    listed = resp.json()
    assert isinstance(listed, list)
    assert any(s["id"] == site_id for s in listed)

    resp = await client.get("/api/v1/sites", headers=admin_headers, params={"name": name})
    assert resp.status_code == 200
    assert all(name.lower() in s["name"].lower() for s in resp.json())

    resp = await client.get("/api/v1/sites/999999", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_model_info_reports_real_artifacts(client):
    resp = await client.get("/api/v1/model/info")
    assert resp.status_code == 200, resp.text
    info = resp.json()
    assert info["status"] in ("up", "degraded", "unavailable")
    assert "status_detail" in info
    tracks = {t["id"]: t for t in info["tracks"]}
    assert set(tracks) == {"A", "B"}
    assert tracks["B"]["species_count"] >= 0
    assert "metrics" in info


@pytest.mark.anyio
async def test_missing_resources_return_404(client, auth_headers):
    resp = await client.get("/api/v1/recordings/999999", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.get("/api/v1/recordings/999999/detections", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Spektrogram dan audio untuk rekaman yang tidak ada: 404 jelas, bukan 500
    # dari dalam library audio. Indeks soundscape 403 untuk ranger (uji
    # terpisah di test_peran_analis.py).
    for path in ("spectrogram", "audio"):
        resp = await client.get(f"/api/v1/recordings/999999/{path}", headers=auth_headers)
        assert resp.status_code == 404, f"{path}: {resp.status_code}"


@pytest.mark.anyio
async def test_verify_detection_not_found(client, peneliti_headers):
    # Peran yang berhak, supaya yang diuji benar-benar 404 dan bukan 403.
    resp = await client.post(
        "/api/v1/detections/999999/verify", headers=peneliti_headers, json={"status": "correct"}
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_upload_rejects_bad_extension(client, auth_headers):
    files = {"file": ("catatan.txt", b"bukan audio", "text/plain")}
    data = {"site_id": "1"}
    resp = await client.post(
        "/api/v1/recordings", headers=auth_headers, files=files, data=data
    )
    assert resp.status_code == 400
    assert "tidak didukung" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_recordings_filters_and_pagination(client, auth_headers):
    """Filter harus benar-benar menyaring dan paginasi mengembalikan total_pages."""
    semua = await client.get("/api/v1/recordings", headers=auth_headers)
    assert semua.status_code == 200
    semua_data = semua.json()
    assert "total_pages" in semua_data
    total_semua = semua_data["total"]

    # page_size dihormati
    kecil = await client.get(
        "/api/v1/recordings", headers=auth_headers, params={"page_size": 2}
    )
    assert kecil.status_code == 200
    kecil_data = kecil.json()
    assert len(kecil_data["items"]) <= 2
    assert kecil_data["page_size"] == 2
    assert kecil_data["total_pages"] == max(1, (total_semua + 1) // 2)

    # filter status
    selesai = await client.get(
        "/api/v1/recordings", headers=auth_headers, params={"status": "done"}
    )
    assert selesai.status_code == 200
    for item in selesai.json()["items"]:
        assert item["status"] == "done"

    # filter status yang tidak dikenal ditolak
    resp = await client.get(
        "/api/v1/recordings", headers=auth_headers, params={"status": "ngawur"}
    )
    assert resp.status_code == 422

    # tanggal tidak valid ditolak dengan pesan jelas
    resp = await client.get(
        "/api/v1/recordings", headers=auth_headers, params={"from": "bukan-tanggal"}
    )
    assert resp.status_code == 400
    assert "YYYY-MM-DD" in resp.json()["detail"]

    # filter lokasi menyaring
    lokasi = await client.get("/api/v1/sites", headers=auth_headers)
    sites = lokasi.json()
    if sites:
        site_id = sites[0]["id"]
        terfilter = await client.get(
            "/api/v1/recordings", headers=auth_headers, params={"site": site_id}
        )
        assert terfilter.status_code == 200
        for item in terfilter.json()["items"]:
            assert item["site_id"] == site_id
        assert terfilter.json()["total"] <= total_semua


@pytest.mark.anyio
async def test_species_detections_endpoint(client, auth_headers):
    species = (await client.get("/api/v1/species", headers=auth_headers)).json()
    sp_id = species[0]["id"]

    resp = await client.get(f"/api/v1/species/{sp_id}/detections", headers=auth_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    for row in rows:
        assert set(row) >= {
            "detection_id", "recording_id", "confidence", "start_s", "end_s",
            "verified_status",
        }
        assert row["confidence"] <= 1


@pytest.mark.anyio
async def test_jobs_list_and_retry(client, auth_headers, peneliti_headers):
    recordings = (await client.get("/api/v1/recordings", headers=auth_headers)).json()
    if not recordings["items"]:
        return
    rid = recordings["items"][0]["id"]

    resp = await client.get("/api/v1/jobs", headers=auth_headers, params={"recording_id": rid})
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)
    if jobs:
        assert jobs[0]["recording_id"] == rid
        assert jobs[0]["status"] in ("pending", "running", "done", "failed")

    # filter status job
    resp = await client.get("/api/v1/jobs", headers=auth_headers, params={"status": "ngawur"})
    assert resp.status_code == 422

    resp = await client.post("/api/v1/jobs/999999/retry", headers=peneliti_headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_exports(client, peneliti_headers):
    resp = await client.get("/api/v1/exports/recordings", headers=peneliti_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    header = resp.text.splitlines()[0]
    assert header.startswith("recording_id,site_name,status")
    assert "verified_detections" in header

    resp = await client.get("/api/v1/exports/verified", headers=peneliti_headers)
    assert resp.status_code == 200
    assert resp.text.splitlines()[0].startswith("detection_id,recording_id")

    resp = await client.get(
        "/api/v1/exports/verified", headers=peneliti_headers, params={"format": "json"}
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # status tidak dikenal ditolak
    resp = await client.get(
        "/api/v1/exports/verified", headers=peneliti_headers, params={"status": "ngawur"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_exports_need_auth(client):
    resp = await client.get("/api/v1/exports/verified")
    assert resp.status_code in (401, 403)
