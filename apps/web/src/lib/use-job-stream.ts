"use client";

import { useEffect, useRef } from "react";

import { api } from "@/lib/api";

export interface JobUpdate {
  recording_id?: number | null;
  job_id?: number | null;
  status?: string | null;
  progress?: number | null;
  stage?: string | null;
}

/** Selang cadangan kalau siaran status tidak bisa dipakai. */
export const POLL_INTERVAL_MS = 5000;

function kirim(penerima: React.MutableRefObject<(update: JobUpdate) => void>, update: JobUpdate) {
  try {
    penerima.current(update);
  } catch {
    // Kesalahan pada pemanggil tidak boleh mematikan koneksi siaran.
  }
}

/**
 * Siaran progres job lewat EventSource, dengan cadangan polling lima detik.
 *
 * Stream dipakai sebagai pelengkap: kalau peramban menutup koneksi atau server
 * menolaknya, hook ini berpindah ke polling supaya progres tetap segar.
 * Koneksi dan timer selalu dibersihkan saat komponen dibongkar.
 */
export function useJobStream(aktif: boolean, onUpdate: (update: JobUpdate) => void) {
  const penerima = useRef(onUpdate);
  penerima.current = onUpdate;

  useEffect(() => {
    if (!aktif || typeof window === "undefined") return;

    let dibatalkan = false;
    let sumber: EventSource | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;

    const hentikanPolling = () => {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const mulaiPolling = () => {
      if (dibatalkan || timer) return;
      const tarik = async () => {
        try {
          const jobs = await api.getJobs({ status: "active" });
          if (dibatalkan || !Array.isArray(jobs)) return;
          for (const job of jobs) {
            kirim(penerima, {
              recording_id: job?.recording_id ?? null,
              job_id: job?.id ?? null,
              status: job?.status ?? null,
              progress: job?.progress ?? null,
              stage: job?.stage ?? null,
            });
          }
        } catch {
          // Jaringan sedang bermasalah: biarkan siklus berikutnya mencoba lagi.
        }
      };
      void tarik();
      timer = setInterval(tarik, POLL_INTERVAL_MS);
    };

    if (typeof EventSource === "undefined") {
      mulaiPolling();
    } else {
      try {
        sumber = new EventSource(api.jobStreamUrl());
        sumber.addEventListener("job", (event) => {
          try {
            kirim(penerima, JSON.parse((event as MessageEvent).data) as JobUpdate);
          } catch {
            // Data rusak diabaikan, stream tetap hidup.
          }
        });
        sumber.onopen = () => hentikanPolling();
        sumber.onerror = () => {
          if (sumber) {
            sumber.close();
            sumber = null;
          }
          mulaiPolling();
        };
      } catch {
        mulaiPolling();
      }
    }

    return () => {
      dibatalkan = true;
      hentikanPolling();
      if (sumber) {
        sumber.close();
        sumber = null;
      }
    };
  }, [aktif]);
}
