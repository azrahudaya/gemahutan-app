import http from "k6/http";
import { check } from "k6";
import { Trend } from "k6/metrics";

// Uji beban unggah GemaHutan ke STACK LOKAL (bukan produksi).
// Tiap virtual user mengunggah satu klip WAV 15 detik ke /api/v1/recordings
// memakai satu akun admin yang tokennya dibuat sekali di setup.
//
// Pakai:
//   k6 run --vus 10 --iterations 10 ops/beban/unggah.js
//   k6 run --vus 25 --iterations 25 ops/beban/unggah.js
//   k6 run --vus 50 --iterations 50 ops/beban/unggah.js

const BASE = __ENV.BASE_URL || "http://localhost:8000";

// Trend khusus durasi unggah (tanpa login).
const unggahDurasi = new Trend("unggah_durasi", true);

// Klip WAV 15 detik dibaca sekali di init stage.
const BERKAS = open("/tmp/gemahutan-beban.wav", "b");

export function setup() {
  const login = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ email: "admin@gemahutan.id", password: "admin123" }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (login.status !== 200) {
    throw new Error(`login gagal: ${login.status} ${login.body}`);
  }
  const token = login.json().access_token;
  const sites = http.get(`${BASE}/api/v1/sites`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const daftar = sites.json();
  if (!Array.isArray(daftar) || !daftar[0]) {
    throw new Error("tidak ada lokasi untuk unggah");
  }
  return { token, siteId: daftar[0].id };
}

export default function (data) {
  const body = {
    file: http.file(BERKAS, "beban.wav", "audio/wav"),
    site_id: String(data.siteId),
  };
  const res = http.post(`${BASE}/api/v1/recordings`, body, {
    headers: { Authorization: `Bearer ${data.token}` },
    timeout: "120s",
  });
  unggahDurasi.add(res.timings.duration);
  check(res, {
    "unggah diterima (201/202)": (r) => r.status === 201 || r.status === 202,
  });
}
