"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Mic, Square } from "lucide-react";

import { api } from "@/lib/api";
import { ProgressBar, Skeleton } from "@/components/ui";

type TahapRekam = "siap" | "merekam" | "mengunggah" | "selesai" | "galat";

const JUMLAH_SEGMEN = 20;

function mimeRekam(): string | null {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") return null;
  const pilihan = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4;codecs=mp4a.40.2",
    "audio/mp4",
  ];
  for (const m of pilihan) {
    if (MediaRecorder.isTypeSupported(m)) return m;
  }
  return null;
}

function ekstensiMime(mime: string): string {
  // Safari iPhone menghasilkan audio/mp4 (AAC), Chrome/Firefox audio/webm.
  return mime.includes("mp4") ? ".m4a" : ".webm";
}

function pesanGalat(err: unknown): string {
  const nama = (err as { name?: string })?.name || "";
  switch (nama) {
    case "NotAllowedError":
    case "SecurityError":
      return "Peramban memblokir akses mikrofon. Izinkan mikrofon untuk situs ini lewat ikon gembok di bilah alamat, lalu muat ulang halaman.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "Tidak ada mikrofon yang terdeteksi. Sambungkan mikrofon lalu muat ulang halaman.";
    case "NotReadableError":
    case "TrackStartError":
      return "Mikrofon sedang dipakai aplikasi lain. Tutup aplikasi itu lalu coba lagi.";
    default:
      return (err as Error)?.message || "Perekaman gagal dimulai.";
  }
}

function formatTimer(detik: number): string {
  const m = Math.floor(detik / 60);
  const s = detik % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function RekamPage() {
  const [dukung, setDukung] = useState<boolean | null>(null);
  const [tahap, setTahap] = useState<TahapRekam>("siap");
  const [detik, setDetik] = useState(0);
  const [level, setLevel] = useState(0);
  const [persenUnggah, setPersenUnggah] = useState<number | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [rekamanId, setRekamanId] = useState<number | null>(null);
  const [siteId, setSiteId] = useState("");
  const [deviceId, setDeviceId] = useState("");

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const potonganRef = useRef<Blob[]>([]);
  const mulaiRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rafRef = useRef<number | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const frameRef = useRef(0);

  const {
    data: daftarSitus,
    isLoading: memuatSitus,
    isError: galatSitus,
    refetch: muatUlangSitus,
  } = useQuery({ queryKey: ["sites"], queryFn: () => api.getSites() });
  const situs = daftarSitus ?? [];

  const { data: daftarPerangkat, isError: galatPerangkat } = useQuery({
    queryKey: ["devices", siteId],
    queryFn: () => api.getDevicesPilihan(siteId ? { site_id: siteId } : undefined),
  });
  const perangkat = Array.isArray(daftarPerangkat) ? daftarPerangkat : [];

  useEffect(() => {
    const adaMedia = typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);
    setDukung(adaMedia && mimeRekam() !== null);
  }, []);

  const bersihkanAlat = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) track.stop();
      streamRef.current = null;
    }
    if (ctxRef.current) {
      void ctxRef.current.close().catch(() => {});
      ctxRef.current = null;
    }
    setLevel(0);
  }, []);

  useEffect(() => bersihkanAlat, [bersihkanAlat]);

  const unggahHasil = async (mime: string) => {
    const blob = new Blob(potonganRef.current, { type: mime });
    potonganRef.current = [];

    if (blob.size === 0) {
      setGalat("Rekaman kosong karena tidak ada data audio yang tertangkap. Coba rekam lagi.");
      setTahap("galat");
      return;
    }

    const ekstensi = ekstensiMime(mime);
    const nama = `rekaman-peramban-${new Date(mulaiRef.current || Date.now())
      .toISOString()
      .replace(/[:.]/g, "-")}${ekstensi}`;
    const formData = new FormData();
    formData.append("file", new File([blob], nama, { type: mime }));
    formData.append("site_id", siteId);
    if (deviceId) formData.append("device_id", deviceId);
    if (mulaiRef.current) {
      formData.append("recorded_at", new Date(mulaiRef.current).toISOString());
    }

    setTahap("mengunggah");
    setPersenUnggah(0);
    try {
      const hasil = await api.uploadRecording(formData, setPersenUnggah);
      setRekamanId(hasil?.id ?? null);
      setTahap("selesai");
    } catch (err) {
      setGalat((err as Error)?.message || "Unggahan rekaman gagal.");
      setTahap("galat");
    } finally {
      setPersenUnggah(null);
    }
  };

  const analisisLevel = (stream: MediaStream) => {
    try {
      const Ctx =
        window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      ctxRef.current = ctx;
      const sumber = ctx.createMediaStreamSource(stream);
      const analiser = ctx.createAnalyser();
      analiser.fftSize = 512;
      sumber.connect(analiser);
      const data = new Uint8Array(analiser.fftSize);

      const ukur = () => {
        analiser.getByteTimeDomainData(data);
        let jumlah = 0;
        for (let i = 0; i < data.length; i += 1) {
          const simpangan = (data[i] - 128) / 128;
          jumlah += simpangan * simpangan;
        }
        const rms = Math.sqrt(jumlah / data.length);
        // Diperbarui tiap tiga bingkai saja: cukup untuk indikator, jauh lebih
        // ringan daripada menggambar ulang enam puluh kali per detik.
        frameRef.current += 1;
        if (frameRef.current % 3 === 0) {
          setLevel(Math.min(100, Math.round(rms * 260)));
        }
        rafRef.current = requestAnimationFrame(ukur);
      };
      rafRef.current = requestAnimationFrame(ukur);
    } catch {
      // Indikator level hanya pelengkap, perekaman tetap jalan tanpa itu.
    }
  };

  const mulaiRekam = async () => {
    if (!siteId) {
      setGalat("Pilih lokasi perekaman dulu supaya rekaman tercatat di tempat yang benar.");
      return;
    }
    setGalat(null);
    setRekamanId(null);
    setDetik(0);
    setTahap("siap");

    const mime = mimeRekam();
    if (!mime) {
      setGalat("Peramban ini tidak bisa merekam audio. Pakai Chrome, Firefox, atau Safari versi terbaru.");
      setTahap("galat");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false },
      });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 128000 });
      potonganRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) potonganRef.current.push(e.data);
      };
      recorder.onstop = () => {
        void unggahHasil(recorder.mimeType || mime);
      };
      recorder.start(1000);
      recorderRef.current = recorder;
      mulaiRef.current = Date.now();
      analisisLevel(stream);
      timerRef.current = setInterval(() => setDetik((d) => d + 1), 1000);
      setTahap("merekam");
    } catch (err) {
      bersihkanAlat();
      setGalat(pesanGalat(err));
      setTahap("galat");
    }
  };

  const hentikanRekam = () => {
    const recorder = recorderRef.current;
    bersihkanAlat();
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    } else {
      setGalat("Perekam belum berjalan. Tekan Mulai rekam dulu.");
      setTahap("galat");
    }
  };

  const belumSiap = tahap === "merekam" || tahap === "mengunggah";

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Rekam dari peramban</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Rekaman disimpan lalu langsung diproses server. Untuk mengirim berkas
          yang sudah ada, pakai{" "}
          <Link href="/upload" className="focus-ring underline">
            halaman unggah
          </Link>
          . Untuk memperkirakan lokasi suara tanpa rekaman asli, buka{" "}
          <Link href="/simulasi" className="focus-ring underline">
            halaman simulasi
          </Link>
          .
        </p>
      </div>

      {dukung === false && (
        <div role="alert" className="mb-6 rounded-lg border border-[var(--destructive)] bg-[var(--destructive-surface)] p-4">
          <p className="text-sm font-medium text-[var(--destructive)]">
            Perekaman dari peramban tidak bisa dipakai di sini
          </p>
          <p className="mt-1 text-sm text-[var(--foreground)]">
            Peramban ini tidak menyediakan MediaRecorder dengan dukungan perekaman audio, atau
            koneksi ke peramban tidak aman. Pakai Chrome, Firefox, atau Safari versi terbaru
            lewat alamat https atau localhost.
          </p>
        </div>
      )}

      {dukung === null && <Skeleton className="mb-6 h-20 w-full" />}

      {dukung && (
        <section className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs text-[var(--muted-foreground)]">
              Lokasi perekaman
              {memuatSitus ? (
                <Skeleton className="mt-1 h-11 w-full" />
              ) : (
                <select
                  value={siteId}
                  onChange={(e) => {
                    setSiteId(e.target.value);
                    setDeviceId("");
                  }}
                  disabled={belumSiap}
                  className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
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
                <span className="mt-1 block">Belum ada lokasi yang bisa dipakai.</span>
              )}
            </label>

            <label className="text-xs text-[var(--muted-foreground)]">
              Perangkat (opsional)
              <select
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                disabled={belumSiap || perangkat.length === 0}
                className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
                aria-label="Perangkat perekam"
              >
                <option value="">Tanpa perangkat</option>
                {perangkat.map((d: any) => (
                  <option key={d.id} value={String(d.id)}>
                    {d.name}
                  </option>
                ))}
              </select>
              {galatPerangkat && (
                <span className="mt-1 block text-[var(--destructive)]">
                  Daftar perangkat gagal dimuat, rekaman tetap bisa dikirim tanpa perangkat.
                </span>
              )}
            </label>
          </div>

          <div className="mt-6 rounded border border-[var(--border)] bg-[var(--background)] p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
                  Durasi rekaman
                </p>
                <p className="mt-1 text-2xl font-semibold text-[var(--foreground)]" aria-live="off">
                  {formatTimer(detik)}
                </p>
              </div>
              <p role="status" className="text-sm text-[var(--muted-foreground)]">
                {tahap === "merekam"
                  ? "Sedang merekam"
                  : tahap === "mengunggah"
                    ? "Mengunggah rekaman"
                    : tahap === "selesai"
                      ? "Rekaman terkirim"
                      : "Siap merekam"}
              </p>
            </div>

            <div className="mt-4">
              <p className="text-xs text-[var(--muted-foreground)]">Level sinyal mikrofon</p>
              <div className="mt-2 flex gap-1" aria-hidden="true">
                {Array.from({ length: JUMLAH_SEGMEN }).map((_, i) => {
                  const aktif = i < Math.round((level / 100) * JUMLAH_SEGMEN);
                  return (
                    <span
                      key={i}
                      className={`h-6 flex-1 rounded-xs ${
                        aktif ? "bg-[var(--accent)]" : "bg-[var(--muted)]"
                      }`}
                    />
                  );
                })}
              </div>
            </div>

            {persenUnggah !== null && (
              <div className="mt-4">
                <ProgressBar value={persenUnggah} label="Progres unggah" />
              </div>
            )}

            {galat && (
              <p role="alert" className="mt-4 text-sm text-[var(--destructive)]">
                {galat}
              </p>
            )}

            {tahap === "selesai" && rekamanId && (
              <p className="mt-4 text-sm text-[var(--foreground)]">
                Rekaman tersimpan sebagai #{rekamanId}.{" "}
                <Link href={`/recordings/${rekamanId}`} className="focus-ring underline">
                  Lihat progres dan deteksinya
                </Link>
                .
              </p>
            )}

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={mulaiRekam}
                disabled={belumSiap || !siteId}
                className="focus-ring inline-flex min-h-11 items-center justify-center gap-2 rounded bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
              >
                <Mic size={16} aria-hidden="true" />
                {tahap === "selesai" || tahap === "galat" ? "Rekam lagi" : "Mulai rekam"}
              </button>
              <button
                type="button"
                onClick={hentikanRekam}
                disabled={tahap !== "merekam"}
                className="focus-ring inline-flex min-h-11 items-center justify-center gap-2 rounded border border-[var(--border)] px-4 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)] disabled:opacity-50"
              >
                <Square size={16} aria-hidden="true" />
                Berhenti dan unggah
              </button>
            </div>
            {!siteId && (
              <p className="mt-3 text-xs text-[var(--muted-foreground)]">
                Tombol rekam aktif setelah lokasi dipilih.
              </p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
