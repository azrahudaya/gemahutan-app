"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function FormAturSandi() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [sandi, setSandi] = useState("");
  const [galat, setGalat] = useState("");
  const [memproses, setMemproses] = useState(false);

  const kirim = async (e: React.FormEvent) => {
    e.preventDefault();
    setGalat("");
    setMemproses(true);
    try {
      await api.activateAccount(token, sandi);
      router.push("/login");
    } catch (err) {
      setGalat((err as Error).message || "Akun tidak bisa diaktifkan.");
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
          <h1 className="mt-1 text-xl font-bold text-[var(--foreground)]">Buat sandi untuk akun</h1>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            Selesaikan undangan dengan membuat sandi sendiri.
          </p>
        </div>

        {!token ? (
          <p className="text-center text-sm text-[var(--muted-foreground)]">
            Tautan undangan tidak lengkap. Minta admin mengirim undangan baru.
          </p>
        ) : (
          <form onSubmit={kirim} className="space-y-4">
            {galat && (
              <div className="rounded bg-[var(--destructive-surface)] px-3 py-2 text-sm text-[var(--destructive)]">
                {galat}
              </div>
            )}
            <div>
              <label htmlFor="sandi" className="mb-1 block text-sm text-[var(--muted-foreground)]">
                Sandi
              </label>
              <input
                id="sandi"
                type="password"
                required
                minLength={8}
                value={sandi}
                onChange={(e) => setSandi(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <button
              type="submit"
              disabled={memproses}
              className="w-full rounded-md bg-[var(--primary)] py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2 transition-opacity"
            >
              {memproses ? "Mengaktifkan..." : "Aktifkan akun"}
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

export default function AturSandiPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-[var(--muted-foreground)]">Memuat...</div>}>
      <FormAturSandi />
    </Suspense>
  );
}
