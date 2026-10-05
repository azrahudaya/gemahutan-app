/**
 * Aturan unggah batch dan ringkasan hasilnya.
 *
 * Dipisah dari halaman supaya bisa diuji tanpa React: batas dua puluh berkas,
 * daftar ekstensi yang benar-benar diterima API, dan hitungan selesai atau
 * gagal semuanya fungsi murni di sini.
 */

/** Batas berkas sekali unggah, sama dengan batas field `files` di API. */
export const MAKS_BERKAS_BATCH = 20;

/**
 * Ekstensi yang diterima API. `webm` ikut karena rekaman dari peramban
 * dikirim apa adanya sebagai audio/webm.
 */
export const EKSTENSI_AUDIO = ["wav", "mp3", "flac", "ogg", "m4a", "aac", "opus", "webm"];

/** Tipe MIME yang diterima API, dipakai untuk menyaring sebelum diunggah. */
export const TIPE_AUDIO = [
  "audio/wav",
  "audio/x-wav",
  "audio/wave",
  "audio/mpeg",
  "audio/mp3",
  "audio/flac",
  "audio/x-flac",
  "audio/ogg",
  "audio/opus",
  "audio/mp4",
  "audio/m4a",
  "audio/x-m4a",
  "audio/aac",
  "audio/webm",
  "application/octet-stream",
];

export interface BerkasMasuk {
  name: string;
  type?: string;
}

export interface BerkasDitolak {
  nama: string;
  alasan: string;
}

export interface HasilSaring {
  diterima: BerkasMasuk[];
  ditolak: BerkasDitolak[];
  /** Jumlah berkas yang diabaikan karena melewati batas maksimal. */
  dipotong: number;
}

export function ekstensiBerkas(nama: string): string {
  const bersih = (nama || "").trim().toLowerCase();
  const titik = bersih.lastIndexOf(".");
  if (titik < 0 || titik === bersih.length - 1) return "";
  return bersih.slice(titik + 1);
}

export function alasanTolak(berkas: BerkasMasuk): string | null {
  const nama = bersihkanNama(berkas.name);
  if (!nama) return "Nama berkas kosong";
  const ekstensi = ekstensiBerkas(nama);
  if (!ekstensi) return "Berkas tidak punya ekstensi audio";
  if (!EKSTENSI_AUDIO.includes(ekstensi)) {
    return `Ekstensi .${ekstensi} tidak didukung, pakai ${EKSTENSI_AUDIO.join(", ")}`;
  }
  const tipe = (berkas.type || "").toLowerCase();
  if (tipe && !tipe.startsWith("audio/") && tipe !== "application/octet-stream") {
    return `Tipe berkas ${tipe} bukan audio`;
  }
  return null;
}

function bersihkanNama(nama: string): string {
  return (nama || "").trim();
}

/**
 * Saring daftar berkas: yang tidak didukung dikembalikan berikut alasannya,
 * dan kelebihannya dipotong supaya tidak ada kontrol yang pasti ditolak API.
 */
export function saringBerkasAudio(
  berkas: BerkasMasuk[],
  maks: number = MAKS_BERKAS_BATCH
): HasilSaring {
  const daftar = Array.isArray(berkas) ? berkas : [];
  const hasil: HasilSaring = { diterima: [], ditolak: [], dipotong: 0 };

  for (const item of daftar) {
    const nama = bersihkanNama(item?.name || "");
    const alasan = alasanTolak({ name: nama, type: item?.type });
    if (alasan) {
      hasil.ditolak.push({ nama: nama || "(tanpa nama)", alasan });
      continue;
    }
    if (hasil.diterima.length >= maks) {
      hasil.dipotong += 1;
      continue;
    }
    hasil.diterima.push({ name: nama, type: item?.type });
  }

  return hasil;
}

export interface BerkasBatch {
  filename?: string | null;
  recording_id?: number | null;
  status?: string | null;
  progress?: number | null;
  stage?: string | null;
  error?: string | null;
}

export interface RingkasanBatch {
  total: number;
  selesai: number;
  gagal: number;
  diproses: number;
  menunggu: number;
}

/**
 * Ringkas status berkas dalam satu batch. Status yang belum dikenal dihitung
 * sebagai menunggu, bukan diabaikan, supaya totalnya selalu cocok dengan
 * jumlah berkas yang dikirim.
 */
export function ringkasBatch(items?: BerkasBatch[] | null): RingkasanBatch {
  const daftar = Array.isArray(items) ? items : [];
  const ringkasan: RingkasanBatch = {
    total: daftar.length,
    selesai: 0,
    gagal: 0,
    diproses: 0,
    menunggu: 0,
  };

  for (const item of daftar) {
    switch (item?.status) {
      case "done":
        ringkasan.selesai += 1;
        break;
      case "failed":
        ringkasan.gagal += 1;
        break;
      case "processing":
        ringkasan.diproses += 1;
        break;
      default:
        ringkasan.menunggu += 1;
    }
  }

  return ringkasan;
}

/** Batch dianggap selesai kalau semua berkas sudah selesai atau gagal. */
export function batchSelesai(items?: BerkasBatch[] | null): boolean {
  const ringkasan = ringkasBatch(items);
  return ringkasan.total > 0 && ringkasan.selesai + ringkasan.gagal === ringkasan.total;
}

export function kalimatRingkasan(ringkasan: RingkasanBatch): string {
  if (ringkasan.total === 0) return "Belum ada berkas pada batch ini.";
  const bagian = [`${ringkasan.selesai} selesai`, `${ringkasan.gagal} gagal`];
  if (ringkasan.diproses > 0) bagian.push(`${ringkasan.diproses} sedang diproses`);
  if (ringkasan.menunggu > 0) bagian.push(`${ringkasan.menunggu} menunggu antrean`);
  return `Dari ${ringkasan.total} berkas: ${bagian.join(", ")}.`;
}
