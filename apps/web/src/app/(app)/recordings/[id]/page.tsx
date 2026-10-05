"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatKeyakinan, labelStatus, labelTahap, formatArahMataAngin, formatDerajat, formatJarak } from "@/lib/format";
import { Skeleton, TableSkeleton, EmptyState, ErrorState, ProgressBar, StageBadge, Toast } from "@/components/ui";
import { useJobStream } from "@/lib/use-job-stream";
import { WaveformPlayer } from "@/components/waveform-player";

const VERIFY_LABELS: Record<string, string> = {
  correct: "Benar",
  incorrect: "Salah",
  uncertain: "Ragu",
  unverified: "Belum diverifikasi",
};

const VERIFY_CLASSES: Record<string, string> = {
  correct: "bg-[var(--primary-surface)] text-[var(--accent)]",
  incorrect: "bg-[var(--destructive-surface)] text-[var(--destructive)]",
  uncertain: "bg-[var(--muted)] text-[var(--highlight)]",
  unverified: "bg-[var(--muted)] text-[var(--muted-foreground)]",
};

const STATUS_LABELS: Record<string, string> = {
  done: "Selesai dianalisis",
  processing: "Sedang diproses",
  pending: "Menunggu antrean",
  failed: "Gagal diproses",
};

const STATUS_CLASSES: Record<string, string> = {
  done: "bg-[var(--primary-surface)] text-[var(--accent)]",
  processing: "bg-[var(--muted)] text-[var(--highlight)]",
  pending: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  failed: "bg-[var(--destructive-surface)] text-[var(--destructive)]",
};

function formatTime(seconds?: number | null) {
  if (seconds == null) return "-";
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function RecordingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const router = useRouter();
  const { user } = useAuth();
  const bolehIndeks = user?.role === "admin" || user?.role === "researcher";
  const [spectrogramUrl, setSpectrogramUrl] = useState<string | null>(null);
  const [spectrogramError, setSpectrogramError] = useState<string | null>(null);

  const {
    data: recording,
    isLoading: loadingRecording,
    isError: recordingError,
    error: recordingErrorObject,
    refetch: refetchRecording,
  } = useQuery({
    queryKey: ["recording", id],
    queryFn: () => api.getRecording(id),
    // Selama worker masih memproses, halaman menyegarkan diri sendiri supaya
    // pengguna tidak perlu reload manual untuk melihat hasil.
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      return status === "pending" || status === "processing" ? 5000 : false;
    },
  });

  const {
    data: detections,
    isLoading: loadingDetections,
    isError: detectionsError,
    error: detectionsErrorObject,
    refetch: refetchDetections,
  } = useQuery({
    queryKey: ["detections", id],
    queryFn: () => api.getDetections(id),
    refetchInterval: (query) => {
      const rows = query.state.data as unknown[] | undefined;
      const recordingStatus = (queryClient.getQueryData(["recording", id]) as
        | { status?: string }
        | undefined)?.status;
      if (Array.isArray(rows) && rows.length > 0) return false;
      return recordingStatus === "pending" || recordingStatus === "processing" ? 5000 : false;
    },
  });

  const { data: jobs } = useQuery({
    queryKey: ["jobs", id],
    queryFn: () => api.getJobs(Number(id)),
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: number) => api.retryJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recording", id] });
      queryClient.invalidateQueries({ queryKey: ["jobs", id] });
      queryClient.invalidateQueries({ queryKey: ["detections", id] });
    },
  });

  const latestJob = Array.isArray(jobs) && jobs.length > 0 ? jobs[0] : null;

  // Penanda selesai: sekali tampil per kejadian, tidak diulang walau stream
  // dan status rekaman tiba berbarengan.
  const [toast, setToast] = useState<{ pesan: string; nada: "info" | "sukses" | "galat" } | null>(
    null
  );
  const kunciToastRef = useRef<string>("");

  const tampilkanToast = useCallback(
    (pesan: string, nada: "info" | "sukses" | "galat", kunci: string) => {
      if (kunciToastRef.current === kunci) return;
      kunciToastRef.current = kunci;
      setToast({ pesan, nada });
    },
    []
  );

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 8000);
    return () => clearTimeout(timer);
  }, [toast]);

  const statusRekaman = (recording as { status?: string } | undefined)?.status ?? null;
  const statusRekamanSebelumnya = useRef<string | null>(null);

  useEffect(() => {
    const sebelumnya = statusRekamanSebelumnya.current;
    if (sebelumnya && (sebelumnya === "pending" || sebelumnya === "processing")) {
      if (statusRekaman === "done") {
        tampilkanToast(
          `Rekaman #${id} selesai diproses. Hasil deteksinya sudah lengkap.`,
          "sukses",
          `selesai-${id}`
        );
      } else if (statusRekaman === "failed") {
        tampilkanToast(
          `Rekaman #${id} gagal diproses. Lihat pesan worker di halaman ini.`,
          "galat",
          `gagal-${id}`
        );
      }
    }
    if (statusRekaman) statusRekamanSebelumnya.current = statusRekaman;
  }, [statusRekaman, id, tampilkanToast]);

  const jobAktif = statusRekaman === "pending" || statusRekaman === "processing";

  // Progres disegarkan dari siaran status job; kalau stream gagal, hook yang
  // sama beralih ke polling lima detik.
  useJobStream(jobAktif, (update) => {
    if (update.recording_id !== Number(id)) return;
    if (update.status === "done") {
      tampilkanToast(`Job pemrosesan rekaman #${id} selesai.`, "sukses", `selesai-${id}`);
    } else if (update.status === "failed") {
      tampilkanToast(`Job pemrosesan rekaman #${id} gagal.`, "galat", `gagal-${id}`);
    }
    queryClient.invalidateQueries({ queryKey: ["recording", id] });
    queryClient.invalidateQueries({ queryKey: ["jobs", id] });
  });

  const { data: infoModel } = useQuery({
    queryKey: ["model-info"],
    queryFn: () => api.getModelInfo(),
    retry: false,
  });
  const infoLokalisasi = infoModel?.localization;

  const { data: indices } = useQuery({
    queryKey: ["indices", id],
    queryFn: () => api.getIndices(id),
    retry: false,
    // Indeks soundscape tidak ditampilkan untuk ranger.
    enabled: bolehIndeks,
  });

  useEffect(() => {
    if (!recording) return;
    let objectUrl: string | null = null;

    api
      .getSpectrogram(id)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob as Blob);
        setSpectrogramUrl(objectUrl);
      })
      .catch((err: Error) => setSpectrogramError(err.message));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id, recording]);

  const verifyMutation = useMutation({
    mutationFn: ({ detectionId, status }: { detectionId: number; status: string }) =>
      api.verifyDetection(detectionId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["detections", id] });
    },
  });

  const detectionList = Array.isArray(detections) ? detections : [];
  // Deteksi yang memang punya azimuth terhitung. Null berarti arahnya belum
  // dihitung, jadi tidak dipaksa jadi nol derajat.
  const deteksiBerarah = detectionList.filter((d: any) => d.azimuth_deg != null);
  const verifiedCount = detectionList.filter(
    (d: any) => d.verified_status && d.verified_status !== "unverified"
  ).length;

  // Peran diperiksa di API, jadi tombol yang tidak akan diizinkan tidak
  // ditampilkan sama sekali. Petugas lapangan tetap bisa mengunggah dan melihat.
  const bolehVerifikasi = user?.role === "admin" || user?.role === "researcher";
  const bolehUbahRekaman = Boolean(
    user && recording && (user.role === "admin" || user.id === recording.uploaded_by)
  );

  const [formEdit, setFormEdit] = useState({ site_id: "", recorded_at: "" });
  const [pesanEdit, setPesanEdit] = useState<string | null>(null);

  // Pilihan lokasi diisi dari data rekaman begitu termuat, supaya formulir
  // menampilkan keadaan sebenarnya dan bukan pilihan kosong.
  useEffect(() => {
    if (!recording) return;
    setFormEdit((f) => ({
      ...f,
      site_id: f.site_id || String((recording as { site_id?: number }).site_id ?? ""),
    }));
  }, [recording]);

  const { data: daftarSitus } = useQuery({
    queryKey: ["sites"],
    queryFn: () => api.getSites(),
  });
  const situs = daftarSitus ?? [];

  const simpanEdit = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.updateRecording(id, payload),
    onSuccess: () => {
      setPesanEdit("Perubahan tersimpan.");
      queryClient.invalidateQueries({ queryKey: ["recording", id] });
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
    },
    onError: (err) => setPesanEdit((err as Error)?.message || "Gagal menyimpan perubahan"),
  });

  const hapusRekaman = useMutation({
    mutationFn: () => api.deleteRecording(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] });
      router.replace("/recordings");
    },
    onError: (err) => setPesanEdit((err as Error)?.message || "Gagal menghapus rekaman"),
  });

  if (loadingRecording) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="mb-6 h-32 w-full" />
        <TableSkeleton rows={4} />
      </div>
    );
  }

  if (recordingError) {
    const pesan = (recordingErrorObject as Error)?.message || "";
    // 404 (milik orang lain atau sudah dihapus) ditampilkan tenang, bukan kotak galat.
    if (/tidak ditemukan/i.test(pesan)) {
      return (
        <div className="mx-auto max-w-5xl px-4 py-8">
          <EmptyState
            title="Rekaman tidak ditemukan"
            message="Rekaman ini mungkin sudah dihapus atau bukan milik Anda. Pilih rekaman lain dari daftar."
            action={
              <Link
                href="/recordings"
                className="rounded border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
              >
                Ke daftar rekaman
              </Link>
            }
          />
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <ErrorState
          title="Gagal memuat rekaman"
          message={pesan || "Tidak bisa menghubungi API."}
          onRetry={() => refetchRecording()}
        />
      </div>
    );
  }

  if (!recording) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <EmptyState
          title="Rekaman tidak ditemukan"
          message="Rekaman ini mungkin sudah dihapus. Pilih rekaman lain dari daftar."
          action={
            <Link
              href="/recordings"
              className="rounded border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
            >
              Ke daftar rekaman
            </Link>
          }
        />
      </div>
    );
  }

  const status = recording.status as string;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          href="/recordings"
          className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        >
          Kembali ke daftar rekaman
        </Link>
        <Link
          href="/simulasi"
          className="focus-ring text-sm text-[var(--muted-foreground)] underline hover:text-[var(--foreground)]"
        >
          Coba perkirakan lokasi
        </Link>
      </div>

      {toast && (
        <Toast message={toast.pesan} tone={toast.nada} onClose={() => setToast(null)} />
      )}

      <section className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--foreground)]">
              Rekaman #{recording.id}
            </h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              {recording.site_name || "Lokasi belum diisi"}
              {recording.recorded_at
                ? `, ${new Date(recording.recorded_at).toLocaleString("id-ID")}`
                : ""}
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <span
              className={`inline-flex items-center whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium ${
                STATUS_CLASSES[status] || STATUS_CLASSES.pending
              }`}
            >
              {STATUS_LABELS[status] || status}
            </span>
            {bolehVerifikasi && latestJob && (status === "failed" || status === "done") && (
              <button
                onClick={() => retryMutation.mutate(latestJob.id)}
                disabled={retryMutation.isPending}
                className="rounded border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
              >
                {retryMutation.isPending
                  ? "Mengirim ulang"
                  : status === "failed"
                    ? "Proses ulang rekaman ini"
                    : "Analisis ulang"}
              </button>
            )}
          </div>
        </div>
        {retryMutation.isError && (
          <p className="mt-2 text-sm text-[var(--destructive)]">
            Gagal mengirim ulang: {(retryMutation.error as Error)?.message}
          </p>
        )}
        {retryMutation.isSuccess && (
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            Rekaman dimasukkan ulang ke antrean. Hasil akan muncul otomatis dalam beberapa saat.
          </p>
        )}

        <div className="mt-5 rounded border border-[var(--border)] bg-[var(--background)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-[var(--foreground)]">Progres pemrosesan</h2>
            <StageBadge stage={latestJob?.stage} />
          </div>
          <ProgressBar
            value={latestJob?.progress}
            label={`Tahap ${labelTahap(latestJob?.stage)}`}
            className="mt-3"
          />
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            {latestJob
              ? `Job #${latestJob.id}, status ${labelStatus(latestJob.status)}${
                  latestJob.attempts ? `, percobaan ke-${latestJob.attempts}` : ""
                }.`
              : "Belum ada job pemrosesan untuk rekaman ini."}
          </p>
        </div>

        {bolehUbahRekaman && (
          <div className="mt-5 rounded border border-[var(--border)] bg-[var(--background)] p-4">
            <h2 className="text-sm font-medium text-[var(--foreground)]">Koreksi data rekaman</h2>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Lokasi dan waktu perekaman bisa dikoreksi. Isi audio dan hasil analisis tidak diubah dari sini.
            </p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="flex-1 text-xs text-[var(--muted-foreground)]">
                Lokasi
                <select
                  value={formEdit.site_id || String(recording.site_id ?? "")}
                  onChange={(e) => setFormEdit((f) => ({ ...f, site_id: e.target.value }))}
                  className="focus-ring mt-1 w-full rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)]"
                >
                  {situs.map((s: any) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex-1 text-xs text-[var(--muted-foreground)]">
                Waktu perekaman
                <input
                  type="datetime-local"
                  value={formEdit.recorded_at}
                  onChange={(e) => setFormEdit((f) => ({ ...f, recorded_at: e.target.value }))}
                  className="focus-ring mt-1 w-full rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </label>
              <button
                onClick={() => {
                  const payload: Record<string, unknown> = {};
                  if (formEdit.site_id) payload.site_id = Number(formEdit.site_id);
                  if (formEdit.recorded_at) {
                    payload.recorded_at = new Date(formEdit.recorded_at).toISOString();
                  }
                  if (Object.keys(payload).length === 0) {
                    setPesanEdit("Pilih lokasi atau waktu dulu sebelum menyimpan.");
                    return;
                  }
                  setPesanEdit(null);
                  simpanEdit.mutate(payload);
                }}
                disabled={simpanEdit.isPending}
                className="focus-ring rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
              >
                {simpanEdit.isPending ? "Menyimpan" : "Simpan perubahan"}
              </button>
              <button
                onClick={() => {
                  const yakin = window.confirm(
                    `Hapus rekaman #${recording.id} beserta deteksi dan berkas audionya? Tindakan ini tidak bisa dibatalkan.`
                  );
                  if (yakin) hapusRekaman.mutate();
                }}
                disabled={hapusRekaman.isPending}
                className="focus-ring rounded border border-[var(--destructive)] px-4 py-2 text-sm text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
              >
                {hapusRekaman.isPending ? "Menghapus" : "Hapus rekaman"}
              </button>
            </div>
            {pesanEdit && (
              <p role="status" className="mt-2 text-xs text-[var(--muted-foreground)]">
                {pesanEdit}
              </p>
            )}
          </div>
        )}

        <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Durasi</dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {formatTime(recording.duration_s)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Sample rate</dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {recording.sample_rate ? `${recording.sample_rate} Hz` : "-"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Deteksi</dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {recording.detection_count ?? detectionList.length}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Diverifikasi ahli
            </dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {verifiedCount} dari {detectionList.length}
            </dd>
          </div>
        </dl>

        {latestJob?.last_error && status !== "failed" && (
          <p className="mt-4 text-xs text-[var(--muted-foreground)]">
            Catatan proses: {latestJob.last_error}
          </p>
        )}
        {latestJob?.last_error && status === "failed" && (
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            Pesan worker: {latestJob.last_error}
          </p>
        )}
        {status === "failed" && (
          <div
            role="alert"
            className="mt-5 rounded border border-[var(--destructive)] bg-[var(--destructive-surface)] p-3 text-sm"
          >
            <p className="font-medium text-[var(--destructive)]">Proses gagal</p>
            <p className="mt-1 text-[var(--foreground)]">
              {recording.error_message ||
                "Worker tidak bisa memproses berkas ini. Periksa format audio lalu unggah ulang."}
            </p>
          </div>
        )}

        <div className="mt-6">
          <h2 className="mb-2 text-sm font-medium text-[var(--foreground)]">Gelombang suara</h2>
          <WaveformPlayer audioUrl={api.getAudioUrl(id)} />
        </div>

        <div className="mt-6">
          <h2 className="mb-2 text-sm font-medium text-[var(--foreground)]">Spektrogram</h2>
          {spectrogramError ? (
            <p className="rounded border border-[var(--border)] bg-[var(--background)] p-3 text-sm text-[var(--muted-foreground)]">
              {spectrogramError}
            </p>
          ) : spectrogramUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={spectrogramUrl}
              alt="Spektrogram mel rekaman ini"
              className="w-full rounded border border-[var(--border)]"
            />
          ) : (
            <Skeleton className="h-48 w-full" />
          )}
        </div>

        {indices && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-medium text-[var(--foreground)]">
              Indeks soundscape
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { key: "aci", label: "ACI", value: indices.aci },
                { key: "ndsi", label: "NDSI", value: indices.ndsi },
                { key: "adi", label: "ADI", value: indices.adi },
                { key: "bi", label: "BI", value: indices.bi },
              ].map((metric) => (
                <div
                  key={metric.key}
                  className="rounded border border-[var(--border)] bg-[var(--background)] p-3"
                >
                  <p className="text-xs text-[var(--muted-foreground)]">{metric.label}</p>
                  <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                    {metric.value == null ? "-" : Number(metric.value).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
            {indices.caveat && (
              <p className="mt-2 text-xs text-[var(--muted-foreground)]">{indices.caveat}</p>
            )}
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">Lokalisasi arah</h2>

        {!bolehIndeks ? (
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            Arah suara butuh alat dengan minimal 2 mikrofon yang jarak antar mikrofonnya tercatat
            di halaman Perangkat.
          </p>
        ) : deteksiBerarah.length === 0 ? (
          <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
            <p className="text-sm font-medium text-[var(--foreground)]">Arah belum tersedia</p>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Tidak ada deteksi pada rekaman ini yang punya azimuth terhitung, jadi tidak ada sudut
              yang bisa ditampilkan. Nilai nol tidak diisikan karena arahnya memang belum dihitung,
              bukan nol derajat.
            </p>
            <p className="mt-2 text-sm text-[var(--muted-foreground)]">
              {`Sebabnya, lokalisasi butuh rekaman minimal ${
                infoLokalisasi?.butuh_kanal_minimal ?? 2
              } kanal dengan geometri mikrofon terpasang, yaitu jarak antar mikrofon tercatat di halaman Perangkat. Rekaman ini belum memenuhi syarat itu.`}
            </p>
            {Array.isArray(infoLokalisasi?.batas) && infoLokalisasi.batas.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-[var(--muted-foreground)]">
                {infoLokalisasi.batas.map((kalimat: string, i: number) => (
                  <li key={i}>{kalimat}</li>
                ))}
              </ul>
            )}
            {infoLokalisasi?.terpasang_di_worker === false && (
              <p className="mt-3 text-xs text-[var(--muted-foreground)]">
                Catatan: engine lokalisasi belum terpasang di worker, jadi belum ada rekaman mana pun
                yang punya azimuth.
              </p>
            )}
          </div>
        ) : (
          <>
            <p className="mt-2 text-sm text-[var(--muted-foreground)]">
              {`${deteksiBerarah.length} dari ${detectionList.length} deteksi punya perkiraan arah. Azimuth dihitung dari selisih waktu antar kanal.`}
            </p>
            <ul className="mt-3 space-y-3">
              {deteksiBerarah.map((d: any) => (
                <li
                  key={d.id}
                  className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4"
                >
                  <p className="text-sm font-medium text-[var(--foreground)]">
                    {d.species_name}
                    {d.species_common ? (
                      <span className="ml-2 text-xs text-[var(--muted-foreground)]">
                        {d.species_common}
                      </span>
                    ) : null}
                  </p>
                  <dl className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Azimuth</dt>
                      <dd className="mt-1 text-[var(--foreground)]">
                        {formatDerajat(d.azimuth_deg)}, arah {formatArahMataAngin(d.azimuth_deg)}
                        {d.azimuth_kembar_deg == null ? null : (
                          <span className="mt-1 block text-[var(--muted-foreground)]">
                            Bisa juga {formatDerajat(d.azimuth_kembar_deg)}. Susunan mikrofon
                            segaris tidak memisahkan arah depan dan belakang.
                          </span>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Keyakinan arah</dt>
                      <dd className="mt-1 text-[var(--foreground)]">
                        {d.azimuth_confidence == null
                          ? "Belum dihitung"
                          : formatKeyakinan(d.azimuth_confidence)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Jangkauan</dt>
                      <dd className="mt-1 text-[var(--foreground)]">
                        {d.range_m == null ? "Belum dihitung" : formatJarak(d.range_m)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Mesin</dt>
                      <dd className="mt-1 text-[var(--foreground)]">
                        {d.localization_engine || "Belum dicatat"}
                      </dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-[var(--muted-foreground)]">
              Ketelitian arah bergantung pada jumlah kanal dan jarak mikrofon yang tercatat di halaman
              Perangkat. Perkiraan ini pendukung, bukan pengukuran posisi presisi.
            </p>
          </>
        )}
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">Deteksi spesies</h2>
          {detectionList.length > 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              Tandai benar atau salah untuk melatih ulang classifier lokal.
            </p>
          )}
        </div>

        {loadingDetections ? (
          <TableSkeleton rows={4} />
        ) : detectionsError ? (
          <ErrorState
            title="Gagal memuat deteksi"
            message={(detectionsErrorObject as Error)?.message || "Tidak bisa menghubungi API."}
            onRetry={() => refetchDetections()}
          />
        ) : detectionList.length === 0 ? (
          <EmptyState
            title="Belum ada deteksi"
            message={
              status === "done"
                ? "Model tidak menemukan spesies di atas threshold pada rekaman ini. Coba rekaman lain atau turunkan threshold spesies target."
                : "Deteksi akan muncul setelah worker selesai memproses rekaman ini."
            }
          />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Spesies</th>
                  <th className="px-4 py-3 font-medium">Waktu</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Engine</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Verifikasi ahli</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {detectionList.map((d: any) => (
                  <tr key={d.id} className="hover:bg-[var(--card-hover)]">
                    <td className="px-4 py-3">
                      <Link
                        href={`/species/${d.species_id}`}
                        className="text-[var(--primary-text)] hover:underline"
                      >
                        {d.species_name}
                      </Link>
                      {d.species_common && (
                        <span className="ml-2 text-xs text-[var(--muted-foreground)]">
                          {d.species_common}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {formatTime(d.start_s)} sampai {formatTime(d.end_s)}
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {formatKeyakinan(d.confidence)}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--muted-foreground)]">
                      {d.engine} {d.engine_version}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
                          VERIFY_CLASSES[d.verified_status] || VERIFY_CLASSES.unverified
                        }`}
                      >
                        {VERIFY_LABELS[d.verified_status] || d.verified_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {!bolehVerifikasi ? (
                        <span className="text-xs text-[var(--muted-foreground)]">
                          Butuh peran peneliti atau admin
                        </span>
                      ) : (
                      <div className="flex flex-wrap gap-1">
                        {["correct", "incorrect", "uncertain"].map((option) => (
                          <button
                            key={option}
                            onClick={() =>
                              verifyMutation.mutate({ detectionId: d.id, status: option })
                            }
                            disabled={verifyMutation.isPending}
                            aria-label={`Tandai deteksi ${d.species_name} sebagai ${VERIFY_LABELS[option]}`}
                            title={`Tandai ${VERIFY_LABELS[option]}`}
                            className={`rounded border px-2 py-1 text-xs transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50 ${
                              d.verified_status === option
                                ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]"
                                : "border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--muted)]"
                            }`}
                          >
                            {VERIFY_LABELS[option]}
                          </button>
                        ))}
                      </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {verifyMutation.isError && (
          <p className="mt-3 text-sm text-[var(--destructive)]">
            Gagal menyimpan verifikasi: {(verifyMutation.error as Error)?.message}
          </p>
        )}
      </section>
    </div>
  );
}
