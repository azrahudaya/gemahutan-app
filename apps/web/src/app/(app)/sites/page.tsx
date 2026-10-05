"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/ui";
import { SitesMap, type MapLocalization, type MapSite } from "@/components/sites-map";
import { alasanTanpaArah } from "./arah";
import { ambilLokalisasi, type TugasLokalisasi } from "./lokalisasi";

export default function SitesPage() {
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [page, setPage] = useState(1);

  const params: Record<string, string> = { page: String(page), limit: "20" };
  if (name) params.name = name;
  if (location) params.location = location;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["sites", params],
    queryFn: () => api.getSites(params),
  });

  const sites = useMemo(
    () => data ?? [],
    [data]
  );
  // /api/v1/sites mengembalikan daftar penuh (bukan berpaginasi), jadi halaman
  // pagination tidak pernah muncul.
  const totalPages = 1;

  // Menambah dan mengubah lokasi adalah tindakan admin di API, jadi tombolnya
  // hanya muncul untuk admin. Kontrol yang pasti ditolak tidak ditampilkan.
  const admin = user?.role === "admin";

  // Peta butuh lokasi yang punya koordinat. Lokasi tanpa koordinat tetap
  // muncul di daftar, hanya tidak bisa digambar.
  const petaSites: MapSite[] = useMemo(
    () =>
      sites
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s) => ({
          id: s.id,
          name: s.name,
          lat: s.latitude as number,
          lon: s.longitude as number,
          habitat_type: s.habitat_type,
        })),
    [sites]
  );

  const koordinatPerSite = useMemo(() => {
    const peta = new Map<number, { lat: number; lon: number; nama: string }>();
    for (const s of sites) {
      if (s.latitude != null && s.longitude != null) {
        peta.set(s.id, { lat: s.latitude, lon: s.longitude, nama: s.name });
      }
    }
    return peta;
  }, [sites]);

  // Lokalisasi hanya diambil dari rekaman yang sudah selesai diproses. Satu
  // permintaan daftar rekaman, lalu deteksi per rekaman dibatasi di ambilLokalisasi.
  const { data: rekamanSelesai } = useQuery({
    queryKey: ["sites-peta-rekaman"],
    queryFn: () => api.getRecordings({ status: "done", page_size: "20" }),
    enabled: petaSites.length > 0,
    staleTime: 60000,
  });

  const daftarRekaman = rekamanSelesai?.items ?? [];
  const idRekamanPeta = daftarRekaman.map((r) => r.id).slice(0, 8).join(",");

  const { data: lokalisasi = [] } = useQuery<MapLocalization[]>({
    queryKey: ["sites-peta-lokalisasi", idRekamanPeta, petaSites.length],
    queryFn: async () => {
      const tugas: TugasLokalisasi[] = [];
      for (const rec of daftarRekaman) {
        const titik = koordinatPerSite.get(rec.site_id);
        if (!titik) continue;
        tugas.push({
          recordingId: rec.id,
          lat: titik.lat,
          lon: titik.lon,
          detail: titik.nama,
        });
      }
      return ambilLokalisasi(tugas);
    },
    enabled: daftarRekaman.length > 0 && petaSites.length > 0,
    staleTime: 60000,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">Lokasi Perekaman</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Kelola dan pantau semua lokasi monitoring hutan
          </p>
        </div>
        {admin ? (
          <Link
            href="/sites/new"
            className="focus-ring inline-flex min-h-11 items-center justify-center rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)]"
          >
            Tambah Lokasi
          </Link>
        ) : (
          <p className="text-xs text-[var(--muted-foreground)]">
            Menambah lokasi butuh peran admin
          </p>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input
          type="text"
          placeholder="Nama lokasi..."
          value={name}
          onChange={(e) => { setName(e.target.value); setPage(1); }}
          className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          aria-label="Filter nama lokasi"
        />
        <input
          type="text"
          placeholder="Kota/provinsi..."
          value={location}
          onChange={(e) => { setLocation(e.target.value); setPage(1); }}
          className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          aria-label="Filter lokasi"
        />
      </div>

      {/* Peta lokasi dengan arah datang dan jangkauan, kalau datanya ada. */}
      {!isLoading && !isError && petaSites.length > 0 && (
        <section className="mb-6">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold text-[var(--foreground)]">Peta Lokasi</h2>
            <p className="text-xs text-[var(--muted-foreground)]">
              {petaSites.length} lokasi berkoordinat ditampilkan
              {sites.length - petaSites.length > 0
                ? `, ${sites.length - petaSites.length} lokasi belum punya koordinat`
                : ""}
            </p>
          </div>
          <SitesMap
            sites={petaSites}
            localizations={lokalisasi}
            catatanArah={alasanTanpaArah(null)}
          />
        </section>
      )}

      {/* Sites Grid */}
      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat daftar lokasi."}
          onRetry={() => refetch()}
        />
      ) : sites.length === 0 ? (
        <EmptyState
          title={name || location ? "Tidak ada lokasi yang cocok" : "Belum ada lokasi monitoring"}
          message={
            name || location
              ? "Ubah kata kunci filter atau kosongkan kolom pencarian."
              : "Tambahkan lokasi pertama supaya rekaman bisa dikaitkan dengan titik perekaman."
          }
          action={
            name || location || !admin ? null : (
              <Link
                href="/sites/new"
                className="focus-ring inline-flex min-h-11 items-center rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)]"
              >
                Tambah Lokasi
              </Link>
            )
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sites.map((site) => (
            <Link
              key={site.id}
              href={`/sites/${site.id}`}
              className="group flex flex-col rounded-lg border border-[var(--border)] bg-[var(--card)] p-5 transition-colors hover:border-[var(--ring)] hover:bg-[var(--card-hover)]"
            >
              <div className="flex items-start justify-between">
                <h3 className="text-lg font-medium text-[var(--foreground)]">
                  {site.name}
                </h3>
                <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                  site.status === "active"
                    ? "bg-[var(--primary-surface)] text-[var(--accent)]"
                    : "bg-[var(--muted)] text-[var(--muted-foreground)]"
                }`}>
                  {site.status === "active" ? "Ada rekaman terbaru" : "Belum ada rekaman terbaru"}
                </span>
              </div>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                {site.location || "-"}
              </p>
              <div className="mt-3 flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                <span>{site.latitude != null ? `${site.latitude.toFixed(4)} derajat` : "-"}</span>
                <span>{site.longitude != null ? `${site.longitude.toFixed(4)} derajat` : "-"}</span>
              </div>
              {site.description && (
                <p className="mt-3 text-sm text-[var(--muted-foreground)] line-clamp-2">
                  {site.description}
                </p>
              )}
              <div className="mt-auto pt-4 border-t border-[var(--border)]">
                <p className="text-xs text-[var(--muted-foreground)]">
                  {site.recordings_count ?? 0} rekaman
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground)] disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            Sebelumnya
          </button>
          <span className="text-sm text-[var(--muted-foreground)]">
            Halaman {page} dari {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground)] disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            Selanjutnya
          </button>
        </div>
      )}
    </div>
  );
}
