"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Info, TriangleAlert, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { pastikanSesiTamu } from "@/lib/sesi-tamu";
import { KakiSitus, KepalaSitus } from "@/components/situs";

/*
 * Dokumentasi GemaHutan. Menjelaskan alur petugas per peran (masuk lewat undangan,
 * rekam di ponsel, unggah banyak berkas, verifikasi, laporan, simulasi lokasi) dan
 * cara kerja model. Bagian "Coba tanpa akun" tetap ada untuk pengunjung yang ingin
 * menjajal tanpa akun. Ambang per spesies dan daftar batasan dibaca langsung dari
 * /api/v1/model/info lewat sesi demo, jadi angkanya selalu sama dengan model berjalan.
 */

const ISI = [
  { id: "mulai", label: "Mulai" },
  { id: "rekam", label: "Rekam dan unggah" },
  { id: "hasil", label: "Membaca hasil" },
  { id: "verifikasi", label: "Verifikasi" },
  { id: "laporan", label: "Laporan" },
  { id: "simulasi", label: "Simulasi lokasi" },
  { id: "model", label: "Cara kerja model" },
  { id: "berkas", label: "Format berkas" },
  { id: "batasan", label: "Batasan" },
  { id: "masalah", label: "Masalah umum" },
];

const TAHAP: [string, string][] = [
  ["Menunggu antrean", "Rekaman masuk antrean dan menunggu diproses."],
  ["Membaca audio", "Audio dibaca dan disamakan formatnya."],
  ["Deteksi BirdNET", "Tiap potongan 3 detik diperiksa untuk mencari suara burung."],
  ["Klasifikasi spesies", "Model lokal memberi skor per spesies, lalu ambang per spesies diterapkan."],
  ["Menghitung arah", "Hanya untuk rekaman dua kanal atau lebih dari perangkat yang jarak mikrofonnya diketahui."],
  ["Membuat spektrogram", "Gambar frekuensi terhadap waktu dibuat untuk hasil."],
];

const MASALAH: [string, string][] = [
  ["Berkas ditolak saat dipilih", "Pakai MP3, WAV, M4A, FLAC, OGG, AAC, OPUS, atau WEBM, maksimal 200 MB."],
  ["Analisis gagal", "Berkas mungkin rusak atau tidak berisi audio yang bisa dibaca. Coba berkas lain."],
  ["\"Belum ada satwa yang jelas\"", "Model tidak yakin pada satu pun spesies. Coba rekaman yang lebih dekat dengan sumber suara dan minim bising."],
  ["Spesies yang muncul terasa salah", "Model hanya mengenal spesies di daftarnya. Suara di luar daftar bisa tertebak sebagai spesies yang mirip."],
  ["\"Aplikasi belum siap\"", "Server sedang menyala atau terputus. Muat ulang halaman setelah beberapa detik."],
];

type InfoModel = {
  thresholds?: Record<string, number>;
  limits?: string[];
};

export default function Dokumentasi() {
  const [info, setInfo] = useState<InfoModel | null>(null);
  const [nama, setNama] = useState<Record<string, string>>({});
  const [keadaan, setKeadaan] = useState<"muat" | "siap" | "galat">("muat");

  useEffect(() => {
    (async () => {
      try {
        await pastikanSesiTamu();
        const [model, spesies] = await Promise.all([api.getModelInfo(), api.getSpeciesList()]);
        const peta: Record<string, string> = {};
        for (const s of Array.isArray(spesies) ? spesies : []) {
          if (s.common_name_id) peta[s.scientific_name] = s.common_name_id;
        }
        setNama(peta);
        setInfo(model);
        setKeadaan("siap");
      } catch {
        setKeadaan("galat");
      }
    })();
  }, []);

  const ambang = Object.entries(info?.thresholds || {})
    .filter(([k]) => !k.startsWith("_"))
    .sort((a, b) => (nama[a[0]] || a[0]).localeCompare(nama[b[0]] || b[0], "id"));

  return (
    <div className="min-h-screen bg-base-100 font-sans text-base-content">
      <KepalaSitus
        docsAktif
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
              <span aria-current="page">Dokumentasi</span>
            </li>
          </ul>
        </div>

        <header className="mt-6 grid max-w-2xl gap-4">
          <h1 className="text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl">Dokumentasi</h1>
          <p className="text-lg text-base-content/70">Cara memakai GemaHutan dan cara kerjanya.</p>
          <p className="text-sm text-base-content/60">Diperbarui 3 Oktober 2026</p>
        </header>

        <div className="mt-12 grid gap-10 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16">
          <nav aria-label="Isi halaman" className="lg:sticky lg:top-24 lg:self-start">
            <details className="collapse collapse-arrow border border-base-300 bg-base-100 lg:hidden">
              <summary className="collapse-title text-sm font-semibold">Isi halaman</summary>
              <div className="collapse-content">
                <ul className="menu w-full p-0">
                  {ISI.map((s) => (
                    <li key={s.id}>
                      <a href={`#${s.id}`} className="text-base-content hover:text-base-content hover:no-underline">
                        {s.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </details>
            <ul className="menu hidden w-full p-0 lg:flex">
              <li className="menu-title text-base-content/70">Isi halaman</li>
              {ISI.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="text-base-content hover:text-base-content hover:no-underline">
                    {s.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <article className="grid min-w-0 max-w-3xl gap-16">
            <section id="mulai" className="grid scroll-mt-28 gap-5" aria-labelledby="j-mulai">
              <h2 id="j-mulai" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Mulai
              </h2>
              <p className="text-base-content/70">
                Petugas dibuatkan akun oleh admin lewat halaman Pengguna. Undangan berisi tautan untuk
                mengatur sandi, lalu masuk di halaman Masuk. Lupa sandi bisa diatur ulang dari tautan
                di halaman Masuk.
              </p>
              <ol className="grid gap-4">
                {[
                  ["Terima undangan", "Admin membuat akun dengan email Anda. Buka tautan undangan untuk mengatur sandi."],
                  ["Masuk", "Buka halaman Masuk dan pakai email plus sandi yang sudah diatur."],
                  ["Rekam atau unggah", "Rekam langsung dari ponsel di halaman Rekam, atau unggah banyak berkas sekaligus di halaman Unggah."],
                  ["Baca hasil", "Deteksi muncul di Rekaman. Peneliti lalu memverifikasi, dan laporan dirangkum di Laporan."],
                ].map(([judul, isi], i) => (
                  <li key={judul} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-3">
                    <span className="grid size-8 place-items-center rounded-full bg-secondary text-sm font-semibold tabular-nums text-secondary-content">
                      {i + 1}
                    </span>
                    <span className="grid gap-0.5 pt-1">
                      <span className="font-semibold">{judul}</span>
                      <span className="text-base-content/70">{isi}</span>
                    </span>
                  </li>
                ))}
              </ol>
              <div className="grid gap-2">
                <Link href="/login" className="btn btn-primary hover:no-underline">
                  Buka aplikasi
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
                <p className="text-sm text-base-content/60">
                  Belum punya akun dan hanya ingin menjajal? Buka{" "}
                  <Link href="/" className="underline hover:text-base-content">
                    Coba tanpa akun
                  </Link>{" "}
                  untuk mengunggah satu rekaman tanpa akun.
                </p>
              </div>
            </section>

            <section id="rekam" className="grid scroll-mt-28 gap-5" aria-labelledby="j-rekam">
              <h2 id="j-rekam" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Rekam dan unggah
              </h2>
              <dl className="grid gap-4 border-t border-base-300 pt-4">
                {[
                  ["Rekam di ponsel", "Halaman Rekam memakai mikrofon perangkat. Pilih lokasi dulu, tekan Mulai rekam, lalu Berhenti dan unggah. Chrome dan Firefox menyimpan audio/webm, Safari audio/mp4."],
                  ["Unggah banyak berkas", "Halaman Unggah mengirim sampai 20 berkas audio sekaligus ke satu lokasi dalam tiga langkah: pilih lokasi, pilih berkas, kirim."],
                  ["Perangkat (opsional)", "Pilih perangkat supaya asal rekaman tercatat. Perangkat dengan dua kanal atau lebih dipakai untuk memperkirakan arah suara."],
                ].map(([istilah, arti]) => (
                  <div key={istilah} className="grid gap-1 border-b border-base-300 pb-4 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-6">
                    <dt className="font-semibold">{istilah}</dt>
                    <dd className="text-base-content/70">{arti}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section id="hasil" className="grid scroll-mt-28 gap-5" aria-labelledby="j-hasil">
              <h2 id="j-hasil" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Membaca hasil
              </h2>
              <dl className="grid gap-4 border-t border-base-300 pt-4">
                {[
                  ["Spesies terdeteksi", "Spesies yang skor tertingginya minimal 50 persen."],
                  ["Kemungkinan lain", "Spesies dengan skor di bawah 50 persen. Dibuka lewat panel lipat."],
                  ["Persen", "Skor model, bukan peluang benar. Skor tinggi tidak menjamin tebakan tepat."],
                  ["Jumlah × dan waktu mulai", "Berapa potongan 3 detik yang memuat spesies itu, dan kapan pertama terdengar."],
                  ["Tombol Dengar", "Memutar audio tepat di detik spesies itu pertama terdengar."],
                  ["Spektrogram", "Gambar frekuensi terhadap waktu. Kicau burung tampak sebagai garis atau goresan terang."],
                ].map(([istilah, arti]) => (
                  <div key={istilah} className="grid gap-1 border-b border-base-300 pb-4 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-6">
                    <dt className="font-semibold">{istilah}</dt>
                    <dd className="text-base-content/70">{arti}</dd>
                  </div>
                ))}
              </dl>
              <div role="alert" className="alert alert-warning alert-soft">
                <TriangleAlert className="size-5" aria-hidden="true" />
                <span>Hasil adalah prediksi AI dan bisa keliru. Untuk keperluan ilmiah, dengarkan ulang bagian yang ditandai.</span>
              </div>
            </section>

            <section id="verifikasi" className="grid scroll-mt-28 gap-5" aria-labelledby="j-verifikasi">
              <h2 id="j-verifikasi" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Verifikasi
              </h2>
              <p className="text-base-content/70">
                Peneliti dan admin menandai tiap deteksi sebagai benar atau salah di halaman detail
                rekaman. Verifikasi ini yang menurunkan jumlah tebakan palsu, jadi deteksi yang belum
                diverifikasi sebaiknya tidak dipakai sebagai temuan akhir.
              </p>
            </section>

            <section id="laporan" className="grid scroll-mt-28 gap-5" aria-labelledby="j-laporan">
              <h2 id="j-laporan" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Laporan
              </h2>
              <p className="text-base-content/70">
                Halaman Laporan merangkum aktivitas bulanan: jumlah rekaman, deteksi per spesies, dan
                status verifikasi. Bisa dibuka lewat menu Laporan atau tombol di Dasbor.
              </p>
            </section>

            <section id="simulasi" className="grid scroll-mt-28 gap-5" aria-labelledby="j-simulasi">
              <h2 id="j-simulasi" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Simulasi lokasi
              </h2>
              <p className="text-base-content/70">
                Halaman Simulasi memperkirakan posisi sumber suara dari beberapa mikrofon. Saat ini
                masih berupa simulasi untuk memperlihatkan cara kerja lokalisasi, bukan hasil
                pengukuran lapangan.
              </p>
            </section>

            <section id="model" className="grid scroll-mt-28 gap-5" aria-labelledby="j-model">
              <h2 id="j-model" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Cara kerja model
              </h2>
              <p className="text-base-content/70">
                Rekaman dipotong per 3 detik. BirdNET mencari potongan yang berisi suara burung, lalu model lokal GemaHutan
                memberi skor untuk tiap spesies yang dikenalnya. Spesies hanya dilaporkan kalau skornya melewati ambang
                spesies itu.
              </p>
              <div tabIndex={0} role="region" aria-label="Tabel tahap analisis" className="max-w-full overflow-x-auto rounded-box border border-base-300 focus-visible:outline-2 focus-visible:outline-primary">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th className="w-10">#</th>
                      <th>Tahap</th>
                      <th>Yang terjadi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {TAHAP.map(([tahap, isi], i) => (
                      <tr key={tahap}>
                        <th className="tabular-nums text-base-content/60">{i + 1}</th>
                        <td className="whitespace-nowrap font-semibold">{tahap}</td>
                        <td className="min-w-56 text-base-content/70">{isi}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3 className="mt-4 text-lg font-semibold">Ambang per spesies</h3>
              <p className="text-base-content/70">
                Ambang rendah berarti spesies lebih mudah dilaporkan, dengan risiko tebakan palsu lebih besar. Angka di bawah
                dibaca langsung dari model yang sedang berjalan.
              </p>
              {keadaan === "muat" && <div className="skeleton h-14 w-full" />}
              {keadaan === "galat" && (
                <div role="alert" className="alert alert-soft">
                  <Info className="size-5" aria-hidden="true" />
                  <span>Daftar ambang belum bisa dimuat karena server sedang tidak tersambung. Muat ulang halaman nanti.</span>
                </div>
              )}
              {keadaan === "siap" && (
                <details className="collapse collapse-arrow border border-base-300 bg-base-100">
                  <summary className="collapse-title font-semibold">Lihat ambang {ambang.length} spesies</summary>
                  <div className="collapse-content min-w-0">
                    <div tabIndex={0} role="region" aria-label="Tabel ambang per spesies" className="max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-primary">
                      <table className="table table-sm">
                        <thead>
                          <tr>
                            <th>Spesies</th>
                            <th>Nama ilmiah</th>
                            <th className="text-right">Ambang</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ambang.map(([ilmiah, nilai]) => (
                            <tr key={ilmiah}>
                              <td className="font-semibold">{nama[ilmiah] || "–"}</td>
                              <td className="italic text-base-content/70">{ilmiah}</td>
                              <td className="text-right tabular-nums">{nilai.toLocaleString("id-ID", { minimumFractionDigits: 2 })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </details>
              )}
            </section>

            <section id="berkas" className="grid scroll-mt-28 gap-5" aria-labelledby="j-berkas">
              <h2 id="j-berkas" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Format berkas
              </h2>
              <div className="flex flex-wrap gap-2">
                {["MP3", "WAV", "M4A", "FLAC", "OGG", "AAC", "OPUS", "WEBM"].map((f) => (
                  <span key={f} className="badge badge-ghost">
                    {f}
                  </span>
                ))}
              </div>
              <ul className="grid list-disc gap-2 pl-5 text-base-content/70">
                <li>Maksimal 200 MB per berkas.</li>
                <li>Satu berkas per unggahan di halaman depan.</li>
                <li>Rekaman mono cukup untuk mengenali spesies. Arah suara butuh minimal dua kanal.</li>
              </ul>
            </section>

            <section id="batasan" className="grid scroll-mt-28 gap-5" aria-labelledby="j-batasan">
              <h2 id="j-batasan" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Batasan
              </h2>
              <p className="text-base-content/70">Dibaca langsung dari model yang sedang berjalan.</p>
              {keadaan === "muat" && (
                <div className="grid gap-2">
                  <div className="skeleton h-4 w-full" />
                  <div className="skeleton h-4 w-5/6" />
                  <div className="skeleton h-4 w-4/6" />
                </div>
              )}
              {keadaan === "galat" && (
                <div role="alert" className="alert alert-soft">
                  <Info className="size-5" aria-hidden="true" />
                  <span>Daftar batasan belum bisa dimuat. Muat ulang halaman nanti.</span>
                </div>
              )}
              {keadaan === "siap" && (
                <ul className="grid list-disc gap-2 pl-5 text-base-content/70">
                  {(info?.limits || []).map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              )}
            </section>

            <section id="masalah" className="grid scroll-mt-28 gap-5" aria-labelledby="j-masalah">
              <h2 id="j-masalah" className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Masalah umum
              </h2>
              <div className="grid gap-3">
                {MASALAH.map(([gejala, solusi]) => (
                  <details key={gejala} className="collapse collapse-arrow border border-base-300 bg-base-100">
                    <summary className="collapse-title font-semibold">{gejala}</summary>
                    <div className="collapse-content text-base-content/70">{solusi}</div>
                  </details>
                ))}
              </div>
            </section>
          </article>
        </div>
      </main>

      <KakiSitus awalan="/" />
    </div>
  );
}
