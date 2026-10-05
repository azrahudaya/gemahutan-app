"use client";

import { useEffect, useRef, useState } from "react";

interface WaveformPlayerProps {
  audioUrl: string | null;
}

export function WaveformPlayer({ audioUrl }: WaveformPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return;

    let ws: any = null;
    let cancelled = false;

    import("wavesurfer.js")
      .then((WaveSurfer) => {
        if (cancelled || !containerRef.current) return;
        ws = WaveSurfer.default.create({
          // Warna dari token DESIGN.md, bukan warna terpisah.
          container: containerRef.current,
          waveColor: "#9DB3C7",
          progressColor: "#00AA5B",
          cursorColor: "#5F6368",
          barWidth: 2,
          barGap: 1,
          barRadius: 2,
          height: 80,
          normalize: true,
          backend: "WebAudio",
        });

        ws.on("play", () => setIsPlaying(true));
        ws.on("pause", () => setIsPlaying(false));
        ws.on("finish", () => setIsPlaying(false));
        ws.on("error", (err: unknown) => {
          setError(err instanceof Error ? err.message : "Berkas audio tidak bisa diputar");
        });

        ws.load(audioUrl);
        wsRef.current = ws;
      })
      .catch(() => setError("Player gagal dimuat"));

    return () => {
      cancelled = true;
      ws?.destroy();
    };
  }, [audioUrl]);

  if (!audioUrl) {
    return (
      <div className="flex h-24 items-center justify-center rounded bg-[var(--muted)]">
        <span className="text-sm text-[var(--muted-foreground)]">
          Berkas audio tidak tersedia untuk rekaman ini
        </span>
      </div>
    );
  }

  return (
    <div>
      <div ref={containerRef} className="rounded" />
      <div className="mt-2 flex items-center gap-3">
        <button
          onClick={() => wsRef.current?.playPause()}
          aria-label={isPlaying ? "Jeda audio" : "Putar audio"}
          className="rounded bg-[var(--primary)] px-4 py-1.5 text-sm font-medium text-[var(--primary-foreground)] transition-colors hover:bg-[var(--primary-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        >
          {isPlaying ? "Jeda" : "Putar"}
        </button>
        {error && <span className="text-sm text-[var(--destructive)]">{error}</span>}
      </div>
    </div>
  );
}
