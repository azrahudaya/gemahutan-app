/**
 * Pemformat tampilan yang dipakai beberapa halaman.
 *
 * Dipisah dari komponen supaya bisa diuji tanpa menjalankan React, dan supaya
 * aturan tampilannya satu tempat: nilai kosong selalu tampil sebagai tanda
 * hubung, bukan "NaN" atau "Invalid Date".
 */

export function formatTanggal(iso?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString("id-ID");
}

export function formatDurasi(detik?: number | null): string {
  if (detik == null || Number.isNaN(detik)) return "-";
  if (detik < 60) return `${Math.round(detik)} detik`;
  const menit = Math.floor(detik / 60);
  const sisa = Math.round(detik - menit * 60);
  return `${menit} menit ${sisa} detik`;
}

export function formatKeyakinan(nilai?: number | null): string {
  if (nilai == null || Number.isNaN(nilai)) return "-";
  return `${(nilai * 100).toFixed(1)}%`;
}

const LABEL_STATUS: Record<string, string> = {
  done: "Selesai",
  processing: "Diproses",
  pending: "Antre",
  running: "Berjalan",
  failed: "Gagal",
};

export function labelStatus(status?: string | null): string {
  if (!status) return "-";
  return LABEL_STATUS[status] || status;
}

/**
 * Label tahap job. Daftar tahapnya ditetapkan kontrak dan dipakai worker,
 * jadi terjemahan tampilannya dikumpulkan di sini supaya semua halaman
 * menyebut tahap yang sama persis.
 */
const LABEL_TAHAP: Record<string, string> = {
  antre: "Menunggu antrean",
  unduh: "Mengunduh berkas",
  dekode: "Membaca audio",
  birdnet: "Deteksi BirdNET",
  klasifikasi: "Klasifikasi spesies",
  lokalisasi: "Menghitung arah",
  indeks: "Menghitung indeks",
  spektrogram: "Membuat spektrogram",
  selesai: "Selesai",
  gagal: "Gagal",
};

export function labelTahap(tahap?: string | null): string {
  if (!tahap) return "Belum mulai";
  return LABEL_TAHAP[tahap] || tahap;
}

/** Urutan tahap sesuai kontrak, dipakai untuk menandai langkah yang sudah lewat. */
export const TAHAP_URUT = [
  "antre",
  "unduh",
  "dekode",
  "birdnet",
  "klasifikasi",
  "lokalisasi",
  "indeks",
  "spektrogram",
  "selesai",
] as const;

export function indeksTahap(tahap?: string | null): number {
  if (!tahap) return -1;
  return (TAHAP_URUT as readonly string[]).indexOf(tahap);
}

/** Progres dari API dijepit ke 0 sampai 100 supaya bilah tidak pernah melebar. */
export function normalisasiProgres(nilai?: number | null): number {
  if (nilai == null || Number.isNaN(nilai)) return 0;
  return Math.min(100, Math.max(0, Math.round(nilai)));
}

const ARAH_MATA_ANGIN = [
  "Utara",
  "Timur Laut",
  "Timur",
  "Tenggara",
  "Selatan",
  "Barat Daya",
  "Barat",
  "Barat Laut",
] as const;

/**
 * Ubah azimuth jadi arah mata angin delapan penjuru.
 * Nilai null berarti arah belum dihitung, bukan nol derajat, jadi hasilnya
 * tanda hubung dan bukan "Utara".
 */
export function formatArahMataAngin(derajat?: number | null): string {
  if (derajat == null || Number.isNaN(derajat)) return "-";
  const normal = ((derajat % 360) + 360) % 360;
  return ARAH_MATA_ANGIN[Math.round(normal / 45) % 8];
}

export function formatDerajat(derajat?: number | null, angkaDesimal = 1): string {
  if (derajat == null || Number.isNaN(derajat)) return "-";
  return `${derajat.toFixed(angkaDesimal)}°`;
}

export function formatJarak(meter?: number | null): string {
  if (meter == null || Number.isNaN(meter)) return "-";
  if (Math.abs(meter) < 1000) return `${Math.round(meter)} m`;
  return `${(meter / 1000).toFixed(1)} km`;
}
