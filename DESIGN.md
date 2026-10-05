# DESIGN.md. Arah tampilan GemaHutan

Berlaku sejak 3 Oktober 2026 dan menggantikan arah lama (dashboard gelap biru `#0033FF`,
tombol `#0095FF`). Halaman depan dan `/dokumentasi` sudah memakai arah ini. Aplikasi petugas
(`apps/web/src/app/(app)/`) masih bergaya lama dan wajib dipindah ke tema yang sama saat dibuka.

Pengguna: admin kawasan, peneliti, ranger (lihat `docs/VISI_DAN_RUANG_LINGKUP.md`). Layar dipakai
di kantor balai dan di HP di lapangan, sering di bawah matahari. Karena itu temanya terang dan
kontrasnya tinggi.

## Dasar

- Tailwind 4 lewat `@tailwindcss/postcss`, daisyUI 5, tema `gemahutan` di
  `apps/web/src/app/globals.css`. Satu tema terang, tanpa mode gelap dan tanpa toggle.
- Pakai komponen daisyUI (`btn`, `card`, `table`, `badge`, `alert`, `navbar`, `menu`, `modal`,
  `tabs`, `input`, `select`) sebelum membuat komponen sendiri.
- `className` ditulis sebagai string utuh, bukan disusun dari potongan, supaya Tailwind
  menemukannya saat build.
- Ikon: lucide-react. Ikon dipilih per makna (suara, lokasi, burung), tanpa sparkle.
- Font: Plus Jakarta Sans lewat `next/font` (variabel `--font-jakarta`). Judul tidak memakai
  berat di atas 700.

## Palet tema `gemahutan`

| Token daisyUI | Nilai | Fungsi | Kontras |
|---|---|---|---|
| `base-100` | #FFFFFF | latar utama | - |
| `base-200` | #F4F7F5 | latar seksi, panel | - |
| `base-300` | #E3E8E4 | garis, batas | dekoratif |
| `base-content` | #111111 | teks utama | 18,9:1 di putih |
| `primary` | #00873F | isi tombol utama | teks putih 4,6:1 |
| `secondary` | #E5F6EC | lencana, sorotan lembut | teks #00602D 6,9:1 |
| `accent` | #00AA5B | grafik, ilustrasi | bukan untuk teks di putih (3,0:1) |
| `neutral` | #14261C | panel gelap, kaki halaman | - |
| `info` | #0067B8 | info | - |
| `warning` | #9A5B00 | peringatan | teks putih 5,4:1 |
| `error` | #B42318 | error | teks putih 6,6:1 |

Teks, link, dan ikon hijau di atas putih memakai `#007A3D` (5,5:1), lewat `--primary-text`
atau kelas `text-primary` yang sudah diarahkan ke token itu. `#00873F` hanya untuk bidang
terisi. Fokus keyboard memakai `--ring` (#007A3D).

## Aturan

- Angka yang tampil berasal dari data nyata: hasil model, indeks soundscape, isian pengguna.
  Tidak ada metrik hiasan.
- Skor model ditulis sebagai skor, bukan "akurasi" atau "pasti".
- Lokasi spesies prioritas disamarkan untuk peran selain admin dan peneliti. Tampilan yang
  menunjukkan titik lokasi wajib memeriksa peran.
- Spektrogram memakai colormap magma. Itu visualisasi data, bukan warna merek.
- Tanpa emoji di UI, tanpa testimoni, tanpa logo mitra yang belum ada, tanpa foto orang.
- Gerak: transisi dan hover saja di aplikasi petugas. Video Remotion hanya di halaman depan,
  dan berhenti di bingkai akhir kalau pengguna memilih kurangi gerak.
- Tata letak HP: tombol aksi minimal 44 px tinggi, tabel lebar diganti daftar kartu di bawah
  `sm`, tanpa gulir horizontal halaman.

## Komponen bersama

- `apps/web/src/components/situs.tsx`: `KepalaSitus` (navbar mengambang) dan `KakiSitus`
  untuk halaman publik.
- `apps/web/src/remotion/`: video cara kerja di halaman depan.

## Alur kerja UI

Perubahan tampilan dibuat lewat MCP daisyUI Blueprint (setup, rules, lalu creative director dan
page architect untuk halaman baru, lalu quality inspector), dan teks melewati skill antislop.
