"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileAudio, Mic, Upload } from "lucide-react";

import { api } from "@/lib/api";
import { useJobStream } from "@/lib/use-job-stream";
import { labelStatus, labelTahap, formatTanggal } from "@/lib/format";
import {
  EKSTENSI_AUDIO,
  MAKS_BERKAS_BATCH,
  type BerkasBatch,
  batchSelesai,
  kalimatRingkasan,
  ringkasBatch,
  saringBerkasAudio,
} from "@/lib/batch";
import { EmptyState, ProgressBar, Skeleton, StageBadge } from "@/components/ui";

const inputClass =
  "w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

const STATUS_CLASSES: Record<string, string> = {
  done: "bg-[var(--primary-surface)] text-[var(--accent)]",
  processing: "bg-[var(--muted)] text-[var(--highlight)]",
  pending: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  failed: "bg-[var(--destructive-surface)] text-[var(--destructive)]",
};

export default function UploadPage() {
  const queryClient = useQueryClient();
  const [siteId, setSiteId] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [berkas, setBerkas] = useState<File[]>([]);
  const [tolak, setTolak] = useState<{ nama: string; alasan: string }[]>([]);
  const [dipotong, setDipotong] = useState(0);
  const [persenUnggah, setPersenUnggah] = useState<number | null>(null);
  const [galatUnggah, setGalatUnggah] = useState<string | null>(null);
  const [hasil, setHasil] = useState<BerkasBatch[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const inputBerkasRef = useRef<HTMLInputElement>(null);

  const {
    data: daftarSitus,
    isLoading: memuatSitus,
    isError: galatSitus,
    refetch: muatUlangSitus,
  } = useQuery({
    queryKey: ["sites"],
    queryFn: () => api.getSites(),
  });
  const situs = daftarSitus ?? [];

  const {
    data: daftarPerangkat,
    isLoading: memuatPerangkat,
    isError: galatPerangkat,
    refetch: muatUlangPerangkat,
  } = useQuery({
    queryKey: ["devices", siteId],
    queryFn: () => api.getDevicesPilihan(siteId ? { site_id: siteId } : undefined),
    enabled: true,
  });
  const perangkat = Array.isArray(daftarPerangkat) ? daftarPerangkat : [];

  const { data: detailBatch, refetch: muatUlangBatch } = useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => api.getBatch(String(batchId)),
    enabled: Boolean(batchId),
    // Batch yang belum kelar disegarkan sendiri tiap empat detik.
    refetchInterval: (query) => {
      const data = query.state.data as { recordings?: BerkasBatch[] } | undefined;
      if (!data) return 4000;
      return batchSelesai(data.recordings) ? false : 4000;
    },
  });

  const { data: daftarBatch } = useQuery({
    queryKey: ["batches"],
    queryFn: () => api.getBatches(),
  });

  const barisProses: BerkasBatch[] = useMemo(() => {
    const dariDetail: BerkasBatch[] = (detailBatch?.recordings || []).map((r: any) => ({
      filename: r?.filename ?? `Rekaman #${r?.id}`,
      recording_id: r?.id ?? null,
      status: r?.status ?? null,
      progress: r?.progress ?? null,
      stage: r?.stage ?? null,
      error: r?.error ?? null,
    }));
    if (dariDetail.length > 0) return dariDetail;
    return hasil;
  }, [detailBatch, hasil]);

  const ringkasan = useMemo(() => {
    if (barisProses.length > 0) return ringkasBatch(barisProses);
    return {
      total: detailBatch?.total ?? 0,
      selesai: detailBatch?.done ?? 0,
      gagal: detailBatch?.failed ?? 0,
      diproses: detailBatch?.processing ?? 0,
      menunggu: detailBatch?.pending ?? 0,
    };
  }, [barisProses, detailBatch]);

  const adaProses = barisProses.some(
    (b) => b.status === "pending" || b.status === "processing"
  );

  // Progres dipantau lewat siaran status selagi masih ada job jalan; kalau
  // stream tertutup, hook yang sama beralih ke polling lima detik.
  useJobStream(adaProses, () => {
    if (batchId) muatUlangBatch();
  });

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["batches"] });
  }, [batchId, queryClient]);

  const pilihBerkas = (daftar: FileList | null) => {
    const berkasBaru = Array.from(daftar || []);
    const hasilSaring = saringBerkasAudio(berkasBaru);
    const namaDitolak = new Set(hasilSaring.ditolak.map((t) => t.nama));
    // Kelebihan di atas batas ikut dibuang di sini, jadi tombol unggah tidak
    // pernah mengirim berkas yang pasti ditolak API.
    setBerkas(
      berkasBaru.filter((f) => !namaDitolak.has(f.name)).slice(0, MAKS_BERKAS_BATCH)
    );
    setTolak(hasilSaring.ditolak);
    setDipotong(hasilSaring.dipotong);
    setGalatUnggah(null);
  };

  const buangBerkas = (nama: string) => {
    setBerkas((daftar) => daftar.filter((f) => f.name !== nama));
  };

  const mulaiUnggah = async () => {
    if (!siteId) {
      setGalatUnggah("Pilih lokasi perekaman dulu.");
      return;
    }
    if (berkas.length === 0) {
      setGalatUnggah("Pilih minimal satu berkas audio.");
      return;
    }

    setGalatUnggah(null);
    setPersenUnggah(0);
    setHasil([]);
    setBatchId(null);

    const formData = new FormData();
    for (const f of berkas) formData.append("files", f, f.name);
    formData.append("site_id", siteId);
    if (deviceId) formData.append("device_id", deviceId);

    try {
      const resp = await api.uploadRecordingBatch(formData, setPersenUnggah);
      const items: BerkasBatch[] = Array.isArray(resp?.items) ? resp.items : [];
      setHasil(items);
      if (resp?.batch_id) setBatchId(String(resp.batch_id));
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
    } catch (err) {
      setGalatUnggah((err as Error)?.message || "Unggah batch gagal.");
    } finally {
      setPersenUnggah(null);
    }
  };

  const bukaBatchLama = (id: string) => {
    setBatchId(id);
    setHasil([]);
    setGalatUnggah(null);
  };

  const daftarBatchTerbaru = Array.isArray(daftarBatch) ? daftarBatch.slice(0, 5) : [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Unggah banyak berkas</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Kirim sampai {MAKS_BERKAS_BATCH} berkas audio sekaligus ke satu lokasi. Berkas yang
          gagal diproses tidak membatalkan sisanya. Untuk merekam langsung dari peramban, buka{" "}
          <Link href="/rekam" className="focus-ring underline inline-flex items-center min-h-11 -my-2 px-1 py-2 rounded">
            halaman rekam
          </Link>
          . Untuk memperkirakan lokasi suara tanpa rekaman asli, buka{" "}
          <Link href="/simulasi" className="focus-ring underline inline-flex items-center min-h-11 -my-2 px-1 py-2 rounded">
            halaman simulasi
          </Link>
          .
        </p>
      </div>

      <section className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <h2 className="text-sm font-medium text-[var(--foreground)]">Unggah dalam tiga langkah</h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-xs text-[var(--muted-foreground)]">
            1. Lokasi perekaman
            {memuatSitus ? (
              <Skeleton className="mt-1 h-11 w-full" />
            ) : (
              <select
                value={siteId}
                onChange={(e) => {
                  setSiteId(e.target.value);
                  setDeviceId("");
                }}
                className={`mt-1 ${inputClass}`}
                aria-label="Lokasi perekaman"
              >
                <option value="">Pilih lokasi</option>
                {situs.map((s: any) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
            {galatSitus && (
              <span className="mt-1 block text-[var(--destructive)]">
                Gagal memuat lokasi.{" "}
                <button type="button" onClick={() => muatUlangSitus()} className="focus-ring underline">
                  Coba lagi
                </button>
              </span>
            )}
            {!memuatSitus && !galatSitus && situs.length === 0 && (
              <span className="mt-1 block">Belum ada lokasi. Buat lokasi dulu di halaman Lokasi.</span>
            )}
          </label>

          <label className="text-xs text-[var(--muted-foreground)]">
            Perangkat (opsional)
            {memuatPerangkat ? (
              <Skeleton className="mt-1 h-11 w-full" />
            ) : (
              <select
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                className={`mt-1 ${inputClass}`}
                aria-label="Perangkat perekam"
              >
                <option value="">Tanpa perangkat</option>
                {perangkat.map((d: any) => (
                  <option key={d.id} value={String(d.id)}>
                    {d.name} {d.channel_count ? `(${d.channel_count} kanal)` : ""}
                  </option>
                ))}
              </select>
            )}
            {galatPerangkat && (
              <span className="mt-1 block text-[var(--destructive)]">
                Daftar perangkat tidak bisa dimuat, unggahan tetap bisa jalan tanpa perangkat.{" "}
                <button
                  type="button"
                  onClick={() => muatUlangPerangkat()}
                  className="focus-ring underline"
                >
                  Coba lagi
                </button>
              </span>
            )}
            {!memuatPerangkat && !galatPerangkat && perangkat.length === 0 && (
              <span className="mt-1 block">
                Belum ada perangkat terdaftar. Tambahkan lewat halaman Perangkat supaya asal
                rekaman tercatat.
              </span>
            )}
          </label>
        </div>

        <div className="mt-4">
          <span className="text-xs text-[var(--muted-foreground)]">
            2. Berkas audio, maksimal {MAKS_BERKAS_BATCH} sekaligus
          </span>
          <input
            ref={inputBerkasRef}
            id="berkas-audio"
            type="file"
            multiple
            accept={EKSTENSI_AUDIO.map((e) => `.${e}`).join(",")}
            onChange={(e) => pilihBerkas(e.target.files)}
            className="sr-only"
          />
          <button
            type="button"
            onClick={() => inputBerkasRef.current?.click()}
            className="mt-1 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded border border-dashed border-[var(--border)] bg-[var(--background)] px-4 py-3 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            <FileAudio size={16} aria-hidden="true" />
            {berkas.length > 0 ? `Pilih ulang berkas (${berkas.length} terpilih)` : "Pilih berkas"}
          </button>
        </div>

        {dipotong > 0 && (
          <p role="status" className="mt-2 text-xs text-[var(--highlight)]">
            {dipotong} berkas di luar batas {MAKS_BERKAS_BATCH} diabaikan. Unggah sisanya pada
            gelombang berikutnya.
          </p>
        )}

        {tolak.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs text-[var(--destructive)]">
            {tolak.map((t) => (
              <li key={t.nama}>
                {t.nama}: {t.alasan}
              </li>
            ))}
          </ul>
        )}

        {berkas.length > 0 && (
          <ul className="mt-4 space-y-2">
            {berkas.map((f) => (
              <li
                key={f.name}
                className="flex flex-col gap-2 rounded border border-[var(--border)] bg-[var(--background)] p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="flex min-w-0 items-center gap-2 text-sm text-[var(--foreground)]">
                  <FileAudio size={16} aria-hidden="true" />
                  <span className="truncate">{f.name}</span>
                  <span className="shrink-0 text-xs text-[var(--muted-foreground)]">
                    {(f.size / 1024 / 1024).toFixed(1)} MB
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => buangBerkas(f.name)}
                  className="focus-ring min-h-11 rounded border border-[var(--border)] px-3 text-xs text-[var(--destructive)] hover:bg-[var(--destructive-surface)]"
                >
                  Buang
                </button>
              </li>
            ))}
          </ul>
        )}

        {persenUnggah !== null && (
          <div className="mt-4">
            <ProgressBar value={persenUnggah} label="Progres unggah" />
          </div>
        )}

        {galatUnggah && (
          <p role="alert" className="mt-3 text-sm text-[var(--destructive)]">
            {galatUnggah}
          </p>
        )}

        <button
          type="button"
          onClick={mulaiUnggah}
          disabled={berkas.length === 0 || !siteId || persenUnggah !== null}
          className="focus-ring mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50 sm:w-auto"
        >
          <Upload size={16} aria-hidden="true" />
          {persenUnggah !== null ? "Mengunggah" : `3. Kirim ${berkas.length} berkas`}
        </button>
        {(!siteId || berkas.length === 0) && persenUnggah === null && (
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            {!siteId
              ? "Tombol kirim masih nonaktif: pilih lokasi dulu (langkah 1)."
              : "Tombol kirim masih nonaktif: pilih berkas dulu (langkah 2)."}
          </p>
        )}
      </section>

      {(batchId || barisProses.length > 0) && (
        <section className="mt-6 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-sm font-medium text-[var(--foreground)]">
                {batchId ? `Batch ${batchId}` : "Hasil unggahan"}
              </h2>
              <p role="status" className="mt-1 text-sm text-[var(--muted-foreground)]">
                {kalimatRingkasan(ringkasan)}
              </p>
            </div>
            {batchId && <ProgressBar value={detailBatch?.progress_percent ?? null} className="sm:w-56" />}
          </div>

          {adaProses && (
            <p className="mt-2 text-xs text-[var(--muted-foreground)]">
              Progres diperbarui otomatis sampai semua berkas selesai.
            </p>
          )}

          <ul className="mt-4 divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {barisProses.map((b, i) => (
              <li key={`${b.filename}-${i}`} className="py-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-[var(--foreground)]">
                      {b.filename || "Berkas tanpa nama"}
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
                          STATUS_CLASSES[b.status || ""] || STATUS_CLASSES.pending
                        }`}
                      >
                        {labelStatus(b.status)}
                      </span>
                      <StageBadge stage={b.stage} />
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-3">
                    <span className="w-16 text-right text-xs text-[var(--muted-foreground)]">
                      {b.progress ?? 0}%
                    </span>
                    {b.status !== "failed" && b.recording_id ? (
                      <Link
                        href={`/recordings/${b.recording_id}`}
                        className="focus-ring inline-flex min-h-11 items-center text-sm underline"
                      >
                        Detail rekaman
                      </Link>
                    ) : (
                      <span className="text-xs text-[var(--muted-foreground)]">
                        {b.status === "failed" ? "Tidak bisa lanjut" : "Menunggu rekaman"}
                      </span>
                    )}
                  </span>
                </div>
                <ProgressBar
                  value={b.progress}
                  label={labelTahap(b.stage)}
                  className="mt-2"
                />
                {b.error && (
                  <p className="mt-1 text-xs text-[var(--destructive)]">Gagal: {b.error}</p>
                )}
              </li>
            ))}
          </ul>

          {ringkasan.gagal > 0 && (
            <p className="mt-3 text-sm text-[var(--destructive)]">
              {ringkasan.gagal} berkas gagal. Perbaiki berkasnya lalu unggah ulang hanya berkas itu.
            </p>
          )}
        </section>
      )}

      <section className="mt-6">
        <h2 className="text-sm font-medium text-[var(--foreground)]">Batch terbaru</h2>
        {daftarBatchTerbaru.length === 0 ? (
          <div className="mt-3">
            <EmptyState message="Belum ada batch unggahan. Riwayat batch muncul di sini setelah unggahan pertama." />
          </div>
        ) : (
          <ul className="mt-3 space-y-2">
            {daftarBatchTerbaru.map((b: any) => (
              <li
                key={b.batch_id}
                className="flex flex-col gap-2 rounded border border-[var(--border)] bg-[var(--card)] p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="min-w-0 text-sm text-[var(--foreground)]">
                  {/* Id batch panjang tanpa spasi, jadi harus boleh dipotong
                      supaya tidak memaksa gulir mendatar di layar 390 piksel. */}
                  <span className="block break-all font-medium">{b.batch_id}</span>
                  <span className="mt-0.5 block text-xs text-[var(--muted-foreground)]">
                    {formatTanggal(b.created_at)}, {b.done} selesai, {b.failed} gagal dari {b.total}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <ProgressBar value={b.progress_percent} className="w-32" />
                  <button
                    type="button"
                    onClick={() => bukaBatchLama(String(b.batch_id))}
                    className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                  >
                    Lihat berkas
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
        <h2 className="flex items-center gap-2 text-sm font-medium text-[var(--foreground)]">
          <Mic size={16} aria-hidden="true" />
          Rekam dari peramban
        </h2>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Kalau rekaman masih ada di perangkat yang dipakai sekarang, buka halaman rekam dan
          simpan langsung sebagai audio/webm.
        </p>
        <Link
          href="/rekam"
          className="focus-ring mt-3 inline-flex min-h-11 items-center rounded border border-[var(--border)] bg-[var(--background)] px-4 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
        >
          Buka halaman rekam
        </Link>
      </section>
    </div>
  );
}
