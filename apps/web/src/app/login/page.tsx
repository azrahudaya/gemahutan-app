"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const role = await login(email, password);
      router.push(role === "ranger" ? "/rekam" : "/dashboard");
    } catch (err) {
      setError((err as Error).message || "Login gagal");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-[var(--border)] bg-[var(--card)] p-8">
        <div className="mb-6 text-center">
          <Link href="/" className="inline-block text-lg font-semibold tracking-tight text-[var(--foreground)] hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]">
            GemaHutan
          </Link>
          <h1 className="mt-1 text-xl font-bold text-[var(--foreground)]">Masuk ke GemaHutan</h1>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            Pemantauan satwa hutan lewat suara untuk petugas konservasi
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded bg-[var(--destructive-surface)] px-3 py-2 text-sm text-[var(--destructive)]">
              {error}
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
          <div>
            <label htmlFor="password" className="mb-1 block text-sm text-[var(--muted-foreground)]">
              Kata Sandi
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>
          <div className="text-right">
            <Link
              href="/lupa-sandi"
              className="text-sm text-[var(--primary-text)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              Lupa sandi?
            </Link>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-[var(--primary)] py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2 transition-opacity"
          >
            {submitting ? "Memproses..." : "Masuk"}
          </button>
        </form>
        <div className="mt-6 text-center">
          <Link href="/" className="text-sm text-[var(--muted-foreground)] underline hover:text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]">
            Kembali ke beranda
          </Link>
        </div>
      </div>
    </div>
  );
}
