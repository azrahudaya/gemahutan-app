import { Img, interpolate } from "remotion";
import { FileAudio, Server } from "lucide-react";
import { Alat, Bingkai, PetaHutan } from "../bagian";
import { ALAT, BURUNG, KELUAR, LENTUR, POS_BURUNG, POS_SERVER, WARNA, useWaktu } from "../tema";

// Titik pada kurva kuadrat dari alat ke server, melengkung ke atas.
function titik(a: { x: number; y: number }, t: number) {
  const kx = (a.x + POS_SERVER.x) / 2;
  const ky = Math.min(a.y, POS_SERVER.y) - 90;
  const u = 1 - t;
  return { x: u * u * a.x + 2 * u * t * kx + t * t * POS_SERVER.x, y: u * u * a.y + 2 * u * t * ky + t * t * POS_SERVER.y };
}

// Adegan 2: rekaman dari tiap alat terbang ke server.
export function AdeganKirim() {
  const frame = useWaktu();
  const tiba = ALAT.filter((_, i) => frame >= 40 + i * 6).length;

  return (
    <Bingkai nomor="02" judul="Kirim." sub="Rekaman diunggah ke server GemaHutan.">
      <PetaHutan>
        {ALAT.map((a) => (
          <Alat key={a.id} {...a} />
        ))}
        <Img
          src={`/burung/${BURUNG.berkas}`}
          style={{
            position: "absolute",
            left: POS_BURUNG.x - 44,
            top: POS_BURUNG.y - 44,
            width: 88,
            height: 88,
            borderRadius: 999,
            objectFit: "cover",
            border: `5px solid ${WARNA.dasar}`,
            opacity: 0.55,
          }}
        />

        {ALAT.map((a, i) => {
          const t = interpolate(frame, [12 + i * 6, 40 + i * 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR });
          const p = titik(a, t);
          return (
            <div
              key={a.id}
              style={{
                position: "absolute",
                left: p.x - 20,
                top: p.y - 16,
                width: 40,
                height: 32,
                borderRadius: 10,
                backgroundColor: WARNA.primer,
                color: WARNA.dasar,
                display: "grid",
                placeItems: "center",
                boxShadow: "0 8px 18px rgb(0 0 0 / 0.18)",
                opacity: interpolate(t, [0, 0.08, 0.92, 1], [0, 1, 1, 0]),
                scale: interpolate(t, [0, 0.15, 1], [0.5, 1, 0.6]),
              }}
            >
              <FileAudio size={20} strokeWidth={2.2} />
            </div>
          );
        })}

        <div
          style={{
            position: "absolute",
            left: POS_SERVER.x - 82,
            top: POS_SERVER.y - 36,
            width: 164,
            height: 72,
            borderRadius: 20,
            backgroundColor: WARNA.dasar,
            border: `2px solid color-mix(in oklab, ${WARNA.aksen} ${interpolate(frame, [36, 46], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR })}%, ${WARNA.garis})`,
            boxShadow: `0 0 0 ${interpolate(frame, [36, 46], [0, 8], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR })}px color-mix(in oklab, ${WARNA.aksen} 25%, transparent), 0 10px 24px rgb(0 0 0 / 0.1)`,
            display: "flex",
            alignItems: "center",
            gap: 12,
            paddingLeft: 18,
            scale: interpolate(frame, [0, 14], [0.6, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR }),
          }}
        >
          <Server size={30} color={WARNA.primer} strokeWidth={2.2} />
          <div style={{ display: "grid", lineHeight: 1.1 }}>
            <span style={{ fontSize: 20, fontWeight: 600 }}>Server</span>
            <span style={{ fontSize: 16, color: WARNA.redup, fontVariantNumeric: "tabular-nums" }}>{tiba}/4 berkas</span>
          </div>
        </div>
      </PetaHutan>
    </Bingkai>
  );
}
