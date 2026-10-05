"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useJobStream } from "@/lib/use-job-stream";
import { formatDurasi, formatTanggal, labelStatus, labelTahap } from "@/lib/format";
import {
  TableSkeleton,
  EmptyState,
  ErrorState,
  ProgressBar,
  StageBadge,
} from "@/components/ui";

const STATUS_CLASSES: Record<string, string> = {
  done: "bg-[var(--primary-surface)] text-[var(--accent)]",
  processing: "bg-[var(--muted)] text-[var(--highlight)]",
  pending: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  failed: "bg-[var(--destructive-surface)] text-[var(--destructive)]",
};

export default function RecordingsPage() {
  const [site, setSite] = useState("");
  const [species, setSpecies] = useState("");
  const [status, setStatus] = useState("");
  const [minConf, setMinConf] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [page, setPage] = useState(1);

  // Nama parameter ini harus sama dengan kontrak API (site, species, min_conf,
  // status, from, to, page, page_size). Sebelumnya berbeda sehingga filter tidak
  // menyaring apa pun.
  const params: Record<string, string> = { page: String(page), page_size: "20" };
  if (site) params.site = site;
  if (species) params.species = species;
  if (status) params.status = status;
  if (minConf) params.min_conf = minConf;
  if (fromDate) params.from = fromDate;
  if (toDate) params.to = toDate;

  const hasFilter = Boolean(site || species || status || minConf || fromDate || toDate);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Unduhan harus lewat fetch supaya header Authorization ikut terkirim.
  // Tautan <a href> langsung ke API akan dijawab 401 karena tanpa token.
  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const params: Record<string, string> = {};
      if (site) params.site = site;
      const blob = await api.downloadExport("recordings", params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "gemahutan_daftar_rekaman.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError((err as Error)?.message || "Ekspor gagal");
    } finally {
      setIsExporting(false);
    }
  };

  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [hapusError, setHapusError] = useState<string | null>(null);

  // Halaman daftar sebelumnya diam saja saat ada rekaman yang masih diproses,
  // jadi pengguna harus menebak kapan selesai. Polling sepuluh detik lebih murah
  // daripada websocket untuk kebutuhan demo ini.
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["recordings", params],
    queryFn: () => api.getRecordings(params),
    refetchInterval: 10000,
  });

  const bolehHapus = (r: any) =>
    Boolean(user) && (user!.role === "admin" || user!.id === r.uploaded_by);

  // Ekspor CSV hanya untuk peran analis (admin/peneliti); ranger melihat
  // tombolnya tapi API menolak, jadi tombol disembunyikan (W-09).
  const bolehEkspor = user?.role === "admin" || user?.role === "researcher";

  const hapusRekaman = async (r: any) => {
    const yakin = window.confirm(
      `Hapus rekaman #${r.id} beserta deteksi dan berkas audionya? Tindakan ini tidak bisa dibatalkan.`
    );
    if (!yakin) return;
    setHapusError(null);
    try {
      await api.deleteRecording(String(r.id));
      await queryClient.invalidateQueries({ queryKey: ["recordings"] });
    } catch (err) {
      setHapusError((err as Error)?.message || "Gagal menghapus rekaman");
    }
  };

  const { data: sites } = useQuery({
    queryKey: ["sites"],
    queryFn: () => api.getSites(),
  });

  const { data: speciesList } = useQuery({
    queryKey: ["species"],
    queryFn: () => api.getSpeciesList(),
  });

  const recordings = data?.items || [];
  const total = data?.total ?? recordings.length;
  const totalPages = data?.total_pages ?? 1;

  const adaJobAktif = recordings.some(
    (r: any) => r.status === "pending" || r.status === "processing"
  );

  // Siaran status job mempercepat pembaruan saat halaman ini dibuka; cadangan
  // polling bawaan react-query tetap jalan sepuluh detik sekali.
  useJobStream(adaJobAktif, () => refetch());

  const resetFilters = () => {
    setSite("");
    setSpecies("");
    setStatus("");
    setMinConf("");
    setFromDate("");
    setToDate("");
    setPage(1);
  };

  const inputClass =
    "rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {hapusError && (
        <div className="mb-4">
          <ErrorState title="Gagal menghapus" message={hapusError} />
        </div>
      )}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">Daftar Rekaman</h1>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            {isLoading
              ? "Memuat rekaman"
              : `${total} rekaman${hasFilter ? " cocok dengan filter" : " tersimpan"}. Klik satu baris untuk melihat deteksi dan spektrogram.`}
          </p>
        </div>
        {bolehEkspor && (
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="inline-flex items-center justify-center rounded border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
          >
            {isExporting ? "Menyiapkan berkas" : "Unduh CSV"}
          </button>
        )}
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-6">
        <select
          value={site}
          onChange={(e) => { setSite(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Filter lokasi"
        >
          <option value="">Semua lokasi</option>
          {(Array.isArray(sites) ? sites : []).map((s: any) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        <select
          value={species}
          onChange={(e) => { setSpecies(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Filter spesies"
        >
          <option value="">Semua spesies</option>
          {(Array.isArray(speciesList) ? speciesList : []).map((s: any) => (
            <option key={s.id} value={s.id}>
              {s.common_name_id || s.scientific_name}
            </option>
          ))}
        </select>

        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Filter status pemrosesan"
        >
          <option value="">Semua status</option>
          <option value="done">Selesai</option>
          <option value="processing">Sedang diproses</option>
          <option value="pending">Menunggu antrean</option>
          <option value="failed">Gagal</option>
        </select>

        <input
          type="number"
          placeholder="Skor minimum"
          min="0"
          max="1"
          step="0.05"
          value={minConf}
          onChange={(e) => { setMinConf(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Skor minimum"
        />

        <input
          type="date"
          value={fromDate}
          onChange={(e) => { setFromDate(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Tanggal mulai"
        />

        <input
          type="date"
          value={toDate}
          onChange={(e) => { setToDate(e.target.value); setPage(1); }}
          className={inputClass}
          aria-label="Tanggal akhir"
        />
      </div>

      {exportError && (
        <p className="mb-3 text-sm text-[var(--destructive)]">{exportError}</p>
      )}
      {hasFilter && (
        <div className="mb-4">
          <button
            onClick={resetFilters}
            className="rounded border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            Kosongkan filter
          </button>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat daftar rekaman."}
          onRetry={() => refetch()}
        />
      ) : recordings.length === 0 ? (
        <EmptyState
          title={hasFilter ? "Tidak ada rekaman yang cocok" : "Belum ada rekaman"}
          message={
            hasFilter
              ? "Longgarkan filter, misalnya kosongkan skor minimum atau perlebar rentang tanggal."
              : "Unggah rekaman pertama supaya server bisa menganalisisnya."
          }
          action={
            hasFilter ? (
              <button
                onClick={resetFilters}
                className="rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)]"
              >
                Kosongkan filter
              </button>
            ) : (
              <Link
                href="/upload"
                className="rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)]"
              >
                Unggah rekaman
              </Link>
            )
          }
        />
      ) : (
        <>
          {/* Layar sempit memakai kartu: tabel selebar ini bikin gulir mendatar
              di viewport 390 piksel. */}
          <ul className="space-y-3 md:hidden">
            {recordings.map((r: any) => (
              <li
                key={r.id}
                className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <Link
                    href={`/recordings/${r.id}`}
                    className="focus-ring inline-flex min-h-11 items-center text-sm font-medium text-[var(--primary-text)] hover:underline"
                  >
                    Rekaman #{r.id}
                  </Link>
                  <span
                    className={`inline-flex shrink-0 whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${
                      STATUS_CLASSES[r.status] || STATUS_CLASSES.pending
                    }`}
                  >
                    {labelStatus(r.status)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-[var(--foreground)]">{r.site_name || "-"}</p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  {formatTanggal(r.recorded_at)}, {formatDurasi(r.duration_s)}, {r.detection_count ?? 0}{" "}
                  deteksi
                </p>
                <div className="mt-3">
                  <div className="flex items-center justify-between gap-2">
                    <StageBadge stage={r.stage} />
                    <span className="text-xs text-[var(--muted-foreground)]">
                      {r.progress ?? 0}%
                    </span>
                  </div>
                  <ProgressBar value={r.progress} className="mt-2" />
                </div>
                {bolehHapus(r) && (
                  <button
                    onClick={() => hapusRekaman(r)}
                    className="focus-ring mt-3 inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-xs text-[var(--destructive)] hover:bg-[var(--destructive-surface)]"
                  >
                    Hapus
                  </button>
                )}
              </li>
            ))}
          </ul>

          <div className="hidden overflow-x-auto rounded-lg border border-[var(--border)] md:block">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Rekaman</th>
                  <th className="px-4 py-3 font-medium">Lokasi</th>
                  <th className="px-4 py-3 font-medium">Tanggal</th>
                  <th className="px-4 py-3 font-medium">Durasi</th>
                  <th className="px-4 py-3 font-medium">Deteksi</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Progres dan tahap</th>
                  <th className="px-4 py-3 font-medium">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {recordings.map((r: any) => (
                  <tr key={r.id} className="hover:bg-[var(--card-hover)]">
                    <td className="px-4 py-3">
                      <Link
                        href={`/recordings/${r.id}`}
                        className="focus-ring inline-flex min-h-11 items-center text-[var(--primary-text)] hover:underline"
                      >
                        Rekaman #{r.id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{r.site_name || "-"}</td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {formatTanggal(r.recorded_at)}
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {formatDurasi(r.duration_s)}
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{r.detection_count ?? 0}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex shrink-0 whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${
                          STATUS_CLASSES[r.status] || STATUS_CLASSES.pending
                        }`}
                      >
                        {labelStatus(r.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="w-40">
                        <div className="flex items-center justify-between gap-2">
                          <StageBadge stage={r.stage} />
                          <span className="text-xs text-[var(--muted-foreground)]">
                            {r.progress ?? 0}%
                          </span>
                        </div>
                        <ProgressBar
                          value={r.progress}
                          label={`Progres ${labelTahap(r.stage)}`}
                          className="mt-1"
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {bolehHapus(r) ? (
                        <button
                          onClick={() => hapusRekaman(r)}
                          className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-xs text-[var(--destructive)] hover:bg-[var(--destructive-surface)]"
                        >
                          Hapus
                        </button>
                      ) : (
                        <span className="text-xs text-[var(--muted-foreground)]">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="min-h-11 rounded border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground)] disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            Sebelumnya
          </button>
          <span className="text-sm text-[var(--muted-foreground)]">
            Halaman {page} dari {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="min-h-11 rounded border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground)] disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            Selanjutnya
          </button>
        </div>
      )}
    </div>
  );
}
