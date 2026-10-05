"use client";

import { useEffect } from "react";

/**
 * Mendaftarkan service worker.
 *
 * Hanya dijalankan di produksi: di mode pengembangan berkas dari cache bisa
 * menutupi perubahan kode dan membuat orang mengejar bug yang sudah diperbaiki.
 * Kegagalan pendaftaran tidak ditampilkan ke pengguna karena aplikasi tetap
 * bekerja penuh tanpa service worker.
 */
export function PwaRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;

    const daftar = () => {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
        // Diabaikan dengan sengaja: tanpa service worker aplikasi tetap jalan,
        // yang hilang hanya cache aset statis.
      });
    };

    if (document.readyState === "complete") {
      daftar();
    } else {
      window.addEventListener("load", daftar, { once: true });
      return () => window.removeEventListener("load", daftar);
    }
  }, []);

  return null;
}
