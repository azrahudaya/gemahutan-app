import { Easing, useCurrentFrame, useVideoConfig } from "remotion";
import FOTO from "@/lib/foto-burung.json";

/*
 * Token bersama untuk video cara kerja. Warna mengambil variabel tema daisyUI dari
 * halaman, jadi video ikut tema "gemahutan" tanpa salinan kode warna.
 * Semua posisi adalah gambar ilustrasi di bidang panggung 680 x 500 piksel, bukan data.
 */

export const WARNA = {
  primer: "var(--color-primary)",
  aksen: "var(--color-accent)",
  lembut: "var(--color-secondary)",
  dasar: "var(--color-base-100)",
  dasar2: "var(--color-base-200)",
  garis: "var(--color-base-300)",
  teks: "var(--color-base-content)",
  redup: "color-mix(in oklab, var(--color-base-content) 62%, transparent)",
  galat: "var(--color-error)",
};

export const FONT = "var(--font-sans, 'Plus Jakarta Sans', ui-sans-serif, system-ui, sans-serif)";

export const PANGGUNG = { w: 680, h: 500 };

export const BURUNG = FOTO[1];
export const POS_BURUNG = { x: 300, y: 215 };
export const POS_SERVER = { x: 590, y: 64 };
export const ALAT = [
  { id: "A", x: 112, y: 112 },
  { id: "B", x: 410, y: 86 },
  { id: "C", x: 520, y: 372 },
  { id: "D", x: 150, y: 384 },
];

// Video diputar 60 fps supaya gerak halus. Waktu adegan ditulis dalam satuan 1/30 detik,
// lalu dikali SKALA untuk jadi bingkai sungguhan.
export const FPS = 60;
const SKALA = FPS / 30;
const DURASI_30 = { rekam: 84, kirim: 78, pilah: 90, kenali: 78, peta: 100 };
const TRANSISI_30 = 18;
export const DURASI = {
  rekam: DURASI_30.rekam * SKALA,
  kirim: DURASI_30.kirim * SKALA,
  pilah: DURASI_30.pilah * SKALA,
  kenali: DURASI_30.kenali * SKALA,
  peta: DURASI_30.peta * SKALA,
};
export const TRANSISI = TRANSISI_30 * SKALA;
export const TOTAL_FRAME =
  DURASI.rekam + DURASI.kirim + DURASI.pilah + DURASI.kenali + DURASI.peta - 4 * TRANSISI;

/* Bingkai saat ini dalam satuan 1/30 detik, apa pun fps pemutarnya. */
export function useWaktu() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (frame * 30) / fps;
}

// Satu bahasa gerak untuk semua adegan: masuk dan keluar melambat (ease in-out),
// kemunculan diberi sedikit lentingan yang tetap lembut.
export const KELUAR = Easing.bezier(0.65, 0, 0.35, 1);
export const LENTUR = Easing.bezier(0.34, 1.22, 0.64, 1);
export const HALUS = Easing.bezier(0.45, 0, 0.55, 1);
