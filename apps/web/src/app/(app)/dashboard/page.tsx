"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { CardSkeleton, Skeleton, EmptyState, ErrorState } from "@/components/ui";
import { SitesMap } from "@/components/sites-map";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts";

export default function DashboardPage() {
  const {
    data: overview,
    isLoading: loadingOverview,
    isError: overviewError,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ["stats-overview"],
    queryFn: () => api.getStatsOverview(),
  });

  const { data: speciesStats, isLoading: loadingSpecies, isError: speciesError } = useQuery({
    queryKey: ["stats-species"],
    queryFn: () => api.getStatsSpecies(),
  });

  const { data: timeline, isLoading: loadingTimeline, isError: timelineError } = useQuery({
    queryKey: ["stats-timeline"],
    queryFn: () => api.getStatsTimeline(),
  });

  const { data: sites, isLoading: loadingSites } = useQuery({
    queryKey: ["sites"],
    queryFn: () => api.getSites(),
  });

  const sitesList = sites ?? [];
  const speciesList = speciesStats ?? [];
  const timelineList = timeline ?? [];

  // Nama field mengikuti respons /api/v1/stats/overview supaya kartu tidak
  // menampilkan tanda hubung kosong.
  const statCards = [
    { label: "Total Rekaman", value: overview?.recordings },
    { label: "Spesies Terdeteksi", value: overview?.species_detected },
    { label: "Total Deteksi", value: overview?.detections },
    { label: "Lokasi Monitoring", value: overview?.sites },
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-base-content">Dasbor</h1>
            <p className="text-sm text-base-content/70 mt-1">
              Ringkasan biodiversitas dari semua lokasi monitoring
            </p>
          </div>
          <Link
            href="/laporan"
            className="focus-ring inline-flex min-h-11 items-center rounded border border-base-300 bg-base-100 px-4 text-sm font-medium hover:bg-base-200"
          >
            Buka laporan bulanan
          </Link>
        </div>
      </div>

      {/* Kalau API tidak bisa dihubungi, dashboard sebelumnya hanya menampilkan
          tanda hubung tanpa penjelasan. Sekarang alasannya terlihat. */}
      {overviewError && (
        <div className="mb-6">
          <ErrorState
            title="Ringkasan tidak bisa dimuat"
            message="Angka statistik gagal diambil dari API. Periksa koneksi ke server, lalu coba lagi."
            onRetry={() => refetchOverview()}
          />
        </div>
      )}

      {/* Stats Cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {loadingOverview
          ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
          : statCards.map((card) => (
              <div key={card.label} className="p-5 rounded-lg border border-base-300 bg-base-100">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-medium text-base-content/70 uppercase tracking-wide">{card.label}</p>
                </div>
                <p className="text-2xl font-semibold text-base-content">{card.value ?? "-"}</p>
              </div>
            ))}
      </div>

      {/* Charts Section */}
      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        {/* Top Species */}
        <div className="p-5 rounded-lg border border-base-300 bg-base-100">
          <h2 className="text-lg font-medium mb-4 text-base-content">Spesies Teratas</h2>
          {loadingSpecies ? (
            <Skeleton className="h-64 w-full" />
          ) : speciesError ? (
            <EmptyState message="Grafik spesies gagal dimuat dari API." />
          ) : speciesList.length === 0 ? (
            <EmptyState message="Belum ada data spesies." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={speciesList.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" tick={{ fill: "#5F6368", fontSize: 11 }} stroke="#E4E6E8" />
                <YAxis
                  type="category"
                  dataKey="common_name"
                  width={150}
                  tick={{ fill: "#111111", fontSize: 11 }}
                  stroke="#E4E6E8"
                  tickFormatter={(v: string) =>
                    v && v.length > 22 ? v.slice(0, 20) + "..." : v || "tanpa nama umum"
                  }
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                  }}
                  labelStyle={{ color: "var(--foreground)" }}
                />
                <Bar dataKey="count" fill="#00AA5B" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Timeline */}
        <div className="p-5 rounded-lg border border-base-300 bg-base-100">
          <h2 className="text-lg font-medium mb-4 text-base-content">Timeline Deteksi</h2>
          {loadingTimeline ? (
            <Skeleton className="h-64 w-full" />
          ) : timelineError ? (
            <EmptyState message="Timeline gagal dimuat dari API." />
          ) : timelineList.length === 0 ? (
            <EmptyState message="Belum ada data timeline." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={timelineList}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E6E8" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#5F6368", fontSize: 10 }}
                  stroke="#E4E6E8"
                  tickFormatter={(v: string) => (v ? v.slice(0, 10) : "")}
                />
                <YAxis tick={{ fill: "#5F6368", fontSize: 11 }} stroke="#E4E6E8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                  }}
                  labelStyle={{ color: "var(--foreground)" }}
                />
                <Line
                  type="monotone"
                  dataKey="detections"
                  stroke="#00AA5B"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#00AA5B" }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
          {!loadingTimeline && timelineList.length > 0 && timelineList.length <= 2 && (
            <p className="mt-2 text-xs text-base-content/70">
              Data baru mencakup {timelineList.length} hari, jadi grafik masih berupa satu titik.
              Angka ini akan memanjang setelah rekaman lapangan ditambahkan.
            </p>
          )}
        </div>
      </div>

      {/* Peta lokasi perekaman */}
      <div className="rounded-lg border border-base-300 bg-base-100 p-5">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-medium text-base-content">Peta Lokasi Perekaman</h2>
          {sitesList.length > 0 && (
            <p className="text-sm text-base-content/70">
              {sitesList.length} lokasi, {overview?.recordings ?? 0} rekaman
            </p>
          )}
        </div>
        {loadingSites ? (
          <Skeleton className="h-64 w-full" />
        ) : sitesList.length === 0 ? (
          <EmptyState
            title="Belum ada lokasi"
            message="Tambahkan lokasi monitoring supaya rekaman bisa dikaitkan dengan titik perekaman."
          />
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <SitesMap
                sites={sitesList
                  .filter((s: any) => s.latitude != null && s.longitude != null)
                  .map((s: any) => ({
                    id: s.id,
                    name: s.name,
                    lat: s.latitude,
                    lon: s.longitude,
                    habitat_type: s.habitat_type,
                  }))}
              />
              <p className="mt-2 text-xs text-base-content/70">
                Ubin peta dari OpenStreetMap. Kalau jaringan memblokir tile, daftar koordinat di
                samping tetap bisa dipakai.
              </p>
            </div>
            <ul className="divide-y divide-base-300 rounded border border-base-300">
              {sitesList.map((s: any) => (
                <li key={s.id} className="px-3 py-2">
                  <p className="text-sm font-medium text-base-content">{s.name}</p>
                  <p className="text-xs text-base-content/70">
                    {s.latitude != null && s.longitude != null
                      ? `${s.latitude.toFixed(4)} / ${s.longitude.toFixed(4)}`
                      : "koordinat belum diisi"}
                    {s.recordings_count != null ? `, ${s.recordings_count} rekaman` : ""}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
