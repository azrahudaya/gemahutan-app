import { Img, interpolate } from "remotion";
import { Cpu } from "lucide-react";
import { Bingkai } from "../bagian";
import { BURUNG, KELUAR, LENTUR, WARNA, useWaktu } from "../tema";

// Adegan 4: AI menebak spesies dari suaranya; bilah keyakinan terisi.
export function AdeganKenali() {
  const frame = useWaktu();

  return (
    <Bingkai nomor="04" judul="Kenali." sub="AI menebak spesies dari suaranya.">
      <div style={{ position: "absolute", inset: 0, backgroundColor: WARNA.dasar, display: "grid", placeItems: "center" }}>
        <div
          style={{
            width: 500,
            borderRadius: 28,
            border: `2px solid ${WARNA.garis}`,
            backgroundColor: WARNA.dasar,
            boxShadow: "0 18px 40px rgb(0 0 0 / 0.08)",
            padding: 32,
            display: "grid",
            gap: 26,
            scale: interpolate(frame, [0, 16], [0.92, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR }),
            opacity: interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <Img
              src={`/burung/${BURUNG.berkas}`}
              style={{
                width: 128,
                height: 128,
                borderRadius: 999,
                objectFit: "cover",
                scale: interpolate(frame, [4, 20], [0.6, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR }),
              }}
            />
            <div style={{ display: "grid", gap: 6 }}>
              <span
                style={{
                  fontSize: 48,
                  fontWeight: 600,
                  letterSpacing: "-0.02em",
                  opacity: interpolate(frame, [10, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  translate: interpolate(frame, [10, 22], ["0px 14px", "0px 0px"], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR }),
                }}
              >
                {BURUNG.nama}
              </span>
              <span
                style={{
                  fontSize: 24,
                  fontStyle: "italic",
                  color: WARNA.redup,
                  opacity: interpolate(frame, [16, 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              >
                {BURUNG.ilmiah}
              </span>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              borderTop: `2px solid ${WARNA.garis}`,
              paddingTop: 22,
              opacity: interpolate(frame, [26, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            }}
          >
            <Cpu size={30} color={WARNA.primer} strokeWidth={2.2} />
            <div style={{ flex: 1, display: "grid", gap: 10 }}>
              <span style={{ fontSize: 22, fontWeight: 600 }}>Prediksi AI</span>
              <div style={{ height: 12, borderRadius: 999, backgroundColor: WARNA.garis, overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    borderRadius: 999,
                    backgroundColor: WARNA.aksen,
                    width: `${interpolate(frame, [32, 58], [0, 86], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR })}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </Bingkai>
  );
}
