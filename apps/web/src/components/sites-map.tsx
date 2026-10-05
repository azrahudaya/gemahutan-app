"use client";

import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { FeatureCollection, Polygon } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";

import { labelArah, labelJangkauan, lingkaranJangkauan } from "@/app/(app)/sites/arah";

export interface MapSite {
  id: number;
  name: string;
  lat: number;
  lon: number;
  habitat_type?: string | null;
}

export interface MapLocalization {
  /** Kunci unik, biasanya id deteksi. */
  key: string;
  lat: number;
  lon: number;
  /** 0 = utara, bertambah searah jarum jam. Null kalau belum bisa dihitung. */
  azimuth_deg: number | null;
  range_m: number | null;
  /** Nama yang tampil di keterangan, misalnya nama spesies. */
  label: string;
  /** Baris kedua keterangan, misalnya lokasi dan tanggal. */
  detail?: string;
}

const WARNA_ARAH = "#007A3D";
const WARNA_JANGKAUAN = "#007A3D";

/**
 * Peta lokasi pemantauan.
 *
 * Selain titik lokasi, peta bisa menggambar dua hal dari data lokalisasi
 * deteksi: penanda sudut arah datang dan lingkaran perkiraan jangkauan.
 * Keduanya hanya digambar kalau nilainya benar-benar ada di data. Kalau null,
 * peta tidak mengarang posisi, dan halaman pemanggil menampilkan alasannya.
 */
export function SitesMap({
  sites,
  localizations = [],
  catatanArah,
}: {
  sites: MapSite[];
  localizations?: MapLocalization[];
  catatanArah?: string | null;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!mapContainer.current || sites.length === 0) return;

    const center: [number, number] = [
      sites.reduce((s, site) => s + site.lon, 0) / sites.length,
      sites.reduce((s, site) => s + site.lat, 0) / sites.length,
    ];

    const instance = new maplibregl.Map({
      container: mapContainer.current,
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
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center,
      zoom: sites.length === 1 ? 11 : 6,
      attributionControl: { compact: true },
    });
    map.current = instance;

    instance.addControl(new maplibregl.NavigationControl(), "top-right");

    // Kalau jaringan memblokir ubin, pengguna diberi tahu dan tetap punya
    // daftar koordinat dari halaman pemanggil.
    instance.on("error", (event: unknown) => {
      const message = String((event as { error?: { message?: string } })?.error?.message || "");
      if (message.includes("tile") || message.includes("Failed to fetch") || message.includes("NetworkError")) {
        setTileError(true);
      }
    });

    // Titik lokasi.
    for (const site of sites) {
      const isi = document.createElement("div");
      isi.style.color = "#111114";
      isi.style.fontSize = "13px";
      isi.style.lineHeight = "1.4";
      const judul = document.createElement("strong");
      judul.textContent = site.name;
      isi.appendChild(judul);
      if (site.habitat_type) {
        const habitat = document.createElement("div");
        habitat.style.color = "#5F6368";
        habitat.textContent = site.habitat_type.replace(/_/g, " ");
        isi.appendChild(habitat);
      }
      const popup = new maplibregl.Popup({ offset: 22 }).setDOMContent(isi);

      new maplibregl.Marker({ color: "#00AA5B" })
        .setLngLat([site.lon, site.lat])
        .setPopup(popup)
        .addTo(instance);
    }

    // Penanda arah datang dan lingkaran jangkauan, kalau datanya ada.
    const bersudut = localizations.filter((lok) => lok.azimuth_deg != null);
    const berjangkauan = localizations.filter((lok) => lok.range_m != null && lok.range_m > 0);

    for (const lok of bersudut) {
      const derajat = ((Number(lok.azimuth_deg) % 360) + 360) % 360;
      const wadah = document.createElement("div");
      wadah.style.position = "relative";
      wadah.style.width = "44px";
      wadah.style.height = "44px";
      wadah.style.display = "flex";
      wadah.style.alignItems = "center";
      wadah.style.justifyContent = "center";

      const kerucut = document.createElement("div");
      kerucut.style.width = "0";
      kerucut.style.height = "0";
      kerucut.style.borderLeft = "10px solid transparent";
      kerucut.style.borderRight = "10px solid transparent";
      kerucut.style.borderBottom = `28px solid ${WARNA_ARAH}`;
      kerucut.style.transform = `rotate(${derajat}deg)`;
      kerucut.style.transformOrigin = "center 60%";
      kerucut.setAttribute("aria-hidden", "true");
      wadah.appendChild(kerucut);

      const chip = document.createElement("span");
      chip.textContent = labelArah(derajat) || "";
      chip.style.position = "absolute";
      chip.style.top = "100%";
      chip.style.left = "50%";
      chip.style.transform = "translateX(-50%)";
      chip.style.whiteSpace = "nowrap";
      chip.style.background = "#FFFFFF";
      chip.style.color = "#111111";
      chip.style.border = `1px solid ${WARNA_ARAH}`;
      chip.style.borderRadius = "4px";
      chip.style.padding = "1px 6px";
      chip.style.fontSize = "11px";
      wadah.appendChild(chip);
      wadah.setAttribute("aria-label", `Arah datang ${chip.textContent}`);

      const isi = document.createElement("div");
      isi.style.color = "#111114";
      isi.style.fontSize = "13px";
      isi.style.lineHeight = "1.4";
      const nama = document.createElement("strong");
      nama.textContent = lok.label;
      isi.appendChild(nama);
      const rincian = document.createElement("div");
      rincian.style.color = "#5F6368";
      rincian.textContent = [
        labelArah(derajat),
        labelJangkauan(lok.range_m),
        lok.detail,
      ]
        .filter(Boolean)
        .join(" | ");
      isi.appendChild(rincian);

      new maplibregl.Marker({ element: wadah })
        .setLngLat([lok.lon, lok.lat])
        .setPopup(new maplibregl.Popup({ offset: 28 }).setDOMContent(isi))
        .addTo(instance);
    }

    // Lingkaran perkiraan jangkauan digambar sebagai poligon, bukan penanda,
    // supaya radiusnya benar-benar mengikuti skala peta.
    for (const lok of berjangkauan) {
      const radius = Number(lok.range_m);
      const data: FeatureCollection<Polygon> = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: {
              label: `${lok.label} | perkiraan jangkauan ${labelJangkauan(radius)}`,
            },
            geometry: {
              type: "Polygon",
              coordinates: [lingkaranJangkauan(lok.lat, lok.lon, radius)],
            },
          },
        ],
      };

      const idSumber = `jangkauan-${lok.key}`;
      const idIsi = `jangkauan-isi-${lok.key}`;
      const idGaris = `jangkauan-garis-${lok.key}`;

      instance.addSource(idSumber, { type: "geojson", data });
      instance.addLayer({
        id: idIsi,
        type: "fill",
        source: idSumber,
        paint: { "fill-color": WARNA_JANGKAUAN, "fill-opacity": 0.08 },
      });
      instance.addLayer({
        id: idGaris,
        type: "line",
        source: idSumber,
        paint: {
          "line-color": WARNA_JANGKAUAN,
          "line-width": 1.5,
          "line-dasharray": [2, 2],
        },
      });

      instance.on("click", idIsi, (event) => {
        const fitur = event.features?.[0];
        const teks = String(fitur?.properties?.label || lok.label);
        new maplibregl.Popup().setLngLat([lok.lon, lok.lat]).setText(teks).addTo(instance);
      });
    }

    if (bersudut.length > 0 || berjangkauan.length > 0) {
      const titik = [...bersudut, ...berjangkauan].map((lok) => [lok.lon, lok.lat] as [number, number]);
      const batas = new maplibregl.LngLatBounds();
      for (const site of sites) batas.extend([site.lon, site.lat]);
      for (const p of titik) batas.extend(p);
      instance.fitBounds(batas, { padding: 60, maxZoom: 14, duration: 0 });
    }

    return () => {
      instance.remove();
      map.current = null;
    };
  }, [sites, localizations]);

  const adaArah = localizations.some((lok) => lok.azimuth_deg != null);

  return (
    <div className="relative">
      <div
        ref={mapContainer}
        className="h-72 w-full rounded border border-[var(--border)] bg-[var(--muted)]"
        style={{ minHeight: "288px" }}
      />
      {localizations.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-[var(--muted-foreground)]">
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-xs"
              style={{ background: WARNA_ARAH }}
              aria-hidden="true"
            />
            Arah datang (derajat dan mata angin)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-full border border-dashed"
              style={{ borderColor: WARNA_JANGKAUAN }}
              aria-hidden="true"
            />
            Perkiraan jangkauan
          </span>
        </div>
      )}
      {!adaArah && catatanArah && (
        <p className="mt-2 rounded border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs text-[var(--muted-foreground)]">
          {catatanArah}
        </p>
      )}
      {tileError && (
        <div className="absolute inset-x-2 bottom-2 rounded bg-[var(--destructive-surface)] px-3 py-2 text-xs text-[var(--destructive)]">
          Peta tidak bisa memuat ubin dari OpenStreetMap. Koordinat tiap lokasi tetap tersedia di
          daftar lokasi.
        </div>
      )}
    </div>
  );
}
