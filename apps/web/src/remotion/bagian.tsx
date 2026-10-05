import type { ReactNode } from "react";
import { AbsoluteFill, interpolate, useVideoConfig } from "remotion";
import { Mic } from "lucide-react";
import { FONT, KELUAR, PANGGUNG, WARNA, useWaktu } from "./tema";

/*
 * Bingkai tiap adegan: judul besar di kiri (atau atas pada versi tegak) dan panggung
 * ilustrasi 680 x 500 di kanan (atau bawah).
 */
export function Bingkai({ nomor, judul, sub, children }: { nomor: string; judul: string; sub: string; children: ReactNode }) {
  const frame = useWaktu();
  const { width, height } = useVideoConfig();
  const tegak = height > width;

  return (
    <AbsoluteFill style={{ backgroundColor: WARNA.dasar, fontFamily: FONT, color: WARNA.teks }}>
      <div
        style={
          tegak
            ? { position: "absolute", left: 56, right: 56, top: 64 }
            : { position: "absolute", left: 72, width: 430, top: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: "center" }
        }
      >
        <div
          style={{
            fontSize: 22,
            fontWeight: 600,
            fontVariantNumeric: "tabular-nums",
            color: WARNA.redup,
            opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          {nomor} / 05
        </div>
        <div style={{ overflow: "hidden", paddingBottom: 8, marginTop: 8 }}>
          <div
            style={{
              fontSize: tegak ? 92 : 96,
              fontWeight: 600,
              letterSpacing: "-0.035em",
              lineHeight: 1,
              translate: interpolate(frame, [0, 26], ["0px 110%", "0px 0%"], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: KELUAR,
              }),
            }}
          >
            {judul}
          </div>
        </div>
        <div
          style={{
            fontSize: tegak ? 32 : 30,
            lineHeight: 1.3,
            marginTop: 14,
            color: WARNA.redup,
            opacity: interpolate(frame, [8, 32], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            translate: interpolate(frame, [8, 32], ["0px 14px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: KELUAR,
            }),
          }}
        >
          {sub}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          width: PANGGUNG.w,
          height: PANGGUNG.h,
          ...(tegak ? { left: (width - PANGGUNG.w) / 2, top: 336 } : { right: 64, top: (height - PANGGUNG.h) / 2 }),
          borderRadius: 32,
          overflow: "hidden",
          border: `2px solid ${WARNA.garis}`,
          backgroundColor: WARNA.dasar2,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
}

/* Peta hutan dari atas: sungai, tajuk pohon berkelompok, dan garis kontur tipis. */
const TAJUK = [
  [70, 60, 46], [120, 40, 30], [40, 200, 40], [210, 120, 34], [180, 330, 44], [250, 440, 38],
  [360, 300, 48], [390, 190, 30], [560, 150, 40], [620, 300, 34], [600, 450, 46], [80, 460, 36],
  [330, 60, 26], [470, 470, 30],
] as const;

export function PetaHutan({ children }: { children?: ReactNode }) {
  return (
    <div style={{ position: "absolute", inset: 0, backgroundColor: WARNA.lembut }}>
      <svg width={PANGGUNG.w} height={PANGGUNG.h} style={{ position: "absolute", inset: 0 }}>
        {[120, 220, 320].map((y, i) => (
          <path
            key={y}
            d={`M-20,${y} C140,${y - 50 + i * 10} 300,${y + 40} 470,${y - 20} S700,${y + 30} 720,${y}`}
            style={{ fill: "none", stroke: WARNA.dasar, strokeOpacity: 0.55, strokeWidth: 1.5 }}
          />
        ))}
        <path d="M470,-10 C430,90 520,170 470,260 C430,340 500,420 470,520" style={{ fill: "none", stroke: WARNA.dasar, strokeWidth: 22, strokeLinecap: "round" }} />
        <path d="M470,-10 C430,90 520,170 470,260 C430,340 500,420 470,520" style={{ fill: "none", stroke: WARNA.aksen, strokeOpacity: 0.18, strokeWidth: 10, strokeLinecap: "round" }} />
        {TAJUK.map(([x, y, r], i) => (
          <g key={i}>
            <circle cx={x} cy={y} r={r} style={{ fill: WARNA.aksen, fillOpacity: 0.2 }} />
            <circle cx={x - r * 0.3} cy={y - r * 0.25} r={r * 0.55} style={{ fill: WARNA.aksen, fillOpacity: 0.16 }} />
          </g>
        ))}
      </svg>
      {children}
    </div>
  );
}

/* Alat perekam di peta. `nyala` menandai alat yang sedang menangkap suara. */
export function Alat({ x, y, id, nyala = 0, muncul = 1 }: { x: number; y: number; id: string; nyala?: number; muncul?: number }) {
  return (
    <div
      style={{
        position: "absolute",
        left: x - 26,
        top: y - 26,
        width: 52,
        height: 52,
        borderRadius: 16,
        backgroundColor: WARNA.dasar,
        border: `2px solid ${nyala > 0.5 ? WARNA.aksen : WARNA.garis}`,
        boxShadow: `0 0 0 ${nyala * 10}px color-mix(in oklab, ${WARNA.aksen} 28%, transparent), 0 6px 16px rgb(0 0 0 / 0.08)`,
        display: "grid",
        placeItems: "center",
        color: nyala > 0.5 ? WARNA.primer : WARNA.redup,
        scale: muncul,
        opacity: Math.min(1, muncul * 1.5),
      }}
    >
      <Mic size={24} strokeWidth={2.2} />
      <span
        style={{
          position: "absolute",
          right: -9,
          top: -9,
          width: 24,
          height: 24,
          borderRadius: 999,
          backgroundColor: WARNA.teks,
          color: WARNA.dasar,
          fontSize: 13,
          fontWeight: 700,
          display: "grid",
          placeItems: "center",
        }}
      >
        {id}
      </span>
    </div>
  );
}
