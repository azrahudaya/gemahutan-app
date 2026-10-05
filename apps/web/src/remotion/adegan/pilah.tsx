import { interpolate } from "remotion";
import { Bingkai } from "../bagian";
import { KELUAR, WARNA, useWaktu } from "../tema";

// 48 batang = 12 detik rekaman, satu jendela 3 detik = 12 batang. Jendela kedua berisi kicau.
const BATANG = Array.from({ length: 48 }, (_, i) => {
  const dasar = Math.abs(Math.sin(i * 1.3) * 0.6 + Math.sin(i * 0.47) * 0.4);
  return i >= 12 && i < 24 ? 0.55 + Math.abs(Math.sin(i * 2.1)) * 0.42 : 0.1 + dasar * 0.22;
});
const LEBAR = 600;
const KICAU = 1;

// Adegan 3: rekaman dibaca per 3 detik, jendela yang berisi kicau menyala.
export function AdeganPilah() {
  const frame = useWaktu();
  const kepala = interpolate(frame, [8, 70], [0, LEBAR], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR });

  return (
    <Bingkai nomor="03" judul="Pilah." sub="Audio dibaca per 3 detik.">
      <div style={{ position: "absolute", inset: 0, backgroundColor: WARNA.dasar }}>
        <div style={{ position: "absolute", left: 40, top: 120, width: LEBAR, height: 220 }}>
          {[0, 1, 2, 3].map((k) => {
            const tampak = interpolate(kepala, [k * (LEBAR / 4) + 20, (k + 1) * (LEBAR / 4)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const kicau = k === KICAU;
            return (
              <div
                key={k}
                style={{
                  position: "absolute",
                  left: k * (LEBAR / 4) + 3,
                  top: 0,
                  width: LEBAR / 4 - 6,
                  height: 220,
                  borderRadius: 18,
                  backgroundColor: kicau ? WARNA.lembut : WARNA.dasar2,
                  opacity: tampak,
                  border: kicau && tampak > 0.5 ? `2px solid ${WARNA.aksen}` : "2px solid transparent",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: -44,
                    textAlign: "center",
                    fontSize: 18,
                    fontWeight: 600,
                    color: kicau ? WARNA.primer : WARNA.redup,
                    opacity: tampak,
                  }}
                >
                  {kicau ? "Kicau" : "Sunyi"}
                </span>
              </div>
            );
          })}

          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", gap: 4, padding: "0 10px" }}>
            {BATANG.map((h, i) => {
              const x = (i + 0.5) * (LEBAR / BATANG.length);
              const kicau = i >= 12 && i < 24;
              return (
                <span
                  key={i}
                  style={{
                    flex: 1,
                    height: `${h * 100}%`,
                    borderRadius: 4,
                    backgroundColor: kicau && kepala > x ? WARNA.aksen : WARNA.garis,
                    scale: interpolate(frame, [i * 0.4, i * 0.4 + 10], [0.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR }),
                  }}
                />
              );
            })}
          </div>

          <div
            style={{
              position: "absolute",
              left: kepala - 2,
              top: -16,
              width: 4,
              height: 252,
              borderRadius: 4,
              backgroundColor: WARNA.primer,
              opacity: interpolate(frame, [6, 10, 70, 76], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            }}
          />
        </div>

        <div style={{ position: "absolute", left: 40, top: 372, width: LEBAR, display: "flex", justifyContent: "space-between", fontSize: 18, color: WARNA.redup, fontVariantNumeric: "tabular-nums" }}>
          {["0:00", "0:03", "0:06", "0:09", "0:12"].map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </div>
    </Bingkai>
  );
}
