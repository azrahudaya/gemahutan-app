"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Cpu,
  ChevronDown,
  FileAudio,
  FileText,
  Mic,
  Microscope,
  Play,
  Smartphone,
  TriangleAlert,
  Trees,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import { labelTahap } from "@/lib/format";
import { pesanGalat } from "@/lib/pesan-galat";
import { pastikanSesiTamu } from "@/lib/sesi-tamu";
import { useAuth } from "@/lib/auth";
import FOTO from "@/lib/foto-burung.json";
import { KakiSitus, KepalaSitus } from "@/components/situs";
import VideoCaraKerja from "@/components/video-cara-kerja";

/*
 * Halaman depan mode demo: unggah satu rekaman, lalu lihat satwa yang terdeteksi.
 * Tidak ada layar login. Tiap pengunjung mendapat akun tamu sendiri lewat /sesi-demo,
 * dan rekamannya masuk ke lokasi pertama yang terlihat oleh akun tamu.
 * Tampilan memakai daisyUI 5 dengan tema "gemahutan" (putih, hijau hutan) dari globals.css.
 * Lingkar foto di pembuka berhenti saat disentuh kursor atau fokus keyboard, dan diam
 * kalau pengguna memilih kurangi gerakan. Animasi lain berjalan sekali saat bagiannya
 * masuk layar. Kredit foto Wikimedia Commons ada di teks alt dan title tiap foto.
 */

type Tahap = "sesi" | "siap" | "mengunggah" | "menganalisis" | "selesai" | "galat";

type Deteksi = {
  id: number;
  species_name: string;
  species_common?: string | null;
  confidence: number;
  start_s: number;
  end_s: number;
};

type Kelompok = {
  ilmiah: string;
  nama: string;
  namaInggris: string | null;
  tertinggi: number;
  jumlah: number;
  waktu: number[];
};

const EKSTENSI = ".mp3,.wav,.m4a,.flac,.ogg,.aac,.opus,.webm";
const MAKS_MB = 200;

const JUDUL = ["Dengar", "hutan,", "temukan", "burung", "langka."];
// Kelas lengkap per kata judul, supaya Tailwind bisa membacanya apa adanya.
const KELAS_KATA = [
  "inline-block animate-kata motion-reduce:animate-none [animation-delay:0ms]",
  "inline-block animate-kata motion-reduce:animate-none [animation-delay:90ms]",
  "inline-block animate-kata motion-reduce:animate-none [animation-delay:180ms]",
  "inline-block animate-kata motion-reduce:animate-none [animation-delay:270ms]",
  "inline-block animate-kata motion-reduce:animate-none [animation-delay:360ms]",
];
const KELAS_CHIP = [
  "badge badge-accent badge-sm absolute top-0 w-max px-2.5 -translate-x-1/4 whitespace-nowrap font-semibold opacity-0 transition delay-[450ms] duration-300 group-data-[tampil=true]:opacity-100 motion-reduce:transition-none sm:-translate-x-1/2",
  "badge badge-accent badge-sm absolute top-7 w-max px-2.5 -translate-x-1/2 whitespace-nowrap font-semibold opacity-0 transition delay-[1000ms] duration-300 group-data-[tampil=true]:opacity-100 motion-reduce:transition-none sm:top-0",
  "badge badge-accent badge-sm absolute top-0 w-max px-2.5 -translate-x-1/2 whitespace-nowrap font-semibold opacity-0 transition delay-[1600ms] duration-300 group-data-[tampil=true]:opacity-100 motion-reduce:transition-none",
  "badge badge-accent badge-sm absolute top-7 w-max px-2.5 -translate-x-3/4 whitespace-nowrap font-semibold opacity-0 transition delay-[2150ms] duration-300 group-data-[tampil=true]:opacity-100 motion-reduce:transition-none sm:top-0 sm:-translate-x-1/2",
];

function formatWaktu(detik: number): string {
  const total = Math.max(0, Math.round(detik));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function formatPersen(nilai: number): string {
  return `${(nilai * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

function formatUkuran(byte: number): string {
  if (byte < 1024 * 1024) return `${Math.max(1, Math.round(byte / 1024))} KB`;
  return `${(byte / 1024 / 1024).toLocaleString("id-ID", { maximumFractionDigits: 1 })} MB`;
}

export default function HalamanDemo() {
  const [tahap, setTahap] = useState<Tahap>("sesi");
  const [galat, setGalat] = useState<string | null>(null);
  const [lokasiId, setLokasiId] = useState("");
  const [berkas, setBerkas] = useState<File | null>(null);
  const [seret, setSeret] = useState(false);
  const [persenUnggah, setPersenUnggah] = useState(0);
  const [progres, setProgres] = useState({ persen: 0, tahap: "" as string | null });
  const [rekaman, setRekaman] = useState<any>(null);
  const [deteksi, setDeteksi] = useState<Deteksi[]>([]);
  const [namaIndonesia, setNamaIndonesia] = useState<Record<string, string>>({});
  const [spektrogram, setSpektrogram] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const hasilRef = useRef<HTMLElement>(null);
  const akarRef = useRef<HTMLDivElement>(null);

  // Akun tamu ditandai domain email. Kalau yang masuk adalah petugas (bukan
  // tamu), halaman depan tidak membuat sesi tamu dan tidak memakai token petugas
  // untuk demo.
  const { user, loading: authLoading } = useAuth();
  const adalahPetugas = !!user && !user.email.endsWith("@tamu.gemahutan.invalid");

  // Buka sesi demo setiap kali halaman dimuat, supaya token tidak pernah kedaluwarsa
  // di tengah analisis.
  const bukaSesi = useCallback(async () => {
    setTahap("sesi");
    setGalat(null);
    try {
      await pastikanSesiTamu();
      const [daftarLokasi, daftarSpesies] = await Promise.all([api.getSites(), api.getSpeciesList()]);
      const situs = daftarLokasi ?? [];
      if (!situs[0]) throw new Error("Akun demo belum punya lokasi pemantauan.");
      setLokasiId(String(situs[0].id));
      const peta: Record<string, string> = {};
      for (const s of daftarSpesies ?? []) {
        if (s.common_name_id) peta[s.scientific_name] = s.common_name_id;
      }
      setNamaIndonesia(peta);
      setTahap("siap");
    } catch (err) {
      setGalat(pesanGalat(err, "Aplikasi belum siap. Muat ulang halaman."));
      setTahap("galat");
    }
  }, []);

  useEffect(() => {
    if (authLoading || adalahPetugas) return;
    void bukaSesi();
  }, [authLoading, adalahPetugas, bukaSesi]);

  useEffect(() => {
    return () => {
      if (spektrogram) URL.revokeObjectURL(spektrogram);
    };
  }, [spektrogram]);

  // Bagian di bawah pembuka muncul saat masuk layar. Tanpa JavaScript atributnya tidak
  // pernah dipasang, jadi isinya tetap terlihat.
  useEffect(() => {
    const target = akarRef.current?.querySelectorAll<HTMLElement>("[data-muncul]");
    if (!target || !("IntersectionObserver" in window)) return;
    const pengamat = new IntersectionObserver(
      (entri) => {
        for (const e of entri) {
          if (!e.isIntersecting) continue;
          (e.target as HTMLElement).dataset.tampil = "true";
          pengamat.unobserve(e.target);
        }
      },
      { threshold: 0.2 },
    );
    target.forEach((el) => {
      el.dataset.tampil = "false";
      pengamat.observe(el);
    });
    return () => pengamat.disconnect();
  }, []);

  const pilih = (daftar: FileList | null) => {
    const f = daftar?.[0];
    if (!f) return;
    setGalat(null);
    if (f.size > MAKS_MB * 1024 * 1024) {
      setGalat(`Berkas ${formatUkuran(f.size)} terlalu besar. Maksimal ${MAKS_MB} MB.`);
      return;
    }
    setBerkas(f);
    void analisis(f);
  };

  const bukaPemilih = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    inputRef.current?.click();
  };

  const tunggu = (ms: number) => new Promise((r) => setTimeout(r, ms));

  const analisis = async (f: File) => {
    if (!lokasiId) return;
    setGalat(null);
    setRekaman(null);
    setDeteksi([]);
    setSpektrogram(null);
    setProgres({ persen: 0, tahap: null });
    setTahap("mengunggah");
    setPersenUnggah(0);
    try {
      const form = new FormData();
      form.append("file", f, f.name);
      form.append("site_id", lokasiId);
      const baru = await api.uploadRecording(form, setPersenUnggah);
      const id = String(baru.id);

      setTahap("menganalisis");
      let r = baru;
      const mulai = Date.now();
      while (r.status !== "done" && r.status !== "failed") {
        await tunggu(2500);
        r = await api.getRecording(id);
        setProgres({ persen: r.progress ?? 0, tahap: r.stage ?? null });
        if (Date.now() - mulai > 15 * 60 * 1000) {
          throw new Error("Analisis belum selesai setelah 15 menit. Cek halaman Rekaman di dashboard.");
        }
      }
      if (r.status === "failed") {
        throw new Error(r.error_message || "Rekaman ini gagal dianalisis. Coba berkas lain.");
      }

      const [hasilDeteksi, gambar] = await Promise.all([
        api.getDetections(id),
        api.getSpectrogram(id).catch(() => null),
      ]);
      setRekaman(r);
      setDeteksi((hasilDeteksi ?? []).map((d) => ({ ...d, species_name: d.species_name ?? "" })));
      if (gambar) setSpektrogram(URL.createObjectURL(gambar as Blob));
      setTahap("selesai");
      setTimeout(() => hasilRef.current?.focus({ preventScroll: true }), 50);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setGalat(pesanGalat(err, "Analisis gagal. Coba lagi."));
      setTahap("galat");
    }
  };

  const dengar = (detik: number) => {
    const a = audioRef.current;
    if (!a) return;
    a.currentTime = detik;
    void a.play();
  };

  const kelompok = useMemo(() => {
    const peta = new Map<string, Kelompok>();
    for (const d of deteksi) {
      const k = peta.get(d.species_name) || {
        ilmiah: d.species_name,
        nama: namaIndonesia[d.species_name] || d.species_name,
        namaInggris: namaIndonesia[d.species_name] ? null : d.species_common || null,
        tertinggi: 0,
        jumlah: 0,
        waktu: [],
      };
      k.tertinggi = Math.max(k.tertinggi, d.confidence);
      k.jumlah += 1;
      k.waktu.push(d.start_s);
      peta.set(d.species_name, k);
    }
    const semua = [...peta.values()].map((k) => ({ ...k, waktu: k.waktu.sort((a, b) => a - b) }));
    semua.sort((a, b) => b.tertinggi - a.tertinggi);
    return {
      yakin: semua.filter((k) => k.tertinggi >= 0.5),
      lain: semua.filter((k) => k.tertinggi < 0.5),
    };
  }, [deteksi, namaIndonesia]);

  const sibuk = tahap === "mengunggah" || tahap === "menganalisis";
  const sukses = tahap === "selesai" && kelompok.yakin.length > 0;
  const persen = tahap === "mengunggah" ? persenUnggah : progres.persen;

  return (
    <div ref={akarRef} className="min-h-screen scroll-smooth bg-base-100 font-sans text-base-content">
      <KepalaSitus
        aksi={
          <button type="button" className="btn btn-ghost btn-sm rounded-full" disabled={!lokasiId || sibuk} onClick={bukaPemilih}>
            <Upload className="size-4" aria-hidden="true" />
            <span>
              Coba<span className="max-sm:hidden"> tanpa akun</span>
            </span>
          </button>
        }
      />

      <section
        className="group relative -mt-[68px] h-[clamp(680px,96vh,900px)] overflow-hidden bg-base-100 max-sm:h-[780px]"
        aria-labelledby="judul-utama"
      >
        <div className="absolute left-1/2 top-[38%] [--r1:clamp(250px,34vw,430px)] [--r2:clamp(150px,20vw,250px)] [transform:perspective(1400px)_rotateX(18deg)] max-sm:top-[24%] max-sm:[--r1:41vw] max-sm:[--r2:23vw]">
          <div className="absolute left-0 top-0 size-[calc(var(--r1)*2)] -translate-x-1/2 -translate-y-1/2 rounded-full border-[1.5px] border-dashed border-accent/40" aria-hidden="true" />
          <div className="absolute left-0 top-0 size-[calc(var(--r2)*2)] -translate-x-1/2 -translate-y-1/2 rounded-full border-[1.5px] border-dashed border-accent/40" aria-hidden="true" />
          {[FOTO.slice(0, 8), FOTO.slice(8)].map((cincin, ci) => (
            <div
              key={ci}
              className={
                ci === 0
                  ? "absolute left-0 top-0 animate-orbit group-focus-within:[animation-play-state:paused] group-hover:[animation-play-state:paused] motion-reduce:animate-none"
                  : "absolute left-0 top-0 animate-orbit-dalam group-focus-within:[animation-play-state:paused] group-hover:[animation-play-state:paused] motion-reduce:animate-none"
              }
            >
              {cincin.map((f, k) => {
                const sudut = (360 / cincin.length) * k + ci * 18;
                const kredit = `${f.nama} (${f.ilmiah}). Foto: ${f.artis}, ${f.lisensi}, Wikimedia Commons`;
                return (
                  <div
                    key={f.berkas}
                    className="absolute left-0 top-0"
                    style={{ transform: `rotate(${sudut}deg) translateY(calc(-1 * var(${ci === 0 ? "--r1" : "--r2"}))) rotate(${-sudut}deg)` }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/burung/${f.berkas}`}
                      alt={kredit}
                      title={kredit}
                      width={360}
                      height={360}
                      className={
                        ci === 0
                          ? "absolute max-w-none -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-base-100 object-cover shadow-lg group-focus-within:[animation-play-state:paused] group-hover:[animation-play-state:paused] motion-reduce:animate-none size-[clamp(78px,8.4vw,118px)] animate-orbit-balik max-sm:size-16"
                          : "absolute max-w-none -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-base-100 object-cover shadow-lg group-focus-within:[animation-play-state:paused] group-hover:[animation-play-state:paused] motion-reduce:animate-none size-[clamp(62px,6.4vw,90px)] animate-orbit-dalam-balik max-sm:size-12"
                      }
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="pointer-events-none absolute inset-0 z-[2] bg-linear-to-t from-base-100 from-25% via-base-100/90 via-45% to-transparent to-70% max-sm:from-45% max-sm:via-60% max-sm:to-80%" />

        <div className="absolute inset-x-0 bottom-[clamp(36px,7vh,80px)] z-[3] grid justify-items-center gap-4 px-4 text-center">
          <h1 id="judul-utama" className="text-5xl leading-[1.05] font-bold tracking-[-0.035em] text-balance sm:text-6xl lg:text-7xl">
            {JUDUL.map((kata, i) => (
              <Fragment key={kata}>
                <span className="inline-block overflow-hidden pb-[0.08em] align-bottom">
                  <span className={KELAS_KATA[i]}>{kata}</span>
                </span>
                {i < JUDUL.length - 1 ? " " : ""}
              </Fragment>
            ))}
          </h1>
          <p className="max-w-xl animate-muncul text-lg text-pretty text-base-content/70 [animation-delay:450ms] motion-reduce:animate-none">
            GemaHutan mendengar hutan untuk menemukan burung langka lewat suaranya.
          </p>

          {!adalahPetugas && (
            <div className="mt-3 flex flex-wrap items-center justify-center gap-3 animate-muncul [animation-delay:550ms] motion-reduce:animate-none">
              <Link href="/login" className="btn btn-primary">
                Masuk
              </Link>
            </div>
          )}

          <div id="unggah" className="mt-2 grid w-full max-w-[600px] animate-muncul gap-2 text-left [animation-delay:600ms] motion-reduce:animate-none">
            {!adalahPetugas && (
              <p className="text-center text-sm text-base-content/70">
                Coba tanpa akun: unggah satu rekaman suara dan lihat hasil deteksinya.
              </p>
            )}
            {adalahPetugas && (
              <div className="flex flex-wrap items-center justify-center gap-3 rounded-box border border-base-300 bg-base-100 px-5 py-4 sm:justify-between">
                <span className="text-base-content/80">Anda sudah masuk sebagai petugas.</span>
                <Link href="/dashboard" className="btn btn-primary btn-sm">
                  Buka aplikasi
                </Link>
              </div>
            )}
            {!adalahPetugas && tahap === "sesi" && (
              <div className="flex items-center gap-3 rounded-box border border-base-300 bg-base-100 px-5 py-4 text-base-content/70">
                <span className="loading loading-spinner loading-sm text-primary" aria-hidden="true" />
                Menyiapkan aplikasi…
              </div>
            )}

            {!adalahPetugas && sibuk && (
              <div className="grid gap-3 rounded-box border border-base-300 bg-base-100 px-5 py-4" role="status" aria-live="polite">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="loading loading-spinner loading-sm shrink-0 text-primary" aria-hidden="true" />
                    <span className="truncate">
                      {tahap === "mengunggah" ? "Mengunggah" : progres.tahap ? labelTahap(progres.tahap) : "Menunggu giliran"}
                      {berkas && <span className="text-base-content/70"> · {berkas.name}</span>}
                    </span>
                  </span>
                  <span className="tabular-nums text-base-content/70">{persen}%</span>
                </div>
                <progress className="progress w-full" value={persen} max={100} aria-label="Progres analisis" />
              </div>
            )}

            {!adalahPetugas && (tahap === "siap" || tahap === "galat" || tahap === "selesai") && (
              <div
                className={
                  sukses
                    ? "mx-auto flex w-full items-center gap-4 sm:w-fit sm:pr-8 rounded-box border-2 border-solid border-primary bg-base-100 p-3 pr-5 transition-colors animate-pantul motion-reduce:animate-none max-sm:flex-col max-sm:items-stretch max-sm:p-4 max-sm:text-center"
                    : seret
                      ? "mx-auto flex w-full items-center gap-4 sm:w-fit sm:pr-8 rounded-box border-2 border-dashed border-primary bg-secondary p-3 pr-5 transition-colors max-sm:flex-col max-sm:items-stretch max-sm:p-4 max-sm:text-center"
                      : "mx-auto flex w-full items-center gap-4 sm:w-fit sm:pr-8 rounded-box border-2 border-dashed border-base-content/20 bg-base-100 p-3 pr-5 transition-colors hover:border-primary/50 max-sm:flex-col max-sm:items-stretch max-sm:p-4 max-sm:text-center"
                }
                onDragOver={(e) => {
                  e.preventDefault();
                  setSeret(true);
                }}
                onDragLeave={() => setSeret(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setSeret(false);
                  pilih(e.dataTransfer.files);
                }}
              >
                <button type="button" className="btn btn-primary btn-lg shrink-0" disabled={!lokasiId} onClick={() => inputRef.current?.click()}>
                  <Upload className="size-5" aria-hidden="true" />
                  {tahap === "selesai" ? "Rekaman lain" : "Pilih rekaman"}
                </button>
                <div className="grid min-w-0 gap-0.5">
                  {sukses ? (
                    <span className="flex items-center gap-2 font-semibold text-primary max-sm:justify-center">
                      <svg viewBox="0 0 24 24" className="size-6 rounded-full bg-secondary p-1" aria-hidden="true">
                        <path
                          d="M5 13l4 4L19 7"
                          className="animate-centang fill-none stroke-current [stroke-dasharray:24] [stroke-linecap:round] [stroke-linejoin:round] [stroke-width:3] motion-reduce:animate-none"
                        />
                      </svg>
                      {kelompok.yakin.length} spesies terdeteksi
                    </span>
                  ) : (
                    <span className="font-medium">{tahap === "selesai" ? "Belum ada satwa yang jelas" : "atau tarik berkas ke sini"}</span>
                  )}
                  <span className="text-xs text-base-content/70">MP3, WAV, M4A, FLAC · maks {MAKS_MB} MB</span>
                </div>
              </div>
            )}

            <input
              ref={inputRef}
              id="berkas-audio"
              type="file"
              accept={EKSTENSI}
              tabIndex={-1}
              aria-hidden="true"
              aria-label="Berkas rekaman"
              className="sr-only"
              onChange={(e) => pilih(e.target.files)}
            />

            <div className="min-h-9 text-sm max-sm:text-center">
              {galat ? (
                <div role="alert" className="alert alert-error alert-soft py-2">
                  <TriangleAlert className="size-4" aria-hidden="true" />
                  <span>{galat}</span>
                  {!lokasiId && (
                    <button type="button" className="btn btn-sm" onClick={bukaSesi}>
                      Coba lagi
                    </button>
                  )}
                </div>
              ) : tahap === "selesai" ? (
                <a href="#judul-hasil" className="link link-primary inline-flex items-center gap-1">
                  Lihat hasil
                  <ChevronDown className="size-4" aria-hidden="true" />
                </a>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <main>
        {tahap === "selesai" && rekaman && (
          <div className="mx-auto max-w-3xl px-4 pt-6 sm:px-6">
            <section
              ref={hasilRef}
              tabIndex={-1}
              aria-labelledby="judul-hasil"
              className="card scroll-mt-20 border border-base-300 bg-base-100 outline-none"
            >
              <div className="card-body gap-5">
                <div>
                  <h2 id="judul-hasil" className="card-title text-2xl font-semibold tracking-tight">
                    {kelompok.yakin.length === 0
                      ? "Belum ada satwa yang terdengar jelas"
                      : `${kelompok.yakin.length} spesies terdeteksi`}
                  </h2>
                  <p className="text-sm text-base-content/70">
                    {berkas?.name}
                    {rekaman.duration_s ? ` · ${formatWaktu(rekaman.duration_s)}` : ""}
                  </p>
                </div>

                <audio ref={audioRef} controls preload="metadata" src={api.getAudioUrl(String(rekaman.id))} className="w-full">
                  Peramban ini tidak bisa memutar audio.
                </audio>

                {kelompok.yakin.length > 0 ? (
                  <ul className="border-t border-base-300">
                    {kelompok.yakin.map((k) => (
                      <li key={k.ilmiah} className="flex items-center justify-between gap-3 border-b border-base-300 py-4">
                        <div className="grid min-w-0 gap-0.5">
                          <p className="text-lg font-semibold">{k.nama}</p>
                          <p className="text-sm text-base-content/70">
                            {k.nama !== k.ilmiah && <em>{k.ilmiah} · </em>}
                            <span className="tabular-nums">
                              {formatPersen(k.tertinggi)} · {k.jumlah}× · mulai {formatWaktu(k.waktu[0])}
                            </span>
                          </p>
                        </div>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => dengar(k.waktu[0])}
                          aria-label={`Dengar ${k.nama} mulai ${formatWaktu(k.waktu[0])}`}
                        >
                          <Play className="size-4" aria-hidden="true" />
                          Dengar
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-base-content/70">Coba rekaman yang lebih dekat dengan sumber suara.</p>
                )}

                {kelompok.lain.length > 0 && (
                  <details className="collapse collapse-arrow border border-base-300 bg-base-100">
                    <summary className="collapse-title text-sm font-semibold">Kemungkinan lain ({kelompok.lain.length})</summary>
                    <div className="collapse-content">
                      <ul>
                        {kelompok.lain.map((k) => (
                          <li key={k.ilmiah} className="flex items-center justify-between gap-3 border-b border-base-300 py-3 last:border-b-0">
                            <div className="grid min-w-0 gap-0.5">
                              <p className="font-semibold">{k.nama}</p>
                              <p className="text-sm tabular-nums text-base-content/70">
                                {formatPersen(k.tertinggi)} · mulai {formatWaktu(k.waktu[0])}
                              </p>
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => dengar(k.waktu[0])}
                              aria-label={`Dengar ${k.nama} mulai ${formatWaktu(k.waktu[0])}`}
                            >
                              <Play className="size-4" aria-hidden="true" />
                              Dengar
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </details>
                )}

                {spektrogram && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={spektrogram} alt="Spektrogram rekaman: frekuensi suara terhadap waktu" className="block h-auto w-full rounded-field object-contain" />
                )}

                <p className="text-sm text-base-content/70">
                  Hasil prediksi AI dan bisa keliru. Baca cara membacanya di{" "}
                  <Link href="/dokumentasi#hasil" className="link">
                    dokumentasi
                  </Link>
                  .
                </p>
              </div>
            </section>
          </div>
        )}

        <section id="masalah" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-24 sm:px-6 lg:pt-32" aria-labelledby="judul-masalah">
          <div data-muncul className="grid gap-4 lg:grid-cols-12 lg:gap-8 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
            <h2 id="judul-masalah" className="text-3xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-4xl lg:col-span-7 lg:text-5xl">
              Rekaman menumpuk. Waktu untuk mendengar tidak ada.
            </h2>
            <p className="text-lg text-pretty text-base-content/70 lg:col-span-4 lg:col-start-9 lg:self-end">
              GemaHutan yang menyisir.
            </p>
          </div>

          <figure data-muncul className="group mt-12 overflow-hidden rounded-box border border-base-300 bg-base-100 shadow-sm transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
            <div className="px-4 pb-4 pt-5 sm:px-6 sm:pb-6">
              <div className="relative h-44 pt-14 sm:h-40 sm:pt-9" aria-hidden="true">
                <div className="flex h-full items-center gap-px sm:gap-[2px]">
                  {BATANG.map((tinggi, i) => (
                    <span key={i} className="min-w-px flex-1 rounded-xs bg-base-300" style={{ height: `${tinggi}%` }} />
                  ))}
                </div>
                <div className="absolute inset-x-0 bottom-0 top-14 flex items-center gap-px transition-[clip-path] duration-[2400ms] ease-in-out [clip-path:inset(0_100%_0_0)] group-data-[tampil=true]:[clip-path:inset(0_0_0_0)] motion-reduce:transition-none sm:top-9 sm:gap-[2px]">
                  {BATANG.map((tinggi, i) => (
                    <span
                      key={i}
                      className={TANDA.some((t) => i >= t.mulai && i <= t.akhir) ? "min-w-px flex-1 rounded-xs bg-accent" : "min-w-px flex-1 rounded-xs bg-transparent"}
                      style={{ height: `${tinggi}%` }}
                    />
                  ))}
                </div>
                <span className="absolute bottom-0 left-0 top-12 w-0.5 bg-primary transition-[left,opacity] delay-[0ms,2400ms] duration-[2400ms,400ms] ease-in-out group-data-[tampil=true]:left-full group-data-[tampil=true]:opacity-0 motion-reduce:hidden sm:top-7" />
                {TANDA.map((t, i) => (
                  <span key={t.mulai} className={KELAS_CHIP[i]} style={{ left: `${((t.mulai + t.akhir) / 2 / BATANG.length) * 100}%` }}>
                    {t.nama}
                  </span>
                ))}
              </div>
            </div>
            <figcaption className="sr-only">
              Ilustrasi rekaman satu minggu. GemaHutan menyisir dari awal sampai akhir dan menandai empat bagian berisi
              suara burung: {TANDA.map((t) => t.nama).join(", ")}.
            </figcaption>
          </figure>
        </section>

        <section id="cara-kerja" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-24 sm:px-6 lg:pt-32" aria-labelledby="judul-cara">
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
            <div data-muncul className="grid content-start gap-4 lg:sticky lg:top-28 lg:col-span-4 lg:self-start transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
              <h2 id="judul-cara" className="text-3xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-4xl lg:text-5xl">
                Dari rekaman ke laporan.
              </h2>
              <div>
                <Link href="/dokumentasi" className="btn btn-sm">
                  <FileText className="size-4" aria-hidden="true" />
                  Baca docs
                </Link>
              </div>
            </div>

            <ol className="grid grid-cols-2 gap-x-4 gap-y-8 sm:block lg:col-span-8">
              <Langkah nomor="01" judul="Rekam atau unggah" isi="Dari alat perekam atau ponsel.">
                <div className="grid gap-2">
                  <span className="flex items-center gap-2 whitespace-nowrap rounded-field border border-base-300 bg-base-100 px-2 py-1.5 text-[11px] font-semibold shadow-sm sm:px-3 sm:py-2 sm:text-xs">
                    <Mic className="size-4 text-error" />
                    pagi.wav
                  </span>
                  <span className="ml-3 flex -rotate-2 items-center gap-2 whitespace-nowrap rounded-field border border-base-300 bg-base-100 px-2 py-1.5 text-[11px] font-semibold shadow-sm sm:ml-6 sm:px-3 sm:py-2 sm:text-xs">
                    <FileAudio className="size-4 text-primary" />
                    rekaman-pagi.mp3
                  </span>
                </div>
              </Langkah>
              <Langkah nomor="02" judul="Disaring otomatis" isi="Suara satwa ditandai tiap 3 detik.">
                <div className="relative mt-5 flex h-12 w-[85%] items-center gap-[2px] sm:mt-0 sm:h-16">
                  {BATANG.slice(20, 48).map((tinggi, i) => (
                    <span key={i} className={i >= 9 && i <= 14 ? "flex-1 rounded-xs bg-accent" : "flex-1 rounded-xs bg-base-300"} style={{ height: `${tinggi}%` }} />
                  ))}
                  <span className="absolute -inset-y-2 left-[30%] w-[23%] rounded-field border-2 border-accent" />
                  <span className="badge badge-accent badge-xs absolute -top-7 left-[41.5%] w-max -translate-x-1/2 px-2 sm:-top-8">3 detik</span>
                </div>
              </Langkah>
              <Langkah nomor="03" judul="Diprediksi AI" isi="AI menebak spesies dari suaranya.">
                <div className="grid w-[94%] max-w-56 gap-2 rounded-box border border-base-300 bg-base-100 p-2 shadow-sm sm:gap-3 sm:p-3">
                  <span className="flex min-w-0 items-center gap-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`/burung/${FOTO[1].berkas}`} alt="" width={36} height={36} loading="lazy" className="size-7 rounded-full object-cover sm:size-9" />
                    <span className="grid min-w-0">
                      <span className="truncate text-xs font-semibold sm:text-sm">{FOTO[1].nama}</span>
                      <span className="flex items-center gap-1 text-[11px] text-base-content/70 sm:text-xs">
                        <Cpu className="size-3" />
                        Prediksi AI
                      </span>
                    </span>
                  </span>
                  <span className="h-1.5 overflow-hidden rounded-full bg-base-300">
                    <span className="block h-full w-[86%] rounded-full bg-accent" />
                  </span>
                </div>
              </Langkah>
              <Langkah nomor="04" judul="Hasil langsung" isi="Spesies, waktu, dan spektrogram.">
                <div className="grid w-[94%] max-w-56 gap-1.5 rounded-box border border-base-300 bg-base-100 p-2 shadow-sm sm:p-3">
                  {[
                    [FOTO[1].nama, "0:12"],
                    [FOTO[9].nama, "1:47"],
                  ].map(([nama, waktu]) => (
                    <span key={nama} className="flex items-center justify-between gap-2 border-b border-base-300 pb-1.5 text-[11px] last:border-b-0 last:pb-0 sm:text-xs">
                      <span className="truncate font-semibold">{nama}</span>
                      <span className="flex shrink-0 items-center gap-1 tabular-nums text-base-content/70">
                        <Play className="size-3" />
                        {waktu}
                      </span>
                    </span>
                  ))}
                  <span className="mt-0.5 h-5 rounded-field bg-[linear-gradient(90deg,var(--color-base-200)_0%,var(--color-accent)_30%,var(--color-base-200)_45%,var(--color-base-200)_70%,var(--color-accent)_82%,var(--color-base-200)_95%)] opacity-70" />
                </div>
              </Langkah>
            </ol>
          </div>
        </section>

        <section id="untuk-siapa" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-24 sm:px-6 lg:pt-32" aria-labelledby="judul-siapa">
          <h2 id="judul-siapa" data-muncul className="max-w-2xl text-3xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-4xl lg:text-5xl transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
            Untuk penjaga hutan.
          </h2>
          <ul className="mt-12 border-t border-base-300">
            {PERAN.map(({ Ikon, judul, isi }) => (
              <li key={judul} data-muncul className="grid gap-2 border-b border-base-300 py-7 md:grid-cols-[1fr_1.4fr] md:items-baseline md:gap-8 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
                <h3 className="flex items-center gap-3 text-xl font-semibold tracking-tight sm:text-2xl">
                  <Ikon className="size-6 shrink-0 text-base-content/70" aria-hidden="true" />
                  {judul}
                </h3>
                <p className="max-w-xl text-base-content/70">{isi}</p>
              </li>
            ))}
          </ul>
        </section>

        <section id="tahap" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-24 sm:px-6 lg:pt-32" aria-labelledby="judul-tahap">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 id="judul-tahap" data-muncul className="max-w-2xl text-3xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-4xl lg:text-5xl transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
              Lima tahap menuju skala nasional.
            </h2>
            <Link href="/tentang#tahapan" className="btn btn-ghost btn-sm">
              Selengkapnya di Tentang
            </Link>
          </div>
          <ol className="mt-10 grid gap-px overflow-hidden rounded-box border border-base-300 bg-base-300 sm:grid-cols-5">
            {TAHAP.map((t) => (
              <li key={t.no} data-muncul className="grid gap-2 bg-base-100 p-5 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
                <span className="text-xs font-semibold tabular-nums text-base-content/60">Tahap {t.no}</span>
                <h3 className="font-semibold">{t.judul}{t.kini ? " (berjalan)" : ""}</h3>
                <p className="text-sm text-base-content/70">{t.isi}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="simulasi" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-24 sm:px-6 lg:pt-32" aria-labelledby="judul-simulasi">
          <h2 id="judul-simulasi" data-muncul className="mx-auto max-w-5xl text-3xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-4xl lg:text-5xl transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
            Lihat prosesnya.
          </h2>
          <div data-muncul className="mt-10 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none">
            <VideoCaraKerja />
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6 lg:py-32" aria-labelledby="judul-ajakan">
          <div
            data-muncul
            className="relative overflow-hidden rounded-box bg-primary px-6 py-14 text-primary-content sm:px-12 sm:py-16 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none"
          >
            <div className="relative grid max-w-xl gap-5">
              <h2 id="judul-ajakan" className="text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl">
                Masuk untuk mengelola rekaman lapangan.
              </h2>
              <p className="text-lg text-primary-content">Petugas konservasi dan peneliti masuk lewat akun dari admin kawasan.</p>
              <div className="flex flex-wrap gap-3">
                <Link href="/login" className="btn btn-lg border-base-100 bg-base-100 text-primary hover:bg-base-200 hover:no-underline">
                  Masuk
                </Link>
                <button type="button" className="btn btn-lg btn-outline border-primary-content/40 text-primary-content hover:border-primary-content/70 hover:bg-primary-content/10" disabled={!lokasiId || sibuk} onClick={bukaPemilih}>
                  <Upload className="size-5" aria-hidden="true" />
                  Coba tanpa akun
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <KakiSitus />
    </div>
  );
}

function Langkah({ nomor, judul, isi, children }: { nomor: string; judul: string; isi: string; children: ReactNode }) {
  return (
    <li
      data-muncul
      className="grid content-start gap-3 sm:grid-cols-[minmax(0,1fr)_15rem] sm:items-center sm:gap-10 sm:border-b sm:border-base-300 sm:py-8 sm:first:pt-0 transition duration-700 ease-out data-[tampil=false]:translate-y-4 data-[tampil=false]:opacity-0 motion-reduce:transition-none"
    >
      <div className="grid gap-1 sm:gap-2">
        <span className="text-xs font-semibold tabular-nums text-base-content/60 sm:text-sm">{nomor}</span>
        <h3 className="text-base font-semibold tracking-tight sm:text-2xl">{judul}</h3>
        <p className="text-sm text-base-content/70 sm:text-base">{isi}</p>
      </div>
      <div className="relative grid h-32 place-items-center overflow-hidden rounded-box bg-base-200 max-sm:order-first sm:h-40" aria-hidden="true">
        {children}
      </div>
    </li>
  );
}

const PERAN = [
  {
    Ikon: Trees,
    judul: "Pengelola kawasan",
    isi: "Tahu spesies apa yang terdengar di rekaman.",
  },
  {
    Ikon: Microscope,
    judul: "Peneliti dan ahli burung",
    isi: "Saring jam rekaman jadi daftar spesies.",
  },
  {
    Ikon: Smartphone,
    judul: "Ranger dan relawan",
    isi: "Unggah rekaman langsung dari ponsel.",
  },
];

// Lima tahap pengembangan, selaras dengan halaman /tentang.
const TAHAP = [
  { no: "1", judul: "Perangkat lunak", isi: "Model 25 spesies, aplikasi tiga peran, verifikasi ahli, laporan, simulasi lokasi.", kini: true },
  { no: "2", judul: "Uji lapangan", isi: "Satu kawasan mitra, alat perekam terpasang, angka akurasi lapangan yang diverifikasi pakar.", kini: false },
  { no: "3", judul: "Jaringan alat", isi: "Alat dengan jam tersinkron, perkiraan area asal suara dari rekaman nyata, peringatan spesies langka.", kini: false },
  { no: "4", judul: "Peluang dan ancaman", isi: "Peta peluang keberadaan dari riwayat deteksi, plus suara gergaji mesin, tembakan, dan kendaraan.", kini: false },
  { no: "5", judul: "Skala nasional", isi: "Banyak kawasan dalam satu sistem dengan hak akses per kawasan, dan data terbuka.", kini: false },
];


// Pita gelombang ilustrasi. Tingginya dihitung dari rumus tetap supaya hasil server dan
// peramban sama persis.
const BATANG = Array.from({ length: 112 }, (_, i) => {
  const dasar = Math.abs(Math.sin(i * 1.7) * 0.55 + Math.sin(i * 0.37) * 0.45);
  return Math.round(10 + dasar * 34);
});
const TANDA = [
  { mulai: 12, akhir: 18, nama: FOTO[1].nama },
  { mulai: 40, akhir: 45, nama: FOTO[9].nama },
  { mulai: 66, akhir: 73, nama: FOTO[13].nama },
  { mulai: 93, akhir: 98, nama: FOTO[3].nama },
];
for (const t of TANDA) {
  for (let i = t.mulai; i <= t.akhir; i++) BATANG[i] = Math.round(48 + Math.abs(Math.sin(i * 2.3)) * 46);
}
