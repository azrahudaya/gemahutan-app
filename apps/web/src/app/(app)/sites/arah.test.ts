import { describe, expect, it } from "vitest";

import {
  alasanTanpaArah,
  arahMataAngin,
  labelArah,
  labelJangkauan,
  lingkaranJangkauan,
  petakanLokalisasi,
  punyaLokalisasi,
} from "./arah";

describe("arahMataAngin", () => {
  it("mengubah sudut utama jadi delapan mata angin", () => {
    expect(arahMataAngin(0)).toBe("utara");
    expect(arahMataAngin(45)).toBe("timur laut");
    expect(arahMataAngin(90)).toBe("timur");
    expect(arahMataAngin(135)).toBe("tenggara");
    expect(arahMataAngin(180)).toBe("selatan");
    expect(arahMataAngin(225)).toBe("barat daya");
    expect(arahMataAngin(270)).toBe("barat");
    expect(arahMataAngin(315)).toBe("barat laut");
  });

  it("membungkus sudut di luar 0 sampai 360", () => {
    expect(arahMataAngin(360)).toBe("utara");
    expect(arahMataAngin(359)).toBe("utara");
    expect(arahMataAngin(-90)).toBe("barat");
  });
});

describe("labelArah", () => {
  it("memakai tanda hubung kalau arah belum ada", () => {
    expect(labelArah(null)).toBeNull();
    expect(labelArah(undefined)).toBeNull();
    expect(labelArah(Number.NaN)).toBeNull();
  });

  it("menulis derajat dan mata angin", () => {
    expect(labelArah(90)).toBe("90.0 derajat, timur");
    expect(labelArah(44.94)).toBe("44.9 derajat, timur laut");
  });
});

describe("labelJangkauan", () => {
  it("memakai tanda hubung kalau jangkauan belum ada atau nol", () => {
    expect(labelJangkauan(null)).toBeNull();
    expect(labelJangkauan(undefined)).toBeNull();
    expect(labelJangkauan(0)).toBeNull();
  });

  it("memakai meter di bawah satu kilometer dan kilometer di atasnya", () => {
    expect(labelJangkauan(25)).toBe("25 m");
    expect(labelJangkauan(999)).toBe("999 m");
    expect(labelJangkauan(1500)).toBe("1.50 km");
  });
});

describe("lingkaranJangkauan", () => {
  it("menutup cincin pada titik awal", () => {
    const ring = lingkaranJangkauan(-6.7394, 106.5497, 25, 16);
    expect(ring).toHaveLength(17);
    expect(ring[0]).toEqual(ring[16]);
  });

  it("memperlebar radius saat jaraknya ditambah", () => {
    const kecil = lingkaranJangkauan(0, 0, 100);
    const besar = lingkaranJangkauan(0, 0, 1000);
    const lebar = (ring: [number, number][]) =>
      Math.max(...ring.map((p) => p[0])) - Math.min(...ring.map((p) => p[0]));
    expect(lebar(besar)).toBeGreaterThan(lebar(kecil));
  });

  it("melebar lebih banyak di garis lintang tinggi", () => {
    // Satu derajat bujur lebih pendek di lintang tinggi, jadi radius meter yang
    // sama butuh rentang bujur yang lebih lebar supaya lingkarannya bulat.
    const katulistiwa = lingkaranJangkauan(0, 0, 500);
    const lintangTinggi = lingkaranJangkauan(60, 0, 500);
    const lebar = (ring: [number, number][]) =>
      Math.max(...ring.map((p) => p[0])) - Math.min(...ring.map((p) => p[0]));
    expect(lebar(lintangTinggi)).toBeGreaterThan(lebar(katulistiwa) * 1.5);
  });
});

describe("alasanTanpaArah", () => {
  it("menyebut syarat kanal saat API melaporkannya", () => {
    expect(alasanTanpaArah(2)).toMatch(/minimal 2 kanal/);
  });

  it("menjelaskan belum ada data saat kanal minimal tidak diketahui", () => {
    expect(alasanTanpaArah(null)).toMatch(/tidak ditebak/);
  });
});

describe("punyaLokalisasi", () => {
  it("menolak deteksi tanpa arah dan tanpa jangkauan", () => {
    expect(punyaLokalisasi({})).toBe(false);
    expect(punyaLokalisasi({ azimuth_deg: null, range_m: null })).toBe(false);
  });

  it("menerima deteksi yang hanya punya salah satu", () => {
    expect(punyaLokalisasi({ azimuth_deg: 45 })).toBe(true);
    expect(punyaLokalisasi({ range_m: 25 })).toBe(true);
  });

  it("menganggap nol derajat sebagai arah yang sah", () => {
    // 0 derajat adalah utara, bukan nilai kosong. Ini yang mudah salah.
    expect(punyaLokalisasi({ azimuth_deg: 0 })).toBe(true);
    expect(punyaLokalisasi({ range_m: 0 })).toBe(true);
  });
});

describe("petakanLokalisasi", () => {
  const titik = { recordingId: 7, lat: -6.75, lon: 106.55, detail: "Taman Uji" };

  it("melewati deteksi yang kolom lokalisasinya kosong", () => {
    const hasil = petakanLokalisasi(titik, [
      { id: 1, species_common: "Kutilang" },
      { id: 2, species_common: "Cipoh Kacat", azimuth_deg: null, range_m: null },
    ]);
    expect(hasil).toHaveLength(0);
  });

  it("membawa arah, jangkauan, dan keterangan mesin", () => {
    const hasil = petakanLokalisasi(titik, [
      {
        id: 3,
        species_common: "Kutilang",
        azimuth_deg: 123.4,
        range_m: 18,
        localization_engine: "gcc-phat",
      },
    ]);
    expect(hasil).toHaveLength(1);
    expect(hasil[0]).toMatchObject({
      key: "7-3",
      lat: -6.75,
      lon: 106.55,
      azimuth_deg: 123.4,
      range_m: 18,
      label: "Kutilang",
    });
    expect(hasil[0].detail).toContain("Taman Uji");
    expect(hasil[0].detail).toContain("rekaman #7");
    expect(hasil[0].detail).toContain("mesin gcc-phat");
  });

  it("memakai nama ilmiah kalau nama Indonesia tidak ada", () => {
    const hasil = petakanLokalisasi(titik, [{ id: 4, species_name: "Pycnonotus aurigaster", range_m: 30 }]);
    expect(hasil[0].label).toBe("Pycnonotus aurigaster");
    expect(hasil[0].azimuth_deg).toBeNull();
  });
});
