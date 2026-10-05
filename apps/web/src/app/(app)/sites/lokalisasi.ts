import { api } from "@/lib/api";
import type { MapLocalization } from "@/components/sites-map";
import { petakanLokalisasi, type DeteksiLokalisasi } from "./arah";

/**
 * Mengambil data lokalisasi deteksi untuk peta.
 *
 * API belum punya endpoint lokalisasi per lokasi, jadi deteksi diambil per
 * rekaman. Jumlah rekaman yang dipanggil dibatasi supaya halaman tidak
 * menghujani server dengan puluhan permintaan sekaligus.
 *
 * Penyaringan dan pemetaan datanya ada di arah.ts sebagai fungsi murni supaya
 * bisa diuji tanpa peramban.
 */
export interface TugasLokalisasi {
  recordingId: number;
  lat: number;
  lon: number;
  /** Keterangan tambahan, misalnya nama lokasi atau tanggal rekaman. */
  detail?: string;
}

const MAKS_REKAMAN = 8;

export async function ambilLokalisasi(tugas: TugasLokalisasi[]): Promise<MapLocalization[]> {
  const dibatasi = tugas.slice(0, MAKS_REKAMAN);
  if (dibatasi.length === 0) return [];

  const balasan = await Promise.allSettled(
    dibatasi.map((t) => api.getDetections(String(t.recordingId)))
  );

  const hasil: MapLocalization[] = [];
  balasan.forEach((b, i) => {
    if (b.status !== "fulfilled" || !Array.isArray(b.value)) return;
    hasil.push(...petakanLokalisasi(dibatasi[i], b.value as DeteksiLokalisasi[]));
  });

  return hasil;
}

/** Ambang kanal minimal dari blok localization di /model/info, kalau ada. */
export function butuhKanalMinimal(infoModel: unknown): number | null {
  const blok = (infoModel as { localization?: { butuh_kanal_minimal?: unknown } } | null)
    ?.localization;
  const nilai = blok?.butuh_kanal_minimal;
  return typeof nilai === "number" ? nilai : null;
}

/** Batas lokalisasi yang dilaporkan API, dipakai sebagai catatan di halaman lokasi. */
export function batasLokalisasi(infoModel: unknown): string[] {
  const blok = (infoModel as { localization?: { batas?: unknown } } | null)?.localization;
  const daftar = blok?.batas;
  if (!Array.isArray(daftar)) return [];
  return daftar.filter((b): b is string => typeof b === "string");
}
