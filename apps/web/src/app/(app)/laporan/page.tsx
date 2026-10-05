"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { ErrorState, Skeleton } from "@/components/ui";

const CSS_CETAK = `
@media print {
  @page { margin: 15mm; }
  body {
    background: #FFFFFF !important;
    color: #000000 !important;
  }
  aside, header, nav { display: none !important; }
  .tanpa-cetak { display: none !important; }
  .lembar-cetak, .lembar-cetak * {
    background: #FFFFFF !important;
    color: #000000 !important;
    border-color: #999999 !important;
    box-shadow: none !important;
  }
  .lembar-cetak a { text-decoration: none !important; }
  .lembar-cetak table { page-break-inside: auto; }
  .lembar-cetak tr { page-break-inside: avoid; }
  .lembar-cetak h2 { page-break-after: avoid; }
}
`;

function tanggalSingkat(nilai?: string | null): string {
  if (!nilai) return "-";
  const bersih = String(nilai).slice(0, 10);
  const bagian = bersih.split("-");
  if (bagian.length !== 3) return bersih;
  const d = new Date(Number(bagian[0]), Number(bagian[1]) - 1, Number(bagian[2]));
  if (Number.isNaN(d.getTime())) return bersih;
  return d.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function angka(nilai?: number | null): string {
  if (nilai == null || Number.isNaN(nilai)) return "-";
  return nilai.toLocaleString("id-ID");
}

function ambangTeks(nilai?: number | null): string {
  if (nilai == null || Number.isNaN(nilai)) return "-";
  return nilai.toFixed(2).replace(".", ",");
}

export default function LaporanPage() {
  const overview = useQuery({
    queryKey: ["laporan-overview"],
    queryFn: () => api.getStatsOverview(),
    staleTime: 60000,
  });

  const timeline = useQuery({
    queryKey: ["laporan-timeline"],
    queryFn: () => api.getStatsTimeline(),
    staleTime: 60000,
  });

  const spesies = useQuery({
    queryKey: ["laporan-spesies"],
    queryFn: () => api.getSpeciesList(),
    staleTime: 60000,
  });

  const lokasi = useQuery({
    queryKey: ["laporan-lokasi"],
    queryFn: () => api.getSites({ limit: "100", page_size: "100" }),
    staleTime: 60000,
  });

  const infoModel = useQuery({
    queryKey: ["laporan-model"],
    queryFn: () => api.getModelInfo(),
    staleTime: 300000,
  });

  const memuat =
    overview.isLoading || timeline.isLoading || spesies.isLoading || lokasi.isLoading;
  const galat = overview.isError || timeline.isError || spesies.isError || lokasi.isError;

  if (memuat) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Skeleton className="mb-3 h-8 w-72" />
        <Skeleton className="mb-6 h-4 w-96" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (galat) {
    const pesan =
      (overview.error as Error)?.message ||
      (spesies.error as Error)?.message ||
      "Angka laporan tidak bisa dibaca dari API.";
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <ErrorState
          title="Laporan tidak bisa dimuat"
          message={pesan}
          onRetry={() => {
            overview.refetch();
            timeline.refetch();
            spesies.refetch();
            lokasi.refetch();
          }}
        />
      </div>
    );
  }

  const ringkas = overview.data ?? { recordings: 0, detections: 0, species_detected: 0, sites: 0 };
  const daftarSpesies: any[] = Array.isArray(spesies.data) ? spesies.data : [];
  const daftarLokasi: any[] = Array.isArray(lokasi.data) ? lokasi.data : [];
  const deretHari: any[] = Array.isArray(timeline.data) ? timeline.data : [];

  const hariAwal = deretHari.length > 0 ? deretHari[0]?.date : null;
  const hariAkhir = deretHari.length > 0 ? deretHari[deretHari.length - 1]?.date : null;

  const batas: string[] = Array.isArray(infoModel.data?.limits) ? infoModel.data.limits : [];
  // Spesies yang dikenali dikenali model lokal dibaca dari kolom model_supported yang
  // sekarang dikirim /api/v1/species. Sebelumnya penanda ini diturunkan dari daftar
  // ambang, dan deklarasinya sempat dipakai sebelum barisnya sendiri sehingga
  // halaman ini gagal dimuat di browser.
  const namaAmbangLokal = new Set<string>(
    daftarSpesies
      .filter((s) => s.model_supported)
      .map((s) => String(s.scientific_name))
  );

  const spesiesModel = daftarSpesies.filter((s) =>
    namaAmbangLokal.has(String(s.scientific_name)),
  ).length;
  const spesiesTerurut = [...daftarSpesies].sort((a, b) => {
    const d = (b.detection_count || 0) - (a.detection_count || 0);
    if (d !== 0) return d;
    return String(a.scientific_name).localeCompare(String(b.scientific_name));
  });
  const sekarang = new Date();

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <style>{CSS_CETAK}</style>

      <div className="tanpa-cetak mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-[var(--muted-foreground)]">
          Halaman ini disusun untuk dicetak. Semua angka dibaca dari API saat halaman dibuka,
          tidak ada angka yang ditulis tangan.
        </p>
        <button
          type="button"
          onClick={() => window.print()}
          className="focus-ring inline-flex min-h-11 items-center rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)]"
        >
          Cetak laporan
        </button>
      </div>

      <article className="lembar-cetak rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <header className="border-b border-[var(--border)] pb-4">
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">
            Laporan Ringkas Pemantauan Akustik
          </h1>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            GemaHutan, Passive Acoustic Monitoring biodiversitas hutan Indonesia
          </p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Periode data</dt>
              <dd className="text-[var(--foreground)]">
                {tanggalSingkat(hariAwal)} sampai {tanggalSingkat(hariAkhir)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Tanggal laporan</dt>
              <dd className="text-[var(--foreground)]">{sekarang.toLocaleDateString("id-ID", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Sumber angka</dt>
              <dd className="text-[var(--foreground)]">API GemaHutan saat halaman dibuka</dd>
            </div>
          </dl>
        </header>

        <section className="mt-6">
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">1. Ringkasan</h2>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Rekaman", nilai: angka(ringkas.recordings), ket: "Rekaman yang tersimpan di basis data" },
              { label: "Deteksi", nilai: angka(ringkas.detections), ket: "Semua deteksi dari semua mesin" },
              { label: "Spesies terdeteksi", nilai: angka(ringkas.species_detected), ket: "Spesies yang punya minimal satu deteksi" },
              { label: "Lokasi pemantauan", nilai: angka(ringkas.sites), ket: "Titik perekaman terdaftar" },
            ].map((k) => (
              <div key={k.label} className="rounded border border-[var(--border)] bg-[var(--background)] p-4">
                <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">{k.label}</dt>
                <dd className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{k.nilai}</dd>
                <dd className="mt-1 text-xs text-[var(--muted-foreground)]">{k.ket}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-sm text-[var(--muted-foreground)]">
            Basis data memuat {angka(daftarSpesies.length)} baris spesies, {angka(spesiesModel)}
            di antaranya dikenal dikenali model lokal. Sisanya bisa muncul dari jalur deteksi global dan
            tidak punya ambang lokal.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">2. Sebaran lokasi</h2>
          {daftarLokasi.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">Belum ada lokasi terdaftar.</p>
          ) : (
            <div className="overflow-x-auto rounded border border-[var(--border)]">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-[var(--muted)]">
                  <tr>
                    {["Lokasi", "Habitat", "Rekaman", "Deteksi", "Spesies", "Koordinat"].map((k) => (
                      <th
                        key={k}
                        scope="col"
                        className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]"
                      >
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {daftarLokasi.map((s) => (
                    <tr key={s.id} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2 text-[var(--foreground)]">{s.name}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">
                        {s.habitat_type ? String(s.habitat_type).replace(/_/g, " ") : "-"}
                      </td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{angka(s.recordings_count)}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{angka(s.detections_count)}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{angka(s.species_count)}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">
                        {s.latitude != null && s.longitude != null
                          ? `${Number(s.latitude).toFixed(4)}, ${Number(s.longitude).toFixed(4)}`
                          : "belum ada"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">
            3. Spesies, ambang, dan jumlah deteksi
          </h2>
          <p className="mb-3 text-sm text-[var(--muted-foreground)]">
            Ambang adalah skor minimum supaya satu kandidat dilaporkan sebagai deteksi. Angka
            ditampilkan dari basis data, yang isinya disalin dari laporan kalibrasi.
          </p>
          {spesiesTerurut.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">Belum ada baris spesies.</p>
          ) : (
            <div className="overflow-x-auto rounded border border-[var(--border)]">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-[var(--muted)]">
                  <tr>
                    {["Nama ilmiah", "Nama Indonesia", "Status IUCN", "Ambang lokal", "Deteksi", "Di data latih lokal"].map((k) => (
                      <th
                        key={k}
                        scope="col"
                        className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]"
                      >
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {spesiesTerurut.map((s) => (
                    <tr key={s.id} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2 italic text-[var(--foreground)]">{s.scientific_name}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{s.common_name_id || "-"}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{s.iucn_status || "-"}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{ambangTeks(s.default_threshold)}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">{angka(s.detection_count)}</td>
                      <td className="px-3 py-2 text-[var(--foreground)]">
                        {namaAmbangLokal.has(String(s.scientific_name)) ? "ya" : "tidak"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">4. Catatan metode</h2>
          <ol className="list-decimal space-y-2 pl-5 text-sm text-[var(--muted-foreground)]">
            <li>
              Audio diubah menjadi satu kanal 48 kHz, lalu dipotong per tiga detik untuk analisis.
            </li>
            <li>
              Dua jalur deteksi dipakai bersama. Jalur global menandai kandidat dengan cakupan
              spesies luas, jalur lokal memberi skor untuk spesies Indonesia yang ada di data latih
              model.
            </li>
            <li>
              Kandidat dilaporkan sebagai deteksi kalau skornya melewati ambang spesies tersebut.
              Ambang rendah melaporkan lebih banyak, ambang tinggi menahan lebih banyak.
            </li>
            <li>
              Setiap deteksi menyimpan mesin dan versinya, supaya hasil dari dua jalur bisa dibedakan
              di kemudian hari.
            </li>
            <li>
              Ahli bisa menandai deteksi benar, salah, atau ragu. Hasil verifikasi jadi bahan latih
              ulang dan tersedia lewat ekspor.
            </li>
            <li>
              Indeks soundscape ACI, NDSI, ADI, dan BI dihitung per rekaman sebagai gambaran
              keragaman akustik, bukan pengganti deteksi spesies.
            </li>
            <li>
              Angka di laporan ini dihitung dari basis data pada saat halaman dibuka. Rentang tanggal
              diambil dari hari rekaman terawal dan terakhir yang tercatat.
            </li>
          </ol>
        </section>

        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">5. Batas yang harus dibaca</h2>
          {batas.length > 0 ? (
            <ul className="list-disc space-y-2 pl-5 text-sm text-[var(--muted-foreground)]">
              {batas.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          ) : (
            <ul className="list-disc space-y-2 pl-5 text-sm text-[var(--muted-foreground)]">
              <li>
                Angka evaluasi lapangan belum tersedia untuk halaman ini, jadi tidak ada yang
                ditampilkan. Halaman ini tidak menulis angka dari ingatan: kalau laporan evaluasi
                belum ada di image, bagian ini kosong.
              </li>
              <li>
                Batas yang selalu berlaku: angka audio bersih berasal dari klip Xeno-canto tanpa
                gangguan lapangan, jadi itu batas atas, bukan perkiraan lapangan.
              </li>
              <li>
                Skenario hujan, angin, kota, dan jarak adalah simulasi, bukan rekaman lapangan.
              </li>
            </ul>
          )}
        </section>

        <footer className="mt-8 border-t border-[var(--border)] pt-4 text-xs text-[var(--muted-foreground)]">
          Sumber angka: /api/v1/stats/overview, /api/v1/stats/timeline, /api/v1/species,
          /api/v1/sites, dan /api/v1/model/info. Laporan ini dibuat otomatis saat halaman dibuka,
          jadi angka selalu sama dengan isi basis data saat itu.
        </footer>
      </article>
    </div>
  );
}
