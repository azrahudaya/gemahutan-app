"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/ui";

const IUCN_LABEL: Record<string, string> = {
  LC: "Risiko rendah",
  NT: "Hampir terancam",
  VU: "Rentan",
  EN: "Terancam",
  CR: "Kritis",
};

export default function SpeciesPage() {
  const [search, setSearch] = useState("");
  const [hanyaLokal, setHanyaLokal] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["species"],
    queryFn: () => api.getSpeciesList(),
  });

  const semua = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const jumlahLokal = useMemo(
    () => semua.filter((s) => s.model_supported).length,
    [semua]
  );

  const species = useMemo(() => {
    const q = search.trim().toLowerCase();
    let filtered = hanyaLokal
      ? semua.filter((s) => s.model_supported)
      : semua;
    if (q) {
      filtered = filtered.filter(
        (s) =>
          s.scientific_name?.toLowerCase().includes(q) ||
          s.common_name_id?.toLowerCase().includes(q) ||
          s.common_name_en?.toLowerCase().includes(q)
      );
    }
    return [...filtered].sort(
      (a, b) =>
        Number(b.model_supported) - Number(a.model_supported) ||
        (b.detection_count || 0) - (a.detection_count || 0)
    );
  }, [semua, search, hanyaLokal]);

  const total = semua.length;
  const detected = semua.filter((s) => (s.detection_count || 0) > 0).length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Spesies</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          {total > 0
            ? `${total} spesies di basis data, ${jumlahLokal} dikenali dikenali model lokal (Track B), ${detected} sudah pernah terdeteksi.`
            : "Daftar spesies target monitoring beserta status konservasi dan threshold deteksi."}
        </p>
        {total > 0 && (
          <p className="mt-2 max-w-3xl text-sm text-[var(--muted-foreground)]">
            Spesies di luar dikenali model lokal tetap bisa muncul lewat BirdNET zero-shot (Track A),
            tetapi tanpa verifikasi model spesialis dan dengan threshold global, jadi
            ketepatannya lebih rendah. Threshold di tabel ini hanya berlaku untuk spesies yang
            dikenali dikenali model lokal.
          </p>
        )}
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-3">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari nama ilmiah atau nama Indonesia"
          aria-label="Cari spesies"
          className="w-full max-w-sm rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        />
        <label className="focus-within:ring-2 focus-within:ring-[var(--ring)] flex min-h-11 cursor-pointer items-center gap-2 rounded px-1 text-sm text-[var(--foreground)]">
          <input
            type="checkbox"
            checked={hanyaLokal}
            onChange={(e) => setHanyaLokal(e.target.checked)}
            className="h-4 w-4 accent-[var(--primary-text)]"
          />
          Hanya yang dikenali dikenali model lokal
        </label>
      </div>

      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa menghubungi API spesies."}
          onRetry={() => refetch()}
        />
      ) : species.length === 0 ? (
        <EmptyState
          title={total === 0 ? "Basis data spesies masih kosong" : "Tidak ada hasil"}
          message={
            total === 0
              ? "Jalankan seed data untuk mengisi daftar spesies target, lalu unggah rekaman supaya deteksi masuk."
              : search.trim()
                ? `Tidak ada spesies yang cocok dengan "${search}"${hanyaLokal ? " di antara spesies yang dikenali dikenali model lokal" : ""}. Coba hapus kata kunci atau matikan filter dikenali model lokal.`
                : "Tidak ada spesies yang dikenali dikenali model lokal di basis data ini. Matikan filter untuk melihat seluruh daftar."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
              <tr>
                <th className="px-4 py-3 font-medium">Nama ilmiah</th>
                <th className="px-4 py-3 font-medium">Nama Indonesia</th>
                <th className="px-4 py-3 font-medium">Dikenali model lokal</th>
                <th className="px-4 py-3 font-medium">Status IUCN</th>
                <th className="px-4 py-3 font-medium">Threshold</th>
                <th className="px-4 py-3 font-medium">Deteksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {species.map((s) => (
                <tr key={s.id} className="hover:bg-[var(--card-hover)]">
                  <td className="px-4 py-3">
                    <Link
                      href={`/species/${s.id}`}
                      className="focus-ring inline-flex min-h-11 items-center text-[var(--primary-text)] hover:underline"
                    >
                      {s.scientific_name}
                    </Link>
                    {s.prioritas && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        Prioritas
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[var(--foreground)]">
                    {s.common_name_id || "-"}
                  </td>
                  <td className="px-4 py-3">
                    {s.model_supported ? (
                      <span className="text-[var(--foreground)]">Ya</span>
                    ) : (
                      <span className="text-[var(--muted-foreground)]">Hanya BirdNET</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[var(--muted-foreground)]">
                    {s.iucn_status ? `${s.iucn_status} (${IUCN_LABEL[s.iucn_status] || "status"})` : "-"}
                  </td>
                  <td className="px-4 py-3 text-[var(--muted-foreground)]">
                    {s.model_supported ? (s.default_threshold ?? "-") : "-"}
                  </td>
                  <td className="px-4 py-3 text-[var(--foreground)]">{s.detection_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
