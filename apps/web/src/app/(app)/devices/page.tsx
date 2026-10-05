"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { useAuth } from "@/lib/auth";
import { ErrorState, EmptyState, Skeleton, TableSkeleton } from "@/components/ui";

type Perangkat = components["schemas"]["DeviceResponse"];
type Situs = components["schemas"]["SiteResponse"];

const JENIS_PERANGKAT: Record<string, string> = {
  audiomoth: "AudioMoth",
  phone: "Ponsel",
  other: "Lainnya",
};

const inputClass =
  "mt-1 w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50";

interface FormPerangkat {
  name: string;
  type: string;
  site_id: string;
  serial: string;
  channel_count: string;
  mic_spacing_m: string;
  reference_distance_m: string;
  reference_level_db: string;
  installed_at: string;
  notes: string;
  active: boolean;
}

const FORM_KOSONG: FormPerangkat = {
  name: "",
  type: "audiomoth",
  site_id: "",
  serial: "",
  channel_count: "1",
  mic_spacing_m: "",
  reference_distance_m: "",
  reference_level_db: "",
  installed_at: "",
  notes: "",
  active: true,
};

function labelJenis(jenis?: string | null): string {
  if (!jenis) return "-";
  return JENIS_PERANGKAT[jenis] || jenis;
}

function angkaAtauNull(nilai: string): number | null {
  if (!nilai.trim()) return null;
  const angka = Number(nilai);
  return Number.isNaN(angka) ? null : angka;
}

export default function DevicesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [siteId, setSiteId] = useState("");
  const [statusAktif, setStatusAktif] = useState("");
  const [form, setForm] = useState<FormPerangkat>(FORM_KOSONG);
  const [idUbah, setIdUbah] = useState<number | null>(null);
  const [pesan, setPesan] = useState<string | null>(null);

  // Hanya admin yang boleh menulis; peran lain cukup melihat tabelnya.
  const bolehTulis = user?.role === "admin";

  const params: Record<string, string> = {};
  if (siteId) params.site_id = siteId;
  if (statusAktif) params.active = statusAktif;

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["devices", params],
    queryFn: () => api.getDevices(Object.keys(params).length > 0 ? params : undefined),
  });

  const { data: daftarSitus } = useQuery({ queryKey: ["sites"], queryFn: () => api.getSites() });
  const situs = daftarSitus ?? [];

  const perangkat = Array.isArray(data) ? data : [];

  const simpan = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      idUbah === null ? api.createDevice(payload) : api.updateDevice(idUbah, payload),
    onSuccess: () => {
      setPesan(idUbah === null ? "Perangkat baru tersimpan." : "Perubahan perangkat tersimpan.");
      setForm(FORM_KOSONG);
      setIdUbah(null);
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
    onError: (err) => setPesan((err as Error)?.message || "Gagal menyimpan perangkat."),
  });

  const hapus = useMutation({
    mutationFn: (id: number) => api.deleteDevice(id),
    onSuccess: () => {
      setPesan("Perangkat dihapus.");
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
    onError: (err) => setPesan((err as Error)?.message || "Gagal menghapus perangkat."),
  });

  const kirimForm = () => {
    setPesan(null);
    if (!form.name.trim()) {
      setPesan("Nama perangkat wajib diisi.");
      return;
    }
    if (!idUbah && !form.site_id) {
      setPesan("Lokasi perangkat wajib dipilih.");
      return;
    }
    if (form.mic_spacing_m.trim() && angkaAtauNull(form.mic_spacing_m) === null) {
      setPesan("Jarak mikrofon harus berupa angka, isi kosong kalau tidak diketahui.");
      return;
    }

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      type: form.type,
      active: form.active,
      channel_count: angkaAtauNull(form.channel_count) ?? 1,
    };
    if (form.site_id) payload.site_id = Number(form.site_id);
    payload.serial = form.serial.trim() || null;
    payload.mic_spacing_m = angkaAtauNull(form.mic_spacing_m);
    payload.reference_distance_m = angkaAtauNull(form.reference_distance_m);
    payload.reference_level_db = angkaAtauNull(form.reference_level_db);
    payload.installed_at = form.installed_at ? new Date(form.installed_at).toISOString() : null;
    payload.notes = form.notes.trim() || null;
    simpan.mutate(payload);
  };

  const mulaiUbah = (d: Perangkat) => {
    setIdUbah(d.id);
    setPesan(null);
    setForm({
      name: d.name || "",
      type: d.type || "audiomoth",
      site_id: String(d.site_id ?? ""),
      serial: d.serial || "",
      channel_count: String(d.channel_count ?? 1),
      mic_spacing_m: d.mic_spacing_m == null ? "" : String(d.mic_spacing_m),
      reference_distance_m:
        d.reference_distance_m == null ? "" : String(d.reference_distance_m),
      reference_level_db: d.reference_level_db == null ? "" : String(d.reference_level_db),
      installed_at: d.installed_at ? String(d.installed_at).slice(0, 10) : "",
      notes: d.notes || "",
      active: d.active !== false,
    });
  };

  const batalUbah = () => {
    setIdUbah(null);
    setForm(FORM_KOSONG);
    setPesan(null);
  };

  const aktifkan = useMutation({
    mutationFn: (id: number) => api.updateDevice(id, { active: true }),
    onSuccess: () => {
      setPesan("Perangkat diaktifkan kembali.");
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
    onError: (err) => setPesan((err as Error)?.message || "Gagal mengaktifkan perangkat."),
  });

  const konfirmasiHapus = (d: Perangkat) => {
    setPesan(null);
    const yakin = window.confirm(
      `Hapus perangkat ${d.name}? Perangkat yang masih dipakai rekaman tidak bisa dihapus.`
    );
    if (yakin) hapus.mutate(d.id);
  };

  const aktifkanUlang = (id: number) => aktifkan.mutate(id);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Perangkat perekam</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          {isLoading
            ? "Memuat perangkat"
            : `${perangkat.length} perangkat terdaftar. Geometri mikrofon dipakai untuk menghitung arah sumber suara.`}
        </p>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-[var(--muted-foreground)]">
          Filter lokasi
          <select
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
            className={inputClass}
            aria-label="Filter lokasi perangkat"
          >
            <option value="">Semua lokasi</option>
            {situs.map((s: Situs) => (
              <option key={s.id} value={String(s.id)}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-[var(--muted-foreground)]">
          Filter status
          <select
            value={statusAktif}
            onChange={(e) => setStatusAktif(e.target.value)}
            className={inputClass}
            aria-label="Filter status perangkat"
          >
            <option value="">Semua status</option>
            <option value="true">Aktif</option>
            <option value="false">Nonaktif</option>
          </select>
        </label>
      </div>

      {pesan && (
        <p role="status" className="mb-4 rounded border border-[var(--border)] bg-[var(--card)] p-3 text-sm text-[var(--foreground)]">
          {pesan}
        </p>
      )}

      {bolehTulis && (
        <section className="mb-8 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
          <h2 className="text-sm font-medium text-[var(--foreground)]">
            {idUbah === null ? "Tambah perangkat" : `Ubah perangkat #${idUbah}`}
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="text-xs text-[var(--muted-foreground)]">
              Nama
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className={inputClass}
                placeholder="Contoh: AM-01 Halimun"
                aria-label="Nama perangkat"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Jenis
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                className={inputClass}
                aria-label="Jenis perangkat"
              >
                <option value="audiomoth">AudioMoth</option>
                <option value="phone">Ponsel</option>
                <option value="other">Lainnya</option>
              </select>
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Lokasi
              <select
                value={form.site_id}
                onChange={(e) => setForm((f) => ({ ...f, site_id: e.target.value }))}
                className={inputClass}
                aria-label="Lokasi perangkat"
              >
                <option value="">Pilih lokasi</option>
                {situs.map((s: Situs) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Nomor seri
              <input
                value={form.serial}
                onChange={(e) => setForm((f) => ({ ...f, serial: e.target.value }))}
                className={inputClass}
                aria-label="Nomor seri"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Jumlah kanal
              <input
                type="number"
                min="1"
                step="1"
                value={form.channel_count}
                onChange={(e) => setForm((f) => ({ ...f, channel_count: e.target.value }))}
                className={inputClass}
                aria-label="Jumlah kanal"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Jarak antar mikrofon (meter)
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.mic_spacing_m}
                onChange={(e) => setForm((f) => ({ ...f, mic_spacing_m: e.target.value }))}
                className={inputClass}
                placeholder="Kosongkan kalau belum diukur"
                aria-label="Jarak antar mikrofon dalam meter"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Jarak acuan (meter)
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.reference_distance_m}
                onChange={(e) => setForm((f) => ({ ...f, reference_distance_m: e.target.value }))}
                className={inputClass}
                aria-label="Jarak acuan kalibrasi"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Level acuan (dB)
              <input
                type="number"
                step="0.1"
                value={form.reference_level_db}
                onChange={(e) => setForm((f) => ({ ...f, reference_level_db: e.target.value }))}
                className={inputClass}
                aria-label="Level acuan kalibrasi"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)]">
              Tanggal pemasangan
              <input
                type="date"
                value={form.installed_at}
                onChange={(e) => setForm((f) => ({ ...f, installed_at: e.target.value }))}
                className={inputClass}
                aria-label="Tanggal pemasangan"
              />
            </label>
            <label className="text-xs text-[var(--muted-foreground)] sm:col-span-2 lg:col-span-3">
              Catatan
              <textarea
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className={inputClass}
                rows={2}
                aria-label="Catatan perangkat"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--foreground)]">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
                className="h-5 w-5"
              />
              Perangkat aktif
            </label>
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={kirimForm}
              disabled={simpan.isPending}
              className="focus-ring inline-flex min-h-11 items-center justify-center rounded bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
            >
              {simpan.isPending ? "Menyimpan" : idUbah === null ? "Tambah perangkat" : "Simpan perubahan"}
            </button>
            {idUbah !== null && (
              <button
                type="button"
                onClick={batalUbah}
                className="focus-ring inline-flex min-h-11 items-center justify-center rounded border border-[var(--border)] px-4 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
              >
                Batal
              </button>
            )}
          </div>
        </section>
      )}

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat daftar perangkat."}
          onRetry={() => refetch()}
        />
      ) : perangkat.length === 0 ? (
        <EmptyState
          title="Belum ada perangkat"
          message={
            bolehTulis
              ? "Tambahkan perangkat lewat formulir di atas supaya asal rekaman tercatat."
              : "Belum ada perangkat yang cocok dengan filter ini. Minta admin menambahkannya."
          }
        />
      ) : (
        <>
          {/* Kartu untuk layar sempit, tabel untuk layar lebar. */}
          <ul className="space-y-3 md:hidden">
            {perangkat.map((d: Perangkat) => (
              <li key={d.id} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
                <p className="font-medium text-[var(--foreground)]">{d.name}</p>
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">
                  {d.site_name || "Lokasi belum diisi"}, {labelJenis(d.type)}
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <dt className="text-[var(--muted-foreground)]">Kanal</dt>
                    <dd className="text-[var(--foreground)]">{d.channel_count ?? 1}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--muted-foreground)]">Jarak mikrofon</dt>
                    <dd className="text-[var(--foreground)]">
                      {d.mic_spacing_m == null ? "Belum diukur" : `${d.mic_spacing_m} m`}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--muted-foreground)]">Status</dt>
                    <dd className={d.active === false ? "text-[var(--muted-foreground)]" : "text-[var(--accent)]"}>
                      {d.active === false ? "Nonaktif" : "Aktif"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--muted-foreground)]">Rekaman</dt>
                    <dd className="text-[var(--foreground)]">{d.recording_count ?? 0}</dd>
                  </div>
                </dl>
                {bolehTulis && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => mulaiUbah(d)}
                      className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                    >
                      Ubah
                    </button>
                    <button
                      type="button"
                      onClick={() => konfirmasiHapus(d)}
                      disabled={hapus.isPending}
                      className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--destructive)] px-3 text-sm text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
                    >
                      Hapus
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>

          <div className="hidden overflow-x-auto rounded-lg border border-[var(--border)] md:block">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Nama</th>
                  <th className="px-4 py-3 font-medium">Lokasi</th>
                  <th className="px-4 py-3 font-medium">Jenis</th>
                  <th className="px-4 py-3 font-medium">Kanal</th>
                  <th className="px-4 py-3 font-medium">Jarak mikrofon</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Rekaman</th>
                  {bolehTulis && <th className="px-4 py-3 font-medium">Aksi</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {perangkat.map((d: Perangkat) => (
                  <tr key={d.id} className="hover:bg-[var(--card-hover)]">
                    <td className="px-4 py-3 text-[var(--foreground)]">{d.name}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{d.site_name || "-"}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{labelJenis(d.type)}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{d.channel_count ?? 1}</td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {d.mic_spacing_m == null ? "Belum diukur" : `${d.mic_spacing_m} m`}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          d.active === false
                            ? "text-[var(--muted-foreground)]"
                            : "text-[var(--accent)]"
                        }
                      >
                        {d.active === false ? "Nonaktif" : "Aktif"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{d.recording_count ?? 0}</td>
                    {bolehTulis && (
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => mulaiUbah(d)}
                            className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                          >
                            Ubah
                          </button>
                          {d.active === false && (
                            <button
                              type="button"
                              onClick={() => aktifkanUlang(d.id)}
                              className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] px-3 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                            >
                              Aktifkan
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => konfirmasiHapus(d)}
                            disabled={hapus.isPending}
                            className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--destructive)] px-3 text-xs text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
                          >
                            Hapus
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!bolehTulis && (
        <p className="mt-4 text-xs text-[var(--muted-foreground)]">
          Menambah, mengubah, dan menghapus perangkat hanya bisa dilakukan admin.
        </p>
      )}

      {simpan.isPending && <Skeleton className="mt-4 h-4 w-32" />}
    </div>
  );
}
