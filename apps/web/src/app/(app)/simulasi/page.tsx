"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Feature, LineString, Polygon } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";

import { api } from "@/lib/api";
import type { SimulasiLokasiResponse } from "@/lib/api";

/*
 * Simulasi perkiraan lokasi (Tahap 3, blok K). Ini simulasi: tidak menulis data
 * lapangan, hanya menunjukkan cara beberapa alat yang mendengar suara yang sama
 * bisa memperkirakan area asal suara. Peta memakai ubin OpenStreetMap, dan
 * koordinat alat/sumber dinyatakan dalam meter di sekitar satu titik acuan.
 */

// Titik acuan: kawasan hutan di Jawa Barat. Semua posisi simulasi adalah
// selisih meter dari titik ini, supaya bisa digambar di peta geografis.
const ANCHOR_LAT = -6.7875;
const ANCHOR_LON = 106.9839;
const M_PER_DEG_LAT = 111320;
const M_PER_DEG_LON = 111320 * Math.cos((ANCHOR_LAT * Math.PI) / 180);

type Titik = { x: number; y: number };

function meterKeLngLat(x: number, y: number): [number, number] {
  return [ANCHOR_LON + x / M_PER_DEG_LON, ANCHOR_LAT + y / M_PER_DEG_LAT];
}

function lngLatKeMeter(lng: number, lat: number): Titik {
  return {
    x: (lng - ANCHOR_LON) * M_PER_DEG_LON,
    y: (lat - ANCHOR_LAT) * M_PER_DEG_LAT,
  };
}

function lingkaran(cx: number, cy: number, radius: number): [number, number][] {
  const pts: [number, number][] = [];
  const n = 64;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * 2 * Math.PI;
    pts.push(meterKeLngLat(cx + radius * Math.cos(a), cy + radius * Math.sin(a)));
  }
  pts.push(pts[0]);
  return pts;
}

function formatMeter(n: number | null | undefined): string {
  if (n == null) return "-";
  return `${Math.round(n)} m`;
}

export default function SimulasiPage() {
  const [alat, setAlat] = useState<Titik[]>([]);
  const [sumber, setSumber] = useState<Titik | null>(null);
  const [mode, setMode] = useState<"alat" | "sumber">("alat");
  const [snr, setSnr] = useState(20);
  const [sinkron, setSinkron] = useState(true);
  const [hasil, setHasil] = useState<SimulasiLokasiResponse | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [sibuk, setSibuk] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const layerRef = useRef<maplibregl.Marker[]>([]);
  const tileError = useRef(false);

  // Handler klik membaca nilai mode dan alat lewat ref supaya handler yang
  // dipasang sekali di bawah tidak memakai nilai state lama.
  const modeRef = useRef(mode);
  const alatRef = useRef(alat);
  modeRef.current = mode;
  alatRef.current = alat;

  useEffect(() => {
    if (!containerRef.current) return;
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [ANCHOR_LON, ANCHOR_LAT],
      zoom: 15,
      attributionControl: { compact: true },
    });
    instance.addControl(new maplibregl.NavigationControl(), "top-right");
    instance.on("error", () => {
      tileError.current = true;
    });
    instance.on("click", (e) => {
      const t = lngLatKeMeter(e.lngLat.lng, e.lngLat.lat);
      if (modeRef.current === "alat") {
        if (alatRef.current.length >= 4) return;
        setAlat((lama) => [...lama, { x: Math.round(t.x), y: Math.round(t.y) }]);
      } else {
        setSumber({ x: Math.round(t.x), y: Math.round(t.y) });
      }
    });
    mapRef.current = instance;
    return () => {
      instance.remove();
      mapRef.current = null;
    };
  }, []);

  const bersihkanLayer = useCallback(() => {
    for (const m of layerRef.current) m.remove();
    layerRef.current = [];
    const map = mapRef.current;
    if (!map) return;
    for (const id of ["arah-garis", "area-isi", "area-garis", "area"]) {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    }
  }, []);

  const gambar = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    bersihkanLayer();

    for (const [i, a] of alat.entries()) {
      const el = document.createElement("div");
      el.style.width = "14px";
      el.style.height = "14px";
      el.style.background = "#00602D";
      el.style.border = "2px solid #FFFFFF";
      el.style.borderRadius = "2px";
      el.style.boxShadow = "0 1px 2px rgba(0,0,0,0.4)";
      el.setAttribute("aria-label", `Alat ${i + 1}`);
      const m = new maplibregl.Marker({ element: el })
        .setLngLat(meterKeLngLat(a.x, a.y))
        .addTo(map);
      layerRef.current.push(m);
    }

    if (sumber) {
      const el = document.createElement("div");
      el.style.width = "18px";
      el.style.height = "18px";
      el.style.background = "#B45309";
      el.style.border = "2px solid #FFFFFF";
      el.style.borderRadius = "50%";
      el.setAttribute("aria-label", "Sumber suara");
      const m = new maplibregl.Marker({ element: el })
        .setLngLat(meterKeLngLat(sumber.x, sumber.y))
        .addTo(map);
      layerRef.current.push(m);
    }

    if (hasil) {
      const garis: Feature<LineString>[] = [];
      for (const a of hasil.arah) {
        if (a.azimuth_deg == null) continue;
        const az = ((a.azimuth_deg % 360) + 360) % 360;
        const rad = (az * Math.PI) / 180;
        const ujung: [number, number] = meterKeLngLat(
          a.x + 90 * Math.cos(rad),
          a.y + 90 * Math.sin(rad),
        );
        garis.push({
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [meterKeLngLat(a.x, a.y), ujung],
          },
        });
      }
      if (garis.length > 0) {
        map.addSource("arah-garis", {
          type: "geojson",
          data: { type: "FeatureCollection", features: garis },
        });
        map.addLayer({
          id: "arah-garis",
          type: "line",
          source: "arah-garis",
          paint: { "line-color": "#007A3D", "line-width": 2 },
        });
      }

      if (hasil.perkiraan && hasil.radius_area_m != null) {
        const [cx, cy] = hasil.perkiraan;
        const pol: Feature<Polygon> = {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [lingkaran(cx, cy, hasil.radius_area_m)],
          },
        };
        map.addSource("area", { type: "geojson", data: pol });
        map.addLayer({ id: "area-isi", type: "fill", source: "area", paint: { "fill-color": "#007A3D", "fill-opacity": 0.12 } });
        map.addLayer({ id: "area-garis", type: "line", source: "area", paint: { "line-color": "#007A3D", "line-width": 1.5, "line-dasharray": [2, 2] } });

        const el = document.createElement("div");
        el.style.width = "12px";
        el.style.height = "12px";
        el.style.background = "#111111";
        el.style.borderRadius = "50%";
        el.setAttribute("aria-label", "Titik perkiraan");
        const m = new maplibregl.Marker({ element: el })
          .setLngLat(meterKeLngLat(cx, cy))
          .addTo(map);
        layerRef.current.push(m);
      }
    }
  }, [alat, sumber, hasil, bersihkanLayer]);

  useEffect(() => {
    gambar();
  }, [gambar]);

  const hitung = useCallback(async () => {
    if (alat.length < 2 || !sumber) return;
    setSibuk(true);
    setGalat(null);
    setHasil(null);
    try {
      const data = await api.simulasiLokasi({
        alat: alat.map((a) => ({ x: a.x, y: a.y, jenis: "larik" })),
        sumber: [sumber.x, sumber.y],
        snr_db: snr,
        benih: 0,
        sinkron,
      });
      setHasil(data);
    } catch (err) {
      setGalat((err as Error)?.message || "Simulasi gagal. Coba lagi.");
    } finally {
      setSibuk(false);
    }
  }, [alat, sumber, snr, sinkron]);

  const bisa = alat.length >= 2 && sumber != null && !sibuk;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Simulasi perkiraan lokasi</h1>
        <p className="mt-1 max-w-2xl text-sm text-base-content/70">
          Letakkan 2 sampai 4 alat virtual dan satu titik sumber suara di peta. GemaHutan menghitung
          arah yang didengar tiap alat lalu menggabungkannya menjadi area perkiraan. Ini simulasi,
          bukan data lapangan.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="flex overflow-hidden rounded border border-base-300">
              <button
                type="button"
                onClick={() => setMode("alat")}
                className={`px-3 py-2 text-sm ${mode === "alat" ? "bg-primary text-primary-content" : "bg-base-100"}`}
              >
                Tambah alat ({alat.length}/4)
              </button>
              <button
                type="button"
                onClick={() => setMode("sumber")}
                className={`px-3 py-2 text-sm ${mode === "sumber" ? "bg-primary text-primary-content" : "bg-base-100"}`}
              >
                Tentukan sumber
              </button>
            </div>
            <button type="button" onClick={() => { setAlat([]); setSumber(null); setHasil(null); }} className="btn btn-sm btn-ghost">
              Bersihkan
            </button>
          </div>

          <div
            ref={containerRef}
            className="h-[420px] w-full rounded border border-base-300 bg-base-200"
            style={{ minHeight: "420px" }}
          />

          <div className="mt-3 flex flex-wrap gap-4 text-xs text-base-content/70">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-xs bg-[#00602D]" aria-hidden="true" /> Alat
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-full bg-[#B45309]" aria-hidden="true" /> Sumber
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 border border-dashed border-[#007A3D]" aria-hidden="true" /> Area perkiraan
            </span>
          </div>
        </div>

        <div className="grid content-start gap-4">
          <div className="rounded border border-base-300 bg-base-100 p-4">
            <h2 className="mb-3 text-sm font-semibold">Pengaturan</h2>
            <label className="mb-2 block text-xs text-base-content/70">
              Derau (SNR): {snr} dB
              <input
                type="range"
                min={0}
                max={40}
                step={5}
                value={snr}
                onChange={(e) => setSnr(Number(e.target.value))}
                className="mt-1 w-full"
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={sinkron} onChange={(e) => setSinkron(e.target.checked)} />
              Jam alat tersinkron
            </label>
            <button
              type="button"
              onClick={hitung}
              disabled={!bisa}
              className="btn btn-primary mt-4 w-full"
            >
              {sibuk ? "Menghitung..." : "Hitung perkiraan"}
            </button>
            {alat.length < 2 && <p className="mt-2 text-xs text-base-content/70">Butuh minimal 2 alat.</p>}
            {alat.length >= 2 && !sumber && <p className="mt-2 text-xs text-base-content/70">Tentukan sumber suara dulu.</p>}
          </div>

          <div className="rounded border border-base-300 bg-base-100 p-4">
            <h2 className="mb-2 text-sm font-semibold">Alat</h2>
            {alat.length === 0 ? (
              <p className="text-xs text-base-content/70">Belum ada alat. Klik peta untuk menambah.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {alat.map((a, i) => (
                  <li key={i} className="flex items-center justify-between">
                    <span className="tabular-nums">Alat {i + 1}: ({a.x}, {a.y}) m</span>
                    <button
                      type="button"
                      onClick={() => { setAlat((lama) => lama.filter((_, k) => k !== i)); setHasil(null); }}
                      className="btn btn-xs btn-ghost"
                    >
                      Hapus
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-base-content/70">
              Sumber: {sumber ? `(${sumber.x}, ${sumber.y}) m` : "belum ditentukan"}
            </p>
          </div>

          {galat && (
            <div role="alert" className="rounded border border-[var(--destructive)] bg-[var(--destructive-surface)] p-3 text-sm">
              {galat}
            </div>
          )}

          {hasil && (
            <div className="rounded border border-base-300 bg-base-100 p-4">
              <h2 className="mb-2 text-sm font-semibold">Hasil</h2>
              {hasil.perkiraan ? (
                <>
                  <p className="text-sm">
                    Perkiraan titik: ({hasil.perkiraan[0]}, {hasil.perkiraan[1]}) m
                  </p>
                  <p className="text-sm">
                    Area perkiraan: jari-jari {formatMeter(hasil.radius_area_m)}
                  </p>
                  <p className="text-sm">
                    Selisih ke sumber sebenarnya: {formatMeter(hasil.galat_m)}
                  </p>
                </>
              ) : (
                <p className="text-sm text-base-content/70">{hasil.catatan}</p>
              )}
              <p className="mt-2 text-xs text-base-content/70">{hasil.catatan}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
