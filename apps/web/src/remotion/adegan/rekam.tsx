import { Img, interpolate } from "remotion";
import { Alat, Bingkai, PetaHutan } from "../bagian";
import { ALAT, BURUNG, KELUAR, LENTUR, POS_BURUNG, WARNA, useWaktu } from "../tema";

// Adegan 1: burung berkicau, gelombang suaranya menyebar dan mengenai alat perekam.
export function AdeganRekam() {
  const frame = useWaktu();

  return (
    <Bingkai nomor="01" judul="Rekam." sub="Alat di hutan menangkap kicau satwa.">
      <div
        style={{
          position: "absolute",
          inset: 0,
          scale: interpolate(frame, [0, 78], [1.14, 1.04], { extrapolateRight: "clamp" }),
          opacity: interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        <PetaHutan>
          {[0, 1, 2].map((i) => {
            const mulai = 12 + i * 14;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: POS_BURUNG.x - 300,
                  top: POS_BURUNG.y - 300,
                  width: 600,
                  height: 600,
                  borderRadius: 999,
                  border: `3px solid ${WARNA.aksen}`,
                  scale: interpolate(frame, [mulai, mulai + 42], [0.08, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: KELUAR }),
                  opacity: interpolate(frame, [mulai, mulai + 6, mulai + 42], [0, 0.9, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              />
            );
          })}

          {ALAT.map((a, i) => {
            const jarak = Math.hypot(a.x - POS_BURUNG.x, a.y - POS_BURUNG.y);
            const kena = 14 + (jarak / 300) * 30;
            return (
              <Alat
                key={a.id}
                {...a}
                muncul={interpolate(frame, [4 + i * 4, 18 + i * 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR })}
                nyala={interpolate(frame, [kena, kena + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
              />
            );
          })}

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
              boxShadow: "0 10px 26px rgb(0 0 0 / 0.16)",
              scale: interpolate(frame, [0, 16], [0.4, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: LENTUR }),
            }}
          />
        </PetaHutan>
      </div>
    </Bingkai>
  );
}
