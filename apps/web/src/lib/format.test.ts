import { describe, expect, it } from "vitest";

import {
  formatArahMataAngin,
  formatDerajat,
  formatDurasi,
  formatJarak,
  formatKeyakinan,
  formatTanggal,
  indeksTahap,
  labelStatus,
  labelTahap,
  normalisasiProgres,
} from "./format";

describe("formatTanggal", () => {
  it("memakai tanda hubung untuk nilai kosong dan tanggal rusak", () => {
    expect(formatTanggal(null)).toBe("-");
    expect(formatTanggal(undefined)).toBe("-");
    expect(formatTanggal("bukan tanggal")).toBe("-");
  });

  it("mengubah tanggal ISO jadi tanggal Indonesia", () => {
    expect(formatTanggal("2026-09-21T03:06:52+00:00")).toMatch(/2026/);
  });
});

describe("formatDurasi", () => {
  it("memakai tanda hubung kalau durasi belum ada", () => {
    expect(formatDurasi(null)).toBe("-");
    expect(formatDurasi(undefined)).toBe("-");
  });

  it("menampilkan detik untuk rekaman pendek", () => {
    expect(formatDurasi(16.114)).toBe("16 detik");
    expect(formatDurasi(59.4)).toBe("59 detik");
  });

  it("memecah menit untuk rekaman panjang", () => {
    expect(formatDurasi(125)).toBe("2 menit 5 detik");
    expect(formatDurasi(60)).toBe("1 menit 0 detik");
  });
});

describe("formatKeyakinan", () => {
  it("memakai tanda hubung kalau nilai kosong", () => {
    expect(formatKeyakinan(null)).toBe("-");
  });

  it("menampilkan satu angka di belakang koma", () => {
    expect(formatKeyakinan(0.9719)).toBe("97.2%");
    expect(formatKeyakinan(0.1)).toBe("10.0%");
  });
});

describe("labelStatus", () => {
  it("menerjemahkan status pipeline", () => {
    expect(labelStatus("done")).toBe("Selesai");
    expect(labelStatus("processing")).toBe("Diproses");
    expect(labelStatus("pending")).toBe("Antre");
    expect(labelStatus("failed")).toBe("Gagal");
  });

  it("meneruskan status yang belum dikenal apa adanya", () => {
    expect(labelStatus("kustom")).toBe("kustom");
    expect(labelStatus(null)).toBe("-");
  });
});

describe("labelTahap", () => {
  it("menerjemahkan semua tahap yang dipakai worker", () => {
    expect(labelTahap("antre")).toBe("Menunggu antrean");
    expect(labelTahap("unduh")).toBe("Mengunduh berkas");
    expect(labelTahap("dekode")).toBe("Membaca audio");
    expect(labelTahap("birdnet")).toBe("Deteksi BirdNET");
    expect(labelTahap("klasifikasi")).toBe("Klasifikasi spesies");
    expect(labelTahap("lokalisasi")).toBe("Menghitung arah");
    expect(labelTahap("indeks")).toBe("Menghitung indeks");
    expect(labelTahap("spektrogram")).toBe("Membuat spektrogram");
    expect(labelTahap("selesai")).toBe("Selesai");
    expect(labelTahap("gagal")).toBe("Gagal");
  });

  it("menandai tahap yang belum ada tanpa mengarang nama", () => {
    expect(labelTahap(null)).toBe("Belum mulai");
    expect(labelTahap(undefined)).toBe("Belum mulai");
    expect(labelTahap("kustom")).toBe("kustom");
  });
});

describe("normalisasiProgres", () => {
  it("menjepit nilai ke rentang nol sampai seratus", () => {
    expect(normalisasiProgres(-5)).toBe(0);
    expect(normalisasiProgres(0)).toBe(0);
    expect(normalisasiProgres(41.6)).toBe(42);
    expect(normalisasiProgres(140)).toBe(100);
  });

  it("memakai nol kalau nilai belum ada", () => {
    expect(normalisasiProgres(null)).toBe(0);
    expect(normalisasiProgres(undefined)).toBe(0);
    expect(normalisasiProgres(Number.NaN)).toBe(0);
  });
});

describe("indeksTahap", () => {
  it("mengembalikan urutan tahap sesuai kontrak", () => {
    expect(indeksTahap("antre")).toBe(0);
    expect(indeksTahap("lokalisasi")).toBe(5);
    expect(indeksTahap("selesai")).toBe(8);
  });

  it("mengembalikan minus satu untuk tahap yang tidak dikenal", () => {
    expect(indeksTahap(null)).toBe(-1);
    expect(indeksTahap("kustom")).toBe(-1);
  });
});

describe("formatArahMataAngin", () => {
  it("memetakan azimuth utama ke delapan penjuru", () => {
    expect(formatArahMataAngin(0)).toBe("Utara");
    expect(formatArahMataAngin(45)).toBe("Timur Laut");
    expect(formatArahMataAngin(90)).toBe("Timur");
    expect(formatArahMataAngin(135)).toBe("Tenggara");
    expect(formatArahMataAngin(180)).toBe("Selatan");
    expect(formatArahMataAngin(225)).toBe("Barat Daya");
    expect(formatArahMataAngin(270)).toBe("Barat");
    expect(formatArahMataAngin(315)).toBe("Barat Laut");
  });

  it("membulatkan ke penjuru terdekat pada batas sektor", () => {
    expect(formatArahMataAngin(22)).toBe("Utara");
    expect(formatArahMataAngin(23)).toBe("Timur Laut");
    expect(formatArahMataAngin(337)).toBe("Barat Laut");
    expect(formatArahMataAngin(338)).toBe("Utara");
  });

  it("membungkus nilai di luar rentang nol sampai tiga ratus enam puluh", () => {
    expect(formatArahMataAngin(360)).toBe("Utara");
    expect(formatArahMataAngin(450)).toBe("Timur");
    expect(formatArahMataAngin(-90)).toBe("Barat");
  });

  it("tidak menampilkan Utara palsu kalau arah belum tersedia", () => {
    expect(formatArahMataAngin(null)).toBe("-");
    expect(formatArahMataAngin(undefined)).toBe("-");
    expect(formatArahMataAngin(Number.NaN)).toBe("-");
  });
});

describe("formatDerajat", () => {
  it("menampilkan satu angka di belakang koma dengan lambang derajat", () => {
    expect(formatDerajat(123.44)).toBe("123.4\u00B0");
    expect(formatDerajat(123.45)).toBe("123.5\u00B0");
    expect(formatDerajat(0)).toBe("0.0\u00B0");
  });

  it("memakai tanda hubung kalau nilai kosong", () => {
    expect(formatDerajat(null)).toBe("-");
    expect(formatDerajat(undefined)).toBe("-");
  });
});

describe("formatJarak", () => {
  it("memakai meter untuk jarak dekat dan kilometer untuk jarak jauh", () => {
    expect(formatJarak(12.4)).toBe("12 m");
    expect(formatJarak(999)).toBe("999 m");
    expect(formatJarak(1500)).toBe("1.5 km");
  });

  it("memakai tanda hubung kalau jangkauan belum tersedia", () => {
    expect(formatJarak(null)).toBe("-");
    expect(formatJarak(undefined)).toBe("-");
  });
});
