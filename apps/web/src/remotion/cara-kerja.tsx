import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { AdeganRekam } from "./adegan/rekam";
import { AdeganKirim } from "./adegan/kirim";
import { AdeganPilah } from "./adegan/pilah";
import { AdeganKenali } from "./adegan/kenali";
import { AdeganPeta } from "./adegan/peta";
import { DURASI, FONT, HALUS, TOTAL_FRAME, TRANSISI, WARNA } from "./tema";

/*
 * Video cara kerja GemaHutan, sekitar 12 detik pada 60 fps, diputar berulang di halaman
 * depan lewat @remotion/player. Ukuran mendatar 1280 x 720 untuk layar lebar, tegak 720 x 900 untuk HP.
 */

// Awal tiap adegan pada garis waktu, dipakai bilah langkah di bawah.
const AWAL = [
  0,
  DURASI.rekam - TRANSISI,
  DURASI.rekam + DURASI.kirim - 2 * TRANSISI,
  DURASI.rekam + DURASI.kirim + DURASI.pilah - 3 * TRANSISI,
  DURASI.rekam + DURASI.kirim + DURASI.pilah + DURASI.kenali - 4 * TRANSISI,
];

export function CaraKerja() {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const tegak = height > width;

  return (
    <AbsoluteFill style={{ backgroundColor: WARNA.dasar, fontFamily: FONT }}>
      <TransitionSeries>
        <TransitionSeries.Sequence name="Rekam" durationInFrames={DURASI.rekam} premountFor={fps}>
          <AdeganRekam />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSISI, easing: HALUS })} />
        <TransitionSeries.Sequence name="Kirim" durationInFrames={DURASI.kirim} premountFor={fps}>
          <AdeganKirim />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSISI, easing: HALUS })} />
        <TransitionSeries.Sequence name="Pilah" durationInFrames={DURASI.pilah} premountFor={fps}>
          <AdeganPilah />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSISI, easing: HALUS })} />
        <TransitionSeries.Sequence name="Kenali" durationInFrames={DURASI.kenali} premountFor={fps}>
          <AdeganKenali />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSISI, easing: HALUS })} />
        <TransitionSeries.Sequence name="Petakan" durationInFrames={DURASI.peta} premountFor={fps}>
          <AdeganPeta />
        </TransitionSeries.Sequence>
      </TransitionSeries>

      <div
        style={
          tegak
            ? { position: "absolute", left: 20, right: 20, bottom: 26, display: "flex", gap: 8 }
            : { position: "absolute", left: 72, width: 400, bottom: 64, display: "flex", gap: 8 }
        }
      >
        {AWAL.map((mulai, i) => {
          const akhir = i < AWAL.length - 1 ? AWAL[i + 1] : TOTAL_FRAME;
          return (
            <div key={mulai} style={{ flex: 1, height: 6, borderRadius: 6, backgroundColor: WARNA.garis, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  borderRadius: 6,
                  backgroundColor: WARNA.aksen,
                  width: `${interpolate(frame, [mulai, akhir], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%`,
                }}
              />
            </div>
          );
        })}
      </div>

      <AbsoluteFill
        style={{
          backgroundColor: WARNA.dasar,
          pointerEvents: "none",
          opacity: interpolate(frame, [0, 30, TOTAL_FRAME - 48, TOTAL_FRAME - 1], [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: HALUS }),
        }}
      />
    </AbsoluteFill>
  );
}
