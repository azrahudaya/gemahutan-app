import type { MetadataRoute } from "next";

/**
 * Halaman publik boleh diindeks, area kerja setelah login dan seluruh API tidak.
 * Ini bukan pengamanan: token tetap yang menahan akses. Ini hanya mencegah
 * halaman kosong tanpa data ikut masuk hasil pencarian.
 */
export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL || "https://gemahutan.site";
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/dokumentasi", "/tentang"],
        disallow: ["/api/", "/dashboard", "/recordings", "/sites", "/upload", "/rekam", "/devices", "/admin", "/model", "/laporan", "/login", "/register"],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
  };
}
