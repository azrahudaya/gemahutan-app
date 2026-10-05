"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton, EmptyState, ErrorState } from "@/components/ui";
import { SitesMap, type MapLocalization } from "@/components/sites-map";
import { alasanTanpaArah } from "../arah";
import { ambilLokalisasi, batasLokalisasi, butuhKanalMinimal, type TugasLokalisasi } from "../lokalisasi";

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const admin = user?.role === "admin";

  const { data: site, isLoading, error } = useQuery({
    queryKey: ["site", id],
    queryFn: () => api.getSite(id),
  });

  // Koreksi lokasi dibatasi admin di API, jadi formulirnya hanya muncul untuk admin.
  const [form, setForm] = useState<Record<string, string>>({});
  const [pesan, setPesan] = useState<string | null>(null);

  const simpan = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.updateSite(id, payload),
    onSuccess: () => {
      setPesan("Perubahan tersimpan.");
      queryClient.invalidateQueries({ queryKey: ["site", id] });
      queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
    onError: (err) => setPesan((err as Error)?.message || "Gagal menyimpan perubahan"),
  });

  const hapus = useMutation({
    mutationFn: () => api.deleteSite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      router.replace("/sites");
    },
    onError: (err) => setPesan((err as Error)?.message || "Gagal menghapus lokasi"),
  });

  const { data: recordings } = useQuery({
    queryKey: ["recordings", { site_id: id }],
    queryFn: () => api.getRecordings({ site_id: String(id), page_size: "8" }),
  });

  const recordingList = recordings?.items ?? [];

  // Cakupan lokalisasi dilaporkan /model/info. Blok itu belum tentu ada, jadi
  // nilainya dibaca dengan hati-hati dan tidak dikarang.
  const { data: infoModel } = useQuery({
    queryKey: ["model-info-situs"],
    queryFn: () => api.getModelInfo(),
    staleTime: 300000,
  });

  const tugasLokalisasi: TugasLokalisasi[] = useMemo(() => {
    const lat = site?.latitude ?? null;
    const lon = site?.longitude ?? null;
    if (lat == null || lon == null) return [];
    return recordingList
      .filter((rec: any) => rec.status === "done")
      .map((rec: any) => ({
        recordingId: rec.id,
        lat,
        lon,
        detail: site?.name ?? "",
      }));
  }, [recordingList, site?.latitude, site?.longitude, site?.name]);

  const kunciTugas = tugasLokalisasi.map((t) => t.recordingId).join(",");

  const { data: lokalisasi = [] } = useQuery<MapLocalization[]>({
    queryKey: ["lokalisasi-situs", id, kunciTugas],
    queryFn: () => ambilLokalisasi(tugasLokalisasi),
    enabled: tugasLokalisasi.length > 0,
    staleTime: 60000,
  });

  const kanalMinimal = butuhKanalMinimal(infoModel);
  const batasArah = batasLokalisasi(infoModel);
  const adaArah = lokalisasi.some((l) => l.azimuth_deg != null);


  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="mb-6 h-48 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat detail lokasi."}
        />
      </div>
    );
  }

  if (!site) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <EmptyState
          title="Lokasi tidak ditemukan"
          message="Lokasi ini mungkin sudah dihapus. Kembali ke daftar lokasi untuk memilih yang lain."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link href="/sites" className="mb-4 inline-flex min-h-11 items-center text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] focus-ring rounded px-1">
        Kembali ke Lokasi
      </Link>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--foreground)]">{site.name}</h1>
            <p className="text-sm text-[var(--muted-foreground)]">{site.location || "-"}</p>
          </div>
          <span className={`inline-flex items-center rounded px-3 py-1.5 text-sm font-medium ${
            site.status === "active"
              ? "bg-[var(--primary-surface)] text-[var(--accent)]"
              : "bg-[var(--muted)] text-[var(--muted-foreground)]"
          }`}>
            {site.status === "active" ? "Ada rekaman 180 hari terakhir" : "Belum ada rekaman terbaru"}
          </span>
        </div>

        {admin && (
          <div className="mt-6 rounded-md border border-[var(--border)] bg-[var(--background)] p-4">
            <h2 className="text-sm font-medium text-[var(--foreground)]">Koreksi data lokasi</h2>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Sebelumnya nama dan keterangan lokasi tidak bisa diperbaiki sama sekali.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-[var(--muted-foreground)]">
                Nama
                <input
                  defaultValue={site.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="focus-ring mt-1 w-full rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </label>
              <label className="text-xs text-[var(--muted-foreground)]">
                Wilayah
                <input
                  defaultValue={site.location || ""}
                  onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                  className="focus-ring mt-1 w-full rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </label>
              <label className="text-xs text-[var(--muted-foreground)] sm:col-span-2">
                Keterangan
                <textarea
                  defaultValue={site.notes || ""}
                  rows={3}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  className="focus-ring mt-1 w-full rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </label>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => {
                  if (Object.keys(form).length === 0) {
                    setPesan("Tidak ada kolom yang diubah.");
                    return;
                  }
                  setPesan(null);
                  simpan.mutate(form);
                }}
                disabled={simpan.isPending}
                className="focus-ring min-h-11 rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
              >
                {simpan.isPending ? "Menyimpan" : "Simpan perubahan"}
              </button>
              <button
                onClick={() => {
                  const yakin = window.confirm(
                    `Hapus lokasi "${site.name}"? Lokasi yang masih dipakai rekaman akan ditolak.`
                  );
                  if (yakin) hapus.mutate();
                }}
                disabled={hapus.isPending}
                className="focus-ring min-h-11 rounded border border-[var(--destructive)] px-4 py-2 text-sm text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
              >
                {hapus.isPending ? "Menghapus" : "Hapus lokasi"}
              </button>
            </div>
            {pesan && (
              <p role="status" className="mt-2 text-xs text-[var(--muted-foreground)]">
                {pesan}
              </p>
            )}
          </div>
        )}

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-md border border-[var(--border)] bg-[var(--background)] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">Koordinat</p>
            <p className="mt-1 font-medium text-[var(--foreground)]">
              {site.latitude ? `${site.latitude.toFixed(6)}°` : "-"} <span className="text-[var(--muted-foreground)]">lat</span>
            </p>
            <p className="font-medium text-[var(--foreground)]">
              {site.longitude ? `${site.longitude.toFixed(6)}°` : "-"} <span className="text-[var(--muted-foreground)]">long</span>
            </p>
          </div>
          <div className="rounded-md border border-[var(--border)] bg-[var(--background)] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">Total Rekaman</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--primary-text)]">
              {site.recordings_count ?? 0}
            </p>
            <p className="text-xs text-[var(--muted-foreground)]">Rekaman dari lokasi ini</p>
          </div>
        </div>

        {site.description && (
          <div className="mt-6">
            <h2 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Deskripsi</h2>
            <p className="text-[var(--muted-foreground)]">{site.description}</p>
          </div>
        )}

        {site.elevation_m != null && (
          <div className="mt-4">
            <h2 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Ketinggian</h2>
            <p className="text-[var(--muted-foreground)]">{site.elevation_m} mdpl</p>
          </div>
        )}

        {site.latitude != null && site.longitude != null && (
          <div className="mt-6">
            <h2 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Peta</h2>
            <SitesMap
              sites={[
                {
                  id: site.id,
                  name: site.name,
                  lat: site.latitude,
                  lon: site.longitude,
                  habitat_type: site.habitat_type,
                },
              ]}
              localizations={lokalisasi}
              catatanArah={alasanTanpaArah(kanalMinimal)}
            />
            {lokalisasi.length > 0 && (
              <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                {lokalisasi.length} deteksi punya data lokalisasi dari {recordingList.length} rekaman
                terakhir di lokasi ini.
              </p>
            )}
            {!adaArah && batasArah.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-[var(--muted-foreground)]">
                {batasArah.slice(0, 3).map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {site.habitat_type && (
          <div className="mt-4">
            <h2 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Tipe Habitat</h2>
            <p className="text-[var(--muted-foreground)]">{site.habitat_type}</p>
          </div>
        )}

        {site.notes && (
          <div className="mt-4">
            <h2 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Catatan</h2>
            <p className="text-[var(--muted-foreground)]">{site.notes}</p>
          </div>
        )}

        {/* Recent Recordings */}
        {recordingList.length > 0 && (
          <div className="mt-8">
            <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">Rekaman Terakhir</h2>
            <div className="space-y-3">
              {recordingList.slice(0, 3).map((rec: any) => (
                <Link
                  key={rec.id}
                  href={`/recordings/${rec.id}`}
                  className="flex items-center justify-between rounded border border-[var(--border)] bg-[var(--background)] p-3 transition-colors hover:bg-[var(--muted)]"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-[var(--primary-surface)] text-xs font-medium text-[var(--primary-text)]">
                      {String(rec.id).slice(-2)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[var(--foreground)]">Rekaman #{rec.id}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        {rec.recorded_at ? new Date(rec.recorded_at).toLocaleDateString("id-ID") : "-"}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {rec.detection_count ?? 0} deteksi
                  </span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
