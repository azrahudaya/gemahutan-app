import type { MetadataRoute } from "next";

/**
 * Manifest PWA. Dipakai browser untuk memasang aplikasi ke layar utama.
 *
 * Warna tema hijau hutan gelap. DESIGN.md hanya mengunci shell gelap dan dua
 * warna aksi (biru elektrik dan mint), jadi hijau di sini dipakai khusus untuk
 * bilah chrome peramban, bukan untuk teks atau tombol di dalam aplikasi, supaya
 * aturan kontras di DESIGN.md tetap berlaku.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GemaHutan",
    short_name: "GemaHutan",
    description:
      "Pemantauan satwa hutan Indonesia lewat suara: unggah rekaman, deteksi spesies, dan verifikasi ahli.",
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#FFFFFF",
    theme_color: "#FFFFFF",
    lang: "id",
    dir: "ltr",
    categories: ["productivity", "utilities", "education"],
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
