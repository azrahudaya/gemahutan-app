/**
 * Perhitungan arah dan jangkauan untuk tampilan peta.
 *
 * Fungsi murni tanpa DOM supaya bisa diuji tanpa peramban. Semua sudut memakai
 * derajat dengan 0 = utara dan bertambah searah jarum jam, sama dengan kolom
 * `azimuth_deg` di API.
 */

export const ARAH_MATA_ANGIN = [
  "utara",
  "timur laut",
  "timur",
  "tenggara",
  "selatan",
  "barat daya",
  "barat",
  "barat laut",
] as const;

/** Ubah azimuth jadi nama mata angin terdekat (delapan arah). */
export function arahMataAngin(derajat: number): string {
  const d = ((derajat % 360) + 360) % 360;
  return ARAH_MATA_ANGIN[Math.round(d / 45) % 8];
}

/** Kalimat keterangan arah, atau null kalau datanya belum ada. */
export function labelArah(derajat: number | null | undefined): string | null {
  if (derajat == null || !Number.isFinite(derajat)) return null;
  const d = ((derajat % 360) + 360) % 360;
  return `${d.toFixed(1)} derajat, ${arahMataAngin(d)}`;
}

/** Jarak dalam satuan yang enak dibaca, atau null kalau datanya belum ada. */
export function labelJangkauan(meter: number | null | undefined): string | null {
  if (meter == null || !Number.isFinite(meter) || meter <= 0) return null;
  if (meter >= 1000) return `${(meter / 1000).toFixed(2)} km`;
  return `${meter.toFixed(0)} m`;
}

/**
 * Cincin koordinat lingkaran dengan radius meter di sekitar satu titik.
 * Dipakai menggambar perkiraan jangkauan deteksi. Rumusnya datar, cukup untuk
 * radius pendek di dalam satu lokasi pemantauan, bukan untuk bola bumi penuh.
 */
export function lingkaranJangkauan(
  lat: number,
  lon: number,
  radiusM: number,
  langkah = 64
): [number, number][] {
  const derajatPerMeterLat = 1 / 111320;
  const cosLat = Math.max(0.01, Math.cos((lat * Math.PI) / 180));
  const derajatPerMeterLon = derajatPerMeterLat / cosLat;
  const ring: [number, number][] = [];
  for (let i = 0; i <= langkah; i += 1) {
    const sudut = (i / langkah) * Math.PI * 2;
    ring.push([
      lon + Math.cos(sudut) * radiusM * derajatPerMeterLon,
      lat + Math.sin(sudut) * radiusM * derajatPerMeterLat,
    ]);
  }
  return ring;
}

/**
 * Kenapa arah datang belum bisa ditampilkan. Dipakai halaman lokasi supaya
 * pengguna tidak mengira peta rusak padahal datanya memang belum ada.
 */
export function alasanTanpaArah(butuhKanalMinimal: number | null): string {
  if (butuhKanalMinimal && butuhKanalMinimal > 1) {
    return `Deteksi di lokasi ini belum punya arah datang. Estimasi arah butuh rekaman minimal ${butuhKanalMinimal} kanal dengan jarak antar mikrofon yang diketahui, sedangkan rekaman sekarang mono satu kanal. Yang bisa ditampilkan hanya perkiraan jangkauan.`;
  }
  return "Deteksi di lokasi ini belum punya arah datang. API belum mengirim kolom azimuth untuk deteksi mana pun di sini, jadi peta hanya menampilkan titik lokasi. Posisi arah tidak ditebak.";
}

/** Bentuk data lokalisasi yang dipakai peta. Strukturnya sama dengan MapLocalization. */
export interface LokalisasiPeta {
  key: string;
  lat: number;
  lon: number;
  azimuth_deg: number | null;
  range_m: number | null;
  label: string;
  detail?: string;
}

export interface DeteksiLokalisasi {
  id?: number | null;
  species_common?: string | null;
  species_name?: string | null;
  azimuth_deg?: number | null;
  range_m?: number | null;
  localization_engine?: string | null;
}

/**
 * Deteksi layak digambar di peta kalau salah satu kolom lokalisasinya benar-benar
 * berisi angka. Nol derajat adalah arah yang sah (utara), jadi nol tidak dianggap
 * kosong. Hanya null dan undefined yang dianggap belum ada.
 */
export function punyaLokalisasi(det: DeteksiLokalisasi): boolean {
  return typeof det.azimuth_deg === "number" || typeof det.range_m === "number";
}

/** Ubah deteksi satu rekaman jadi data peta, dengan titik perekaman sebagai acuan. */
export function petakanLokalisasi(
  titik: { recordingId: number; lat: number; lon: number; detail?: string },
  deteksi: DeteksiLokalisasi[]
): LokalisasiPeta[] {
  const hasil: LokalisasiPeta[] = [];
  for (const det of deteksi) {
    if (!punyaLokalisasi(det)) continue;
    const nama = det.species_common || det.species_name || "Deteksi belum bernama";
    hasil.push({
      key: `${titik.recordingId}-${det.id ?? hasil.length}`,
      lat: titik.lat,
      lon: titik.lon,
      azimuth_deg: typeof det.azimuth_deg === "number" ? det.azimuth_deg : null,
      range_m: typeof det.range_m === "number" ? det.range_m : null,
      label: nama,
      detail: [
        titik.detail,
        `rekaman #${titik.recordingId}`,
        det.localization_engine ? `mesin ${det.localization_engine}` : null,
      ]
        .filter(Boolean)
        .join(", "),
    });
  }
  return hasil;
}
