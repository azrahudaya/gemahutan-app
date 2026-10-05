import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowUpRight,
  AudioLines,
  Bird,
  BookOpen,
  Code,
  FlaskConical,
  Map,
  MapPinned,
  Mic,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { GITHUB, KakiSitus, KepalaSitus } from "@/components/situs";

export const metadata: Metadata = {
  title: "Tentang",
  description: "Apa itu GemaHutan, untuk siapa, tahap pengembangannya, tim di baliknya, serta data dan teknologi yang dipakai.",
};

/*
 * Halaman tentang. Isinya mengikuti docs/VISI_DAN_RUANG_LINGKUP.md; kalau dokumen itu
 * berubah, halaman ini ikut diperbarui. Sumber data ditulis sebagai teks, bukan logo,
 * karena tidak ada kerja sama resmi dengan pemiliknya.
 */

const ALUR = [
  { ikon: Mic, judul: "Rekam", isi: "Alat perekam atau ponsel petugas menangkap suara hutan." },
  { ikon: Bird, judul: "Kenali", isi: "Model mengenali spesies burung dari potongan suara 3 detik." },
  { ikon: MapPinned, judul: "Perkirakan lokasi", isi: "Arah dan jarak dari beberapa alat mempersempit area asal suara. Saat ini masih lewat simulasi." },
];

const PERAN = [
  {
    ikon: ShieldCheck,
    peran: "Admin kawasan",
    siapa: "Pengelola balai taman nasional atau BKSDA",
    kerja: "Membuat akun petugas, mengatur lokasi dan perangkat, menetapkan spesies prioritas, membaca laporan bulanan.",
  },
  {
    ikon: FlaskConical,
    peran: "Peneliti",
    siapa: "Ahli burung dan peneliti mitra",
    kerja: "Memverifikasi deteksi, mengekspor data terverifikasi, memeriksa angka mutu model.",
  },
  {
    ikon: Map,
    peran: "Ranger",
    siapa: "Polisi hutan, petugas lapangan, relawan",
    kerja: "Merekam dan mengunggah, melihat hasil rekamannya sendiri, mencoba simulasi perkiraan lokasi.",
  },
];

const TAHAP = [
  { no: "1", judul: "Perangkat lunak", isi: "Model 25 spesies, aplikasi untuk tiga peran, verifikasi ahli, laporan, simulasi lokasi dengan alat virtual.", kini: true },
  { no: "2", judul: "Uji lapangan", isi: "Satu kawasan mitra, alat perekam terpasang, angka akurasi lapangan yang diverifikasi pakar.", kini: false },
  { no: "3", judul: "Jaringan alat", isi: "Alat dengan jam tersinkron, perkiraan area asal suara dari rekaman nyata, peringatan spesies langka.", kini: false },
  { no: "4", judul: "Peluang dan ancaman", isi: "Peta peluang keberadaan dari riwayat deteksi, serta suara gergaji mesin, tembakan, dan kendaraan.", kini: false },
  { no: "5", judul: "Skala nasional", isi: "Banyak kawasan dalam satu sistem dengan hak akses per kawasan, dan data terbuka.", kini: false },
];

const TIM = [
  { inisial: "AE", nama: "Artya Epriliani", peran: "Ketua tim" },
  { inisial: "AH", nama: "Azra Hudaya", peran: "Anggota tim" },
];

const SUMBER = [
  {
    nama: "Xeno-canto",
    pemilik: "Xeno-canto Foundation",
    guna: "Rekaman suara burung untuk melatih dan menguji model.",
    lisensi: "Creative Commons per rekaman; rekaman berlisensi ND tidak dipakai",
    tautan: "https://xeno-canto.org",
  },
  {
    nama: "iNatSounds",
    pemilik: "Chasmai dkk. (2024), dari pengamatan iNaturalist",
    guna: "Rekaman ponsel sebagai contoh suara bukan target dan bahan uji.",
    lisensi: "Lisensi per pengamatan iNaturalist",
    tautan: "https://huggingface.co/datasets/DBD-research-group/inat_sounds",
  },
  {
    nama: "SEA-Bird",
    pemilik: "Zabidi (2025), Zenodo",
    guna: "Rekaman burung Asia Tenggara yang berasal dari Xeno-canto.",
    lisensi: "CC BY 4.0; rekaman berlisensi ND tidak dipakai",
    tautan: "https://doi.org/10.5281/zenodo.17786115",
  },
  {
    nama: "Indonesian Bird Sounds",
    pemilik: "ULM Data Science Lab, Universitas Lambung Mangkurat (2025)",
    guna: "Rekaman burung Indonesia yang berasal dari Xeno-canto.",
    lisensi: "CC BY-NC 4.0",
    tautan: "https://huggingface.co/datasets/ULM-DS-Lab/indonesian-bird-sounds",
  },
  {
    nama: "BirdNET",
    pemilik: "K. Lisa Yang Center for Conservation Bioacoustics, Cornell Lab of Ornithology, dan Chemnitz University of Technology",
    guna: "Model pendeteksi suara burung dan dasar pengklasifikasi 25 spesies lokal.",
    lisensi: "CC BY-NC-SA 4.0, sehingga GemaHutan hanya untuk tujuan non-komersial",
    tautan: "https://github.com/kahst/BirdNET-Analyzer",
  },
  {
    nama: "OpenStreetMap",
    pemilik: "Kontributor OpenStreetMap",
    guna: "Ubin peta untuk lokasi pemantauan.",
    lisensi: "ODbL",
    tautan: "https://www.openstreetmap.org/copyright",
  },
];

export default function Tentang() {
  return (
    <div className="min-h-screen bg-base-100 font-sans text-base-content">
      <KepalaSitus
        tentangAktif
        aksi={
          <Link href="/" className="btn btn-ghost btn-sm rounded-full hover:no-underline">
            <Upload className="size-4" aria-hidden="true" />
            <span>
              Coba<span className="max-sm:hidden"> tanpa akun</span>
            </span>
          </Link>
        }
      />

      <main className="mx-auto max-w-6xl px-4 pb-24 pt-12 sm:px-6 lg:pt-16">
        <div className="breadcrumbs text-sm text-base-content/70">
          <ul>
            <li>
              <Link href="/" className="inline-block py-1 text-base-content/70 hover:text-base-content">
                Beranda
              </Link>
            </li>
            <li>
              <span aria-current="page">Tentang</span>
            </li>
          </ul>
        </div>

        <section className="hero mt-6 place-items-start" aria-labelledby="judul-tentang">
          <div className="hero-content max-w-3xl flex-col items-start p-0">
            <h1 id="judul-tentang" className="text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl">
              Mendengar hutan untuk menemukan burung langka
            </h1>
            <p className="text-lg text-base-content/70">
              GemaHutan membantu petugas konservasi mengetahui spesies burung yang terdengar di kawasannya, lalu
              memperkirakan di mana burung itu berada dari suara yang ditangkap beberapa alat perekam.
            </p>
          </div>
        </section>

        <ol className="mt-10 grid gap-px overflow-hidden rounded-box border border-base-300 bg-base-300 sm:grid-cols-3" aria-label="Cara kerja singkat">
          {ALUR.map((a, i) => (
            <li key={a.judul} className="flex gap-4 bg-base-100 p-5">
              <span className="text-sm font-semibold tabular-nums text-base-content/50">0{i + 1}</span>
              <div className="grid gap-1">
                <span className="flex items-center gap-2 font-semibold">
                  <a.ikon className="size-5 text-primary" aria-hidden="true" />
                  {a.judul}
                </span>
                <span className="text-sm text-base-content/70">{a.isi}</span>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-20 grid gap-20">
          <section className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="apa">
            <h2 id="apa" className="scroll-mt-28 text-2xl font-semibold tracking-tight lg:sticky lg:top-24 lg:self-start">
              Apa itu GemaHutan
            </h2>
            <div className="grid max-w-2xl gap-4 text-base-content/80">
              <p>
                Survei burung langsung membutuhkan ahli dan waktu lapangan yang panjang. Alat perekam bisa merekam
                hutan berhari-hari, tetapi tidak ada yang sanggup mendengarkan semua rekamannya. GemaHutan memproses
                rekaman itu secara otomatis: mendeteksi spesies, menghitung indeks suara lingkungan, menampilkan
                spektrogram, dan meminta peneliti memverifikasi hasilnya.
              </p>
              <p>
                Lokasi burung langka adalah informasi yang dicari pemburu. Karena itu koordinat tepat deteksi spesies
                prioritas hanya terlihat oleh admin dan peneliti.
              </p>
              <p>
                Aplikasi ini berjalan di peramban laptop dan ponsel, tanpa perlu memasang aplikasi, dan tanpa kartu
                grafis di server.
              </p>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="untuk-siapa">
            <h2 id="untuk-siapa" className="scroll-mt-28 text-2xl font-semibold tracking-tight lg:sticky lg:top-24 lg:self-start">
              Untuk siapa
            </h2>
            <div className="grid gap-4">
              <p className="max-w-2xl text-base-content/80">
                GemaHutan dibuat untuk petugas konservasi, bukan untuk masyarakat umum. Akun dibuat oleh admin kawasan.
              </p>
              <ul className="list rounded-box border border-base-300">
                {PERAN.map((p) => (
                  <li key={p.peran} className="list-row items-start">
                    <p.ikon className="mt-1 size-5 text-base-content/60" aria-hidden="true" />
                    <div>
                      <h3 className="font-semibold">{p.peran}</h3>
                      <p className="text-sm text-base-content/60">{p.siapa}</p>
                    </div>
                    <p className="list-col-wrap text-sm text-base-content/80">{p.kerja}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="tahapan">
            <div className="grid gap-2 lg:sticky lg:top-24 lg:self-start">
              <h2 id="tahapan" className="scroll-mt-28 text-2xl font-semibold tracking-tight">
                Tahapan
              </h2>
              <p className="text-sm text-base-content/60">Alat perekam belum terpasang. Yang berjalan sekarang adalah Tahap 1.</p>
            </div>
            <ol className="grid" aria-label="Lima tahap pengembangan">
              {TAHAP.map((t) => (
                <li
                  key={t.no}
                  className="relative pb-8 pl-12 before:absolute before:top-9 before:bottom-1 before:left-4 before:w-px before:bg-base-300 last:pb-0 last:before:hidden"
                >
                  <span
                    className={
                      t.kini
                        ? "absolute top-0 left-0 grid size-8 place-items-center rounded-full bg-primary text-sm font-semibold text-primary-content"
                        : "absolute top-0 left-0 grid size-8 place-items-center rounded-full border border-dashed border-base-content/40 bg-base-100 text-sm font-semibold text-base-content/70"
                    }
                    aria-hidden="true"
                  >
                    {t.no}
                  </span>
                  <h3 className="flex flex-wrap items-center gap-2 pt-1 font-semibold">
                    Tahap {t.no}: {t.judul}
                    {t.kini ? <span className="badge badge-soft badge-sm px-2.5">Sedang berjalan</span> : <span className="badge badge-ghost badge-sm px-2.5">Rencana</span>}
                  </h3>
                  <p className="mt-1 max-w-xl text-sm text-base-content/70">{t.isi}</p>
                </li>
              ))}
            </ol>
          </section>

          <section id="tim" className="scroll-mt-28 grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="judul-tim">
            <h2 id="judul-tim" className="text-2xl font-semibold tracking-tight lg:sticky lg:top-24 lg:self-start">
              Di balik GemaHutan
            </h2>
            <div className="grid gap-4">
              <p className="max-w-2xl text-base-content/80">GemaHutan dikembangkan oleh tim dua orang.</p>
              <ul className="grid gap-4 sm:grid-cols-2">
                {TIM.map((o) => (
                  <li key={o.nama} className="card card-border border-base-300">
                    <div className="card-body flex-row items-center gap-4 p-5">
                      <div className="avatar avatar-placeholder">
                        <div className="w-12 rounded-full bg-secondary text-secondary-content">
                          <span className="font-semibold" aria-hidden="true">{o.inisial}</span>
                        </div>
                      </div>
                      <div>
                        <h3 className="card-title text-base">{o.nama}</h3>
                        <p className="text-sm text-base-content/60">{o.peran}</p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="sumber">
            <h2 id="sumber" className="scroll-mt-28 text-2xl font-semibold tracking-tight lg:sticky lg:top-24 lg:self-start">
              Data dan teknologi yang kami pakai
            </h2>
            <div className="grid gap-4">
              <p className="max-w-2xl text-base-content/80">
                GemaHutan memakai data dan perangkat lunak terbuka berikut sesuai lisensinya. Pemiliknya tidak terafiliasi
                dengan GemaHutan dan tidak terlibat dalam pengembangannya.
              </p>
              <ul className="list rounded-box border border-base-300">
                {SUMBER.map((s) => (
                  <li key={s.nama} className="list-row items-start">
                    <AudioLines className="mt-1 size-5 text-base-content/50" aria-hidden="true" />
                    <div className="grid gap-1">
                      <h3 className="font-semibold">{s.nama}</h3>
                      <p className="text-sm text-base-content/60">{s.pemilik}</p>
                      <p className="text-sm text-base-content/80">{s.guna}</p>
                      <p className="text-sm text-base-content/60">Lisensi: {s.lisensi}</p>
                    </div>
                    <a
                      href={s.tautan}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-ghost btn-sm hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid"
                    >
                      Kunjungi
                      <ArrowUpRight className="size-3.5" aria-hidden="true" />
                      <span className="sr-only">situs {s.nama} (membuka tab baru)</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16" aria-labelledby="kontak">
            <h2 id="kontak" className="scroll-mt-28 text-2xl font-semibold tracking-tight lg:sticky lg:top-24 lg:self-start">
              Kode dan kontak
            </h2>
            <div className="grid max-w-2xl gap-5">
              <p className="text-base-content/80">
                Kode sumber GemaHutan terbuka. Pertanyaan, laporan masalah, atau tawaran menjadi kawasan uji coba Tahap 2
                bisa dikirim lewat Issues di GitHub.
              </p>
              <div className="flex flex-wrap gap-2">
                <a href={GITHUB} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                  <Code className="size-4" aria-hidden="true" />
                  Buka repositori di GitHub
                  <span className="sr-only">(membuka tab baru)</span>
                </a>
                <Link href="/dokumentasi" className="btn btn-ghost btn-sm hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                  <BookOpen className="size-4" aria-hidden="true" />
                  Baca dokumentasi
                </Link>
              </div>
            </div>
          </section>
        </div>
      </main>

      <KakiSitus awalan="/" />
    </div>
  );
}
