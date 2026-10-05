"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatTanggal } from "@/lib/format";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui";

const LABEL_PERAN: Record<string, string> = {
  admin: "Admin",
  researcher: "Peneliti",
  ranger: "Petugas lapangan",
};

const KELAS_PERAN: Record<string, string> = {
  admin: "bg-[var(--primary-surface)] text-[var(--primary-text)] border-[var(--primary-text)]",
  researcher: "bg-[var(--muted)] text-[var(--highlight)] border-[var(--highlight)]",
  ranger: "bg-[var(--muted)] text-[var(--muted-foreground)] border-[var(--border)]",
};

function labelPeran(peran?: string | null): string {
  if (!peran) return "-";
  return LABEL_PERAN[peran] || peran;
}

export default function AdminUsersPage() {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const [pesan, setPesan] = useState<string | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [peringatan, setPeringatan] = useState<string | null>(null);

  const [tampilForm, setTampilForm] = useState(false);
  const [emailUndang, setEmailUndang] = useState("");
  const [namaUndang, setNamaUndang] = useState("");
  const [peranUndang, setPeranUndang] = useState("ranger");

  const admin = user?.role === "admin";

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.getUsers(),
    enabled: admin,
  });

  const daftar = Array.isArray(data) ? data : [];
  const jumlahAdmin = daftar.filter((u: any) => u.role === "admin").length;

  const ubahPeran = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => api.updateUserRole(id, role),
    onSuccess: () => {
      setGalat(null);
      setPesan("Peran akun diperbarui.");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setPesan(null);
      setGalat((err as Error)?.message || "Peran tidak bisa diubah.");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const hapusAkun = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onSuccess: () => {
      setGalat(null);
      setPesan("Akun dihapus.");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setPesan(null);
      setGalat((err as Error)?.message || "Akun tidak bisa dihapus.");
    },
  });

  const undangAkun = useMutation({
    mutationFn: (data: { email: string; name?: string; role: string }) => api.undangUser(data),
    onSuccess: (data: any) => {
      setGalat(null);
      setPeringatan(null);
      if (data?.email_terkirim === false) {
        setPesan(null);
        setPeringatan("Surel undangan tidak terkirim. Periksa pengaturan surel server, lalu kirim ulang.");
      } else {
        setPesan("Undangan terkirim. Petugas mengaktifkan akun lewat tautan di email.");
      }
      setTampilForm(false);
      setEmailUndang("");
      setNamaUndang("");
      setPeranUndang("ranger");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setPesan(null);
      setPeringatan(null);
      setGalat((err as Error)?.message || "Undangan tidak bisa dikirim.");
    },
  });

  const kirimUlang = useMutation({
    mutationFn: (id: number) => api.resendInvite(id),
    onSuccess: (data: any) => {
      setGalat(null);
      setPeringatan(null);
      if (data?.email_terkirim === false) {
        setPesan(null);
        setPeringatan("Surel undangan tidak terkirim. Periksa pengaturan surel server, lalu kirim ulang.");
      } else {
        setPesan("Undangan dikirim ulang.");
      }
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setPesan(null);
      setPeringatan(null);
      setGalat((err as Error)?.message || "Gagal kirim ulang undangan.");
    },
  });

  const kirimUndangan = (e: React.FormEvent) => {
    e.preventDefault();
    setGalat(null);
    undangAkun.mutate({ email: emailUndang, name: namaUndang, role: peranUndang });
  };

  const gantiPeran = (akun: any, peranBaru: string) => {
    if (peranBaru === akun.role) return;
    const yakin = window.confirm(
      `Ubah peran ${akun.email} dari ${labelPeran(akun.role)} menjadi ${labelPeran(peranBaru)}?`
    );
    if (!yakin) return;
    setGalat(null);
    ubahPeran.mutate({ id: akun.id, role: peranBaru });
  };

  const konfirmasiHapus = (akun: any) => {
    const yakin = window.confirm(
      `Hapus akun ${akun.email}? Akun yang masih punya rekaman atau lokasi tidak bisa dihapus.`
    );
    if (!yakin) return;
    setGalat(null);
    hapusAkun.mutate(akun.id);
  };

  const konfirmasiKirimUlang = (akun: any) => {
    const yakin = window.confirm(`Kirim ulang undangan ke ${akun.email}?`);
    if (!yakin) return;
    setGalat(null);
    kirimUlang.mutate(akun.id);
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <TableSkeleton rows={4} />
      </div>
    );
  }

  // Halaman ini hanya untuk admin. Peran lain tidak diberi tombol apa pun
  // karena API sudah pasti menolaknya.
  if (!admin) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <EmptyState
          title="Tidak berhak membuka halaman ini"
          message="Manajemen akun hanya bisa dibuka admin. Hubungi admin kalau peran akun Anda perlu diubah."
          action={
            <Link
              href="/dashboard"
              className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] bg-[var(--card)] px-4 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
            >
              Kembali ke dashboard
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">Manajemen akun</h1>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            {isLoading ? "Memuat akun" : `${daftar.length} akun terdaftar.`} Admin terakhir tidak bisa
            diturunkan, dan akun yang masih punya rekaman atau lokasi tidak bisa dihapus.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setTampilForm(!tampilForm)}
          className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] bg-[var(--card)] px-4 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--card-hover)]"
        >
          Tambah pengguna
        </button>
      </div>

      {tampilForm && (
        <form
          onSubmit={kirimUndangan}
          className="mb-6 grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 sm:grid-cols-[1fr_1fr_auto_auto]"
        >
          <div>
            <label htmlFor="undang-email" className="mb-1 block text-xs text-[var(--muted-foreground)]">
              Email
            </label>
            <input
              id="undang-email"
              type="email"
              required
              value={emailUndang}
              onChange={(e) => setEmailUndang(e.target.value)}
              className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>
          <div>
            <label htmlFor="undang-nama" className="mb-1 block text-xs text-[var(--muted-foreground)]">
              Nama
            </label>
            <input
              id="undang-nama"
              type="text"
              value={namaUndang}
              onChange={(e) => setNamaUndang(e.target.value)}
              className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>
          <div>
            <label htmlFor="undang-peran" className="mb-1 block text-xs text-[var(--muted-foreground)]">
              Peran
            </label>
            <select
              id="undang-peran"
              value={peranUndang}
              onChange={(e) => setPeranUndang(e.target.value)}
              className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="ranger">Petugas lapangan</option>
              <option value="researcher">Peneliti</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={undangAkun.isPending}
              className="focus-ring inline-flex min-h-11 items-center rounded bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
            >
              {undangAkun.isPending ? "Mengirim..." : "Kirim undangan"}
            </button>
          </div>
        </form>
      )}

      {pesan && (
        <p role="status" className="mb-4 rounded border border-[var(--border)] bg-[var(--card)] p-3 text-sm text-[var(--foreground)]">
          {pesan}
        </p>
      )}
      {peringatan && (
        <div role="alert" className="mb-4 rounded border border-amber-400 bg-amber-50 p-3">
          <p className="text-sm font-medium text-amber-800">Periksa pengaturan surel</p>
          <p className="mt-1 text-sm text-amber-900">{peringatan}</p>
        </div>
      )}
      {galat && (
        <div role="alert" className="mb-4 rounded border border-[var(--destructive)] bg-[var(--destructive-surface)] p-3">
          <p className="text-sm font-medium text-[var(--destructive)]">Permintaan ditolak</p>
          <p className="mt-1 text-sm text-[var(--foreground)]">{galat}</p>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat daftar akun."}
          onRetry={() => refetch()}
        />
      ) : daftar.length === 0 ? (
        <EmptyState
          title="Belum ada akun"
          message="Undang petugas lewat tombol Tambah pengguna di atas."
        />
      ) : (
        <>
          <ul className="space-y-3 lg:hidden">
            {daftar.map((akun: any) => {
              const diriSendiri = akun.id === user?.id;
              const adminTerakhir = akun.role === "admin" && jumlahAdmin === 1;
              const kunciPeran = diriSendiri || adminTerakhir;
              const menunggu = akun.is_active === false;
              return (
                <li key={akun.id} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
                  <p className="font-medium text-[var(--foreground)]">
                    {akun.name || akun.email?.split("@")[0] || "Tanpa nama"}
                  </p>
                  <p className="mt-1 break-all text-sm text-[var(--muted-foreground)]">{akun.email}</p>
                  <p className="mt-2 flex flex-wrap gap-2">
                    <span
                      className={`inline-flex rounded border px-2 py-0.5 text-xs font-medium ${
                        KELAS_PERAN[akun.role] || KELAS_PERAN.ranger
                      }`}
                    >
                      {labelPeran(akun.role)}
                    </span>
                    {menunggu && (
                      <span className="inline-flex rounded border border-[var(--border)] bg-[var(--muted)] px-2 py-0.5 text-xs font-medium text-[var(--muted-foreground)]">
                        Menunggu aktivasi
                      </span>
                    )}
                  </p>
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Rekaman</dt>
                      <dd className="text-[var(--foreground)]">{akun.recording_count ?? 0}</dd>
                    </div>
                    <div>
                      <dt className="text-[var(--muted-foreground)]">Lokasi</dt>
                      <dd className="text-[var(--foreground)]">{akun.site_count ?? 0}</dd>
                    </div>
                  </dl>
                  {menunggu && (
                    <button
                      type="button"
                      onClick={() => konfirmasiKirimUlang(akun)}
                      disabled={kirimUlang.isPending}
                      className="focus-ring mt-3 inline-flex min-h-11 items-center rounded border border-[var(--border)] bg-[var(--card)] px-3 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)] disabled:opacity-50"
                    >
                      Kirim ulang undangan
                    </button>
                  )}
                  <div className="mt-3">
                    <label className="text-xs text-[var(--muted-foreground)]">
                      Peran
                      <select
                        value={akun.role}
                        onChange={(e) => gantiPeran(akun, e.target.value)}
                        disabled={kunciPeran || ubahPeran.isPending}
                        className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
                        aria-label={`Peran akun ${akun.email}`}
                      >
                        <option value="ranger">Petugas lapangan</option>
                        <option value="researcher">Peneliti</option>
                        <option value="admin">Admin</option>
                      </select>
                    </label>
                    {kunciPeran && (
                      <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                        {diriSendiri
                          ? "Peran akun sendiri tidak bisa diubah dari sini."
                          : "Ini admin terakhir, perannya harus tetap admin."}
                      </p>
                    )}
                  </div>
                  {!diriSendiri && (
                    <button
                      type="button"
                      onClick={() => konfirmasiHapus(akun)}
                      disabled={hapusAkun.isPending}
                      className="focus-ring mt-3 inline-flex min-h-11 items-center rounded border border-[var(--destructive)] px-3 text-sm text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
                    >
                      Hapus akun
                    </button>
                  )}
                </li>
              );
            })}
          </ul>

          <div className="hidden overflow-x-auto rounded-lg border border-[var(--border)] lg:block">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Akun</th>
                  <th className="px-4 py-3 font-medium">Peran</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Dibuat</th>
                  <th className="px-4 py-3 font-medium">Rekaman</th>
                  <th className="px-4 py-3 font-medium">Lokasi</th>
                  <th className="px-4 py-3 font-medium">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {daftar.map((akun: any) => {
                  const diriSendiri = akun.id === user?.id;
                  const adminTerakhir = akun.role === "admin" && jumlahAdmin === 1;
                  const kunciPeran = diriSendiri || adminTerakhir;
                  const menunggu = akun.is_active === false;
                  return (
                    <tr key={akun.id} className="hover:bg-[var(--card-hover)]">
                      <td className="px-4 py-3">
                        <span className="block text-[var(--foreground)]">
                          {akun.name || akun.email?.split("@")[0] || "Tanpa nama"}
                        </span>
                        <span className="block break-all text-xs text-[var(--muted-foreground)]">
                          {akun.email}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded border px-2 py-0.5 text-xs font-medium ${
                            KELAS_PERAN[akun.role] || KELAS_PERAN.ranger
                          }`}
                        >
                          {labelPeran(akun.role)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[var(--foreground)]">
                        {menunggu ? "Menunggu aktivasi" : "Aktif"}
                      </td>
                      <td className="px-4 py-3 text-[var(--muted-foreground)]">
                        {formatTanggal(akun.created_at)}
                      </td>
                      <td className="px-4 py-3 text-[var(--foreground)]">
                        {akun.recording_count ?? 0}
                      </td>
                      <td className="px-4 py-3 text-[var(--foreground)]">{akun.site_count ?? 0}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          {menunggu && (
                            <button
                              type="button"
                              onClick={() => konfirmasiKirimUlang(akun)}
                              disabled={kirimUlang.isPending}
                              className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--border)] bg-[var(--card)] px-3 text-xs text-[var(--foreground)] hover:bg-[var(--card-hover)] disabled:opacity-50"
                            >
                              Kirim ulang undangan
                            </button>
                          )}
                          <select
                            value={akun.role}
                            onChange={(e) => gantiPeran(akun, e.target.value)}
                            disabled={kunciPeran || ubahPeran.isPending}
                            title={
                              kunciPeran
                                ? "Peran ini dikunci"
                                : `Ubah peran ${akun.email}`
                            }
                            className="rounded border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-xs text-[var(--foreground)] focus:border-[var(--ring)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
                            aria-label={`Peran akun ${akun.email}`}
                          >
                            <option value="ranger">Petugas lapangan</option>
                            <option value="researcher">Peneliti</option>
                            <option value="admin">Admin</option>
                          </select>
                          {!diriSendiri && (
                            <button
                              type="button"
                              onClick={() => konfirmasiHapus(akun)}
                              disabled={hapusAkun.isPending}
                              className="focus-ring inline-flex min-h-11 items-center rounded border border-[var(--destructive)] px-3 text-xs text-[var(--destructive)] hover:bg-[var(--destructive-surface)] disabled:opacity-50"
                            >
                              Hapus
                            </button>
                          )}
                        </div>
                        {kunciPeran && (
                          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                            {diriSendiri
                              ? "Akun sendiri, peran tidak bisa diubah"
                              : "Admin terakhir"}
                          </p>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
