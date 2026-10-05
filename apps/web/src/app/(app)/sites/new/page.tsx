"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function SiteNewPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    location: "",
    latitude: "",
    longitude: "",
    elevation: "",
    habitat_type: "",
    description: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await api.createSite(formData);
      // Daftar lokasi di-cache react-query, jadi harus disegarkan dulu supaya
      // lokasi baru langsung terlihat setelah redirect.
      await queryClient.invalidateQueries({ queryKey: ["sites"] });
      router.push("/sites");
    } catch (err) {
      setError((err as Error)?.message || "Gagal membuat lokasi. Coba lagi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Tambah Lokasi</h1>
        <Link
          href="/sites"
          className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        >
          Kembali
        </Link>
      </div>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div
              role="alert"
              className="rounded border border-[var(--destructive)] bg-[var(--destructive-surface)] p-3 text-sm text-[var(--destructive)]"
            >
              {error}
            </div>
          )}

          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Nama Lokasi *
            </label>
            <input
              type="text"
              name="name" id="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Contoh: Hutan Gunung Gede"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="latitude" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
                Koordinat Lintang
              </label>
              <input
                type="number"
                name="latitude" id="latitude"
                value={formData.latitude}
                onChange={handleChange}
                step="0.000001"
                className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                placeholder="Contoh: -6.2088"
              />
            </div>
            <div>
              <label htmlFor="longitude" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
                Koordinat Bujur
              </label>
              <input
                type="number"
                name="longitude" id="longitude"
                value={formData.longitude}
                onChange={handleChange}
                step="0.000001"
                className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                placeholder="Contoh: 106.8456"
              />
            </div>
          </div>

          <div>
            <label htmlFor="elevation" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Ketinggian (mdpl)
            </label>
            <input
              type="number"
              name="elevation" id="elevation"
              value={formData.elevation}
              onChange={handleChange}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Contoh: 1500"
            />
          </div>

          <div>
            <label htmlFor="habitat_type" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Tipe Habitat
            </label>
            <select
              name="habitat_type" id="habitat_type"
              value={formData.habitat_type}
              onChange={handleChange}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="">Pilih tipe habitat</option>
              <option value="hutan_tropis">Hutan Tropis</option>
              <option value="hutan_mangrove">Hutan Mangrove</option>
              <option value="hutan_gunung">Hutan Gunung</option>
              <option value="kawasan_konservasi">Kawasan Konservasi</option>
              <option value="lainnya">Lainnya</option>
            </select>
          </div>

          <div>
            <label htmlFor="location" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Lokasi (Kota/Provinsi)
            </label>
            <input
              type="text"
              name="location" id="location"
              value={formData.location}
              onChange={handleChange}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Contoh: Bogor, Jawa Barat"
            />
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Deskripsi
            </label>
            <textarea
              name="description" id="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Deskripsi singkat lokasi..."
            />
          </div>

          <div>
            <label htmlFor="notes" className="mb-1 block text-sm font-medium text-[var(--foreground)]">
              Catatan
            </label>
            <textarea
              name="notes" id="notes"
              value={formData.notes}
              onChange={handleChange}
              rows={2}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Catatan tambahan..."
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[var(--border)]">
            <Link
              href="/sites"
              className="rounded-md border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--card-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              Batal
            </Link>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2"
            >
              {isSubmitting ? "Menyimpan..." : "Simpan Lokasi"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
