/**
 * Ubah galat dari API, jaringan, atau XHR unggah menjadi satu kalimat Indonesia.
 *
 * API kadang mengirim `detail` berupa teks, kadang berupa daftar validasi, dan
 * unggahan XHR menolak dengan teks JSON mentah. Semua bentuk itu berakhir di sini
 * supaya layar tidak pernah menampilkan "[object Object]" atau JSON.
 */
export function pesanGalat(err: unknown, cadangan = "Terjadi kesalahan. Coba lagi."): string {
  const teks = err instanceof Error ? err.message : typeof err === "string" ? err : "";
  if (!teks) return cadangan;

  if (/failed to fetch|networkerror|load failed|upload failed/i.test(teks)) {
    return "Tidak bisa menghubungi server analisis. Pastikan aplikasi menyala, lalu coba lagi.";
  }

  let detail: unknown = teks;
  const awal = teks.trim();
  if (awal.startsWith("{") || awal.startsWith("[")) {
    try {
      const data = JSON.parse(awal);
      detail = data?.detail ?? data;
    } catch {
      detail = teks;
    }
  }

  if (Array.isArray(detail)) {
    const pertama = detail.find((d) => d && typeof d === "object" && "msg" in d) as
      | { msg?: string }
      | undefined;
    return bersihkan(pertama?.msg) || cadangan;
  }
  if (typeof detail === "string") {
    const kode = detail.match(/Request failed: (\d{3})/);
    if (kode) return pesanKode(Number(kode[1])) || cadangan;
    return bersihkan(detail) || cadangan;
  }
  return cadangan;
}

function bersihkan(pesan?: string): string {
  if (!pesan) return "";
  return pesan.replace(/^Value error,\s*/i, "").trim();
}

function pesanKode(kode: number): string {
  if (kode === 413) return "Berkas terlalu besar. Maksimal 200 MB.";
  if (kode === 415) return "Berkas ini bukan audio yang bisa dibaca. Coba MP3, WAV, M4A, atau FLAC.";
  if (kode === 401 || kode === 403) return "Sesi berakhir. Muat ulang halaman.";
  if (kode >= 500) return "Server analisis sedang bermasalah. Coba lagi sebentar lagi.";
  return "";
}
