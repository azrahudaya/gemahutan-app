import { Img, interpolate } from "remotion";
import { MapPin, Printer } from "lucide-react";
import { Alat, Bingkai, PetaHutan } from "../bagian";
import { ALAT, BURUNG, KELUAR, LENTUR, PANGGUNG, POS_BURUNG, WARNA, useWaktu } from "../tema";

const C = ALAT[2];
const SUDUT = Math.atan2(POS_BURUNG.y - C.y, POS_BURUNG.x - C.x);
const PANJANG = Math.hypot(POS_BURUNG.x - C.x, POS_BURUNG.y - C.y) + 60;
const LEBAR = (13 * Math.PI) / 180;
const KERUCUT = `M${C.x},${C.y} L${C.x + Math.cos(SUDUT - LEBAR) * PANJANG},${C.y + Math.sin(SUDUT - LEBAR) * PANJANG} L${C.x + Math.cos(SUDUT + LEBAR) * PANJANG},${C.y + Math.sin(SUDUT + LEBAR) * PANJANG} Z`;

// Adegan 5: arah dari alat C, pin spesies, dan kartu laporan.
export function AdeganPeta() {
  const frame = useWaktu();

  return (
    <Bingkai nomor="05" judul="Petakan." sub="Di aplikasi lengkap, hasil tampil di peta dan laporan.">
      <PetaHutan>
        <svg width={PANGGUNG.w} height={PANGGUNG.h} style={{ position: "absolute", inset: 0 }}>
          <path
            d={KERUCUT}
            style={{
              fill: WARNA.aksen,
              fillOpacity: interpolate(frame, [6, 26], [0, 0.28], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
              transformOrigin: `${C.x}px ${C.y}px`,
              scale: interpolate(frame, [6, 30], [0.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR }),
            }}
          />
        </svg>
        {ALAT.map((a) => (
          <Alat key={a.id} {...a} nyala={a.id === "C" ? interpolate(frame, [4, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0} />
        ))}
        <Img
          src={`/burung/${BURUNG.berkas}`}
          style={{
            position: "absolute",
            left: POS_BURUNG.x - 36,
            top: POS_BURUNG.y - 36,
            width: 72,
            height: 72,
            borderRadius: 999,
            objectFit: "cover",
            border: `4px solid ${WARNA.dasar}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: POS_BURUNG.x + 22,
            top: POS_BURUNG.y - 96,
            color: WARNA.primer,
            translate: interpolate(frame, [20, 38], ["0px -140px", "0px 0px"], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR }),
            opacity: interpolate(frame, [20, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          <MapPin size={64} strokeWidth={1.8} style={{ fill: WARNA.aksen, stroke: WARNA.dasar }} />
        </div>
        <div
          style={{
            position: "absolute",
            left: POS_BURUNG.x - 70,
            top: POS_BURUNG.y + 48,
            padding: "8px 16px",
            borderRadius: 999,
            backgroundColor: WARNA.aksen,
            color: "var(--color-accent-content)",
            fontSize: 20,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 8,
            opacity: interpolate(frame, [32, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          {BURUNG.nama}
        </div>

        <div
          style={{
            position: "absolute",
            left: 24,
            right: 24,
            bottom: 24,
            borderRadius: 22,
            backgroundColor: WARNA.dasar,
            border: `2px solid ${WARNA.garis}`,
            boxShadow: "0 14px 30px rgb(0 0 0 / 0.1)",
            padding: "18px 22px",
            display: "flex",
            alignItems: "center",
            gap: 16,
            translate: interpolate(frame, [42, 60], ["0px 140px", "0px 0px"], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR }),
          }}
        >
          <Printer size={30} color={WARNA.primer} strokeWidth={2.2} />
          <div style={{ display: "grid", lineHeight: 1.2 }}>
            <span style={{ fontSize: 22, fontWeight: 600 }}>Laporan siap dicetak</span>
            <span style={{ fontSize: 18, color: WARNA.redup }}>{BURUNG.nama} · prediksi AI · stasiun C</span>
          </div>
        </div>
      </PetaHutan>
    </Bingkai>
  );
}
