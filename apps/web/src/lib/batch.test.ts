import { describe, expect, it } from "vitest";

import {
  MAKS_BERKAS_BATCH,
  alasanTolak,
  batchSelesai,
  ekstensiBerkas,
  kalimatRingkasan,
  ringkasBatch,
  saringBerkasAudio,
} from "./batch";

describe("ekstensiBerkas", () => {
  it("mengambil ekstensi huruf kecil", () => {
    expect(ekstensiBerkas("Rekaman.WAV")).toBe("wav");
    expect(ekstensiBerkas("a.b.webm")).toBe("webm");
  });

  it("mengembalikan teks kosong kalau tidak ada ekstensi", () => {
    expect(ekstensiBerkas("tanpa-ekstensi")).toBe("");
    expect(ekstensiBerkas("berakhir.")).toBe("");
    expect(ekstensiBerkas("")).toBe("");
  });
});

describe("alasanTolak", () => {
  it("menerima berkas audio yang didukung API termasuk hasil rekaman peramban", () => {
    expect(alasanTolak({ name: "hutan.wav", type: "audio/wav" })).toBeNull();
    expect(alasanTolak({ name: "hp.m4a", type: "audio/mp4" })).toBeNull();
    expect(alasanTolak({ name: "browser-1.webm", type: "audio/webm" })).toBeNull();
    expect(alasanTolak({ name: "tanpa-tipe.mp3", type: "" })).toBeNull();
  });

  it("menolak ekstensi yang tidak dipakai API", () => {
    expect(alasanTolak({ name: "catatan.pdf", type: "application/pdf" })).toContain(".pdf");
    expect(alasanTolak({ name: "video.mp4", type: "audio/mp4" })).toContain(".mp4");
  });

  it("menolak berkas tanpa ekstensi dan tipe bukan audio", () => {
    expect(alasanTolak({ name: "tanpa-ekstensi", type: "" })).toContain("ekstensi");
    expect(alasanTolak({ name: "suara.wav", type: "text/plain" })).toContain("bukan audio");
  });
});

describe("saringBerkasAudio", () => {
  it("memisahkan berkas yang diterima dari yang ditolak", () => {
    const hasil = saringBerkasAudio([
      { name: "a.wav", type: "audio/wav" },
      { name: "b.pdf", type: "application/pdf" },
      { name: "c.mp3", type: "audio/mpeg" },
    ]);
    expect(hasil.diterima.map((f) => f.name)).toEqual(["a.wav", "c.mp3"]);
    expect(hasil.ditolak).toHaveLength(1);
    expect(hasil.ditolak[0].nama).toBe("b.pdf");
    expect(hasil.dipotong).toBe(0);
  });

  it("memotong kelebihan di atas batas maksimal tanpa menolaknya", () => {
    const berkas = Array.from({ length: MAKS_BERKAS_BATCH + 3 }, (_, i) => ({
      name: `berkas-${i}.wav`,
      type: "audio/wav",
    }));
    const hasil = saringBerkasAudio(berkas);
    expect(hasil.diterima).toHaveLength(MAKS_BERKAS_BATCH);
    expect(hasil.ditolak).toHaveLength(0);
    expect(hasil.dipotong).toBe(3);
  });

  it("aman untuk masukan kosong", () => {
    const hasil = saringBerkasAudio([]);
    expect(hasil.diterima).toEqual([]);
    expect(hasil.dipotong).toBe(0);
  });
});

describe("ringkasBatch", () => {
  it("menghitung selesai, gagal, diproses, dan menunggu", () => {
    const ringkasan = ringkasBatch([
      { status: "done" },
      { status: "done" },
      { status: "failed" },
      { status: "processing" },
      { status: "pending" },
    ]);
    expect(ringkasan).toEqual({
      total: 5,
      selesai: 2,
      gagal: 1,
      diproses: 1,
      menunggu: 1,
    });
  });

  it("menghitung status tak dikenal sebagai menunggu supaya total tetap cocok", () => {
    const ringkasan = ringkasBatch([{ status: null }, { status: "kustom" }]);
    expect(ringkasan.total).toBe(2);
    expect(ringkasan.menunggu).toBe(2);
  });

  it("aman untuk nilai kosong", () => {
    expect(ringkasBatch(null).total).toBe(0);
    expect(ringkasBatch(undefined).total).toBe(0);
  });
});

describe("batchSelesai", () => {
  it("benar kalau semua berkas sudah selesai atau gagal", () => {
    expect(batchSelesai([{ status: "done" }, { status: "failed" }])).toBe(true);
  });

  it("salah selama masih ada yang diproses atau menunggu", () => {
    expect(batchSelesai([{ status: "done" }, { status: "processing" }])).toBe(false);
    expect(batchSelesai([{ status: "pending" }])).toBe(false);
  });

  it("salah untuk batch kosong", () => {
    expect(batchSelesai([])).toBe(false);
  });
});

describe("kalimatRingkasan", () => {
  it("menyebut jumlah selesai dan gagal", () => {
    const kalimat = kalimatRingkasan(ringkasBatch([{ status: "done" }, { status: "failed" }]));
    expect(kalimat).toContain("2 berkas");
    expect(kalimat).toContain("1 selesai");
    expect(kalimat).toContain("1 gagal");
  });

  it("menyebut antrean yang belum jalan", () => {
    const kalimat = kalimatRingkasan(ringkasBatch([{ status: "pending" }]));
    expect(kalimat).toContain("menunggu antrean");
  });

  it("menyebut batch kosong apa adanya", () => {
    expect(kalimatRingkasan(ringkasBatch([]))).toBe("Belum ada berkas pada batch ini.");
  });
});
