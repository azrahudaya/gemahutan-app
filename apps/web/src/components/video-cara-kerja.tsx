"use client";

import { useEffect, useRef, useState } from "react";
import { Player, type PlayerRef } from "@remotion/player";
import { Pause, Play } from "lucide-react";
import { CaraKerja } from "@/remotion/cara-kerja";
import { FPS, TOTAL_FRAME } from "@/remotion/tema";

/*
 * Pemutar video cara kerja (Remotion) di halaman depan. Langsung jalan dan berulang terus
 * seperti GIF, bisa dijeda, dan berhenti di bingkai terakhir kalau pengguna memilih kurangi
 * gerakan. Layar sempit memakai versi tegak.
 */
export default function VideoCaraKerja() {
  const pemutar = useRef<PlayerRef>(null);
  const [tegak, setTegak] = useState(false);
  const [siap, setSiap] = useState(false);
  const [dijeda, setDijeda] = useState(false);
  const [kurangiGerak, setKurangiGerak] = useState(false);

  useEffect(() => {
    const sempit = window.matchMedia("(max-width: 639px)");
    const ubah = () => setTegak(sempit.matches);
    ubah();
    sempit.addEventListener("change", ubah);
    setKurangiGerak(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    setSiap(true);
    return () => sempit.removeEventListener("change", ubah);
  }, []);

  useEffect(() => {
    const p = pemutar.current;
    if (!p) return;
    if (kurangiGerak) {
      p.pause();
      p.seekTo(TOTAL_FRAME - 70);
      return;
    }
    if (dijeda) p.pause();
    else p.play();
  }, [dijeda, kurangiGerak, tegak, siap]);

  return (
    <figure className="relative mx-auto max-w-5xl overflow-hidden rounded-box border border-base-300 bg-base-100 shadow-sm">
      <div aria-hidden="true">
        {siap && (
          <Player
            ref={pemutar}
            key={tegak ? "tegak" : "datar"}
            component={CaraKerja}
            durationInFrames={TOTAL_FRAME}
            fps={FPS}
            compositionWidth={tegak ? 720 : 1280}
            compositionHeight={tegak ? 900 : 720}
            loop
            autoPlay={!kurangiGerak}
            controls={false}
            clickToPlay={false}
            doubleClickToFullscreen={false}
            spaceKeyToPlayOrPause={false}
            acknowledgeRemotionLicense
            style={{ width: "100%", aspectRatio: tegak ? "720 / 900" : "1280 / 720" }}
          />
        )}
        {!siap && <div className="aspect-[720/900] w-full bg-base-200 sm:aspect-[1280/720]" />}
      </div>
      <figcaption className="sr-only">
        Video cara kerja: alat di hutan merekam kicau, rekaman dikirim ke server, audio dipilah per 3 detik, spesies
        ditebak oleh AI, dan di aplikasi lengkap hasilnya tampil di peta dan laporan.
      </figcaption>
      {!kurangiGerak && (
        <button
          type="button"
          className="btn btn-sm btn-circle absolute right-3 top-3 border-base-300 bg-base-100/90"
          onClick={() => setDijeda((d) => !d)}
          aria-label={dijeda ? "Putar video" : "Jeda video"}
        >
          {dijeda ? <Play className="size-4" aria-hidden="true" /> : <Pause className="size-4" aria-hidden="true" />}
        </button>
      )}
    </figure>
  );
}
