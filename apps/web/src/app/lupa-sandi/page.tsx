"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function LupaSandiPage() {
  const [email, setEmail] = useState("");
  const [galat, setGalat] = useState("");
  const [terkirim, setTerkirim] = useState(false);
  const [memproses, setMemproses] = useState(false);

  const kirim = async (e: React.FormEvent) => {
    e.preventDefault();
    setGalat("");
    setMemproses(true);
    try {
      await api.forgotPassword(email);
      setTerkirim(true);
    } catch (err) {
      setGalat((err as Error).message || "Gagal mengirim tautan.");
    } finally {
      setMemproses(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-[var(--border)] bg-[var(--card)] p-8">
        <div className="mb-6 text-center">
          <Link href="/" className="inline-block text-lg font-semibold tracking-tight text-[var(--foreground)] hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]">
            GemaHutan
          </Link>
          <h1 className="mt-1 text-xl font-bold text-[var(--foreground)]">Lupa sandi</h1>
        </div>

        {terkirim ? (
          <div className="space-y-4 text-center">
            <p className="text-sm text-[var(--muted-foreground)]">
              Kalau alamat itu terdaftar, tautan atur ulang sandi sudah dikirim. Periksa
              kotak masuk dan folder spam.
            </p>
            <Link
              href="/login"
              className="block text-sm text-[var(--primary-text)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              Kembali ke halaman masuk
            </Link>
          </div>
        ) : (
          <form onSubmit={kirim} className="space-y-4">
            {galat && (
              <div className="rounded bg-[var(--destructive-surface)] px-3 py-2 text-sm text-[var(--destructive)]">
                {galat}
              </div>
            )}
            <div>
              <label htmlFor="email" className="mb-1 block text-sm text-[var(--muted-foreground)]">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <button
              type="submit"
              disabled={memproses}
              className="w-full rounded-md bg-[var(--primary)] py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2 transition-opacity"
            >
              {memproses ? "Mengirim..." : "Kirim tautan"}
            </button>
            <p className="text-center text-sm text-[var(--muted-foreground)]">
              <Link
                href="/login"
                className="text-[var(--primary-text)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                Kembali ke halaman masuk
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
