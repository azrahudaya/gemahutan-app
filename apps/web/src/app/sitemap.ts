import type { MetadataRoute } from "next";

const BASE = process.env.NEXT_PUBLIC_SITE_URL || "https://gemahutan.site";

export default function sitemap(): MetadataRoute.Sitemap {
  const terakhir = new Date();
  return [
    { url: `${BASE}/`, lastModified: terakhir, changeFrequency: "monthly", priority: 1 },
    { url: `${BASE}/dokumentasi`, lastModified: terakhir, changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/tentang`, lastModified: terakhir, changeFrequency: "yearly", priority: 0.5 },
  ];
}
