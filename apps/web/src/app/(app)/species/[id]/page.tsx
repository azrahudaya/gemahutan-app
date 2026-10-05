"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton, TableSkeleton, EmptyState, ErrorState } from "@/components/ui";

const IUCN_LABEL: Record<string, string> = {
  LC: "Risiko rendah",
  NT: "Hampir terancam",
  VU: "Rentan",
  EN: "Terancam",
  CR: "Kritis",
};

const VERIFIED_LABEL: Record<string, string> = {
  correct: "Benar",
  incorrect: "Salah",
  uncertain: "Ragu",
  unverified: "Belum diverifikasi",
};

function formatTime(seconds?: number | null) {
  if (seconds == null) return "-";
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export default function SpeciesDetailPage() {
  const { id } = useParams<{ id: string }>();

  const {
    data: species,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["species", id],
    queryFn: () => api.getSpecies(id),
  });

  const { data: detections, isLoading: loadingDetections } = useQuery({
    queryKey: ["species-detections", id],
    queryFn: () => api.getSpeciesDetections(id, 50),
    enabled: Boolean(species),
  });

  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = user?.role === "admin";

  const setPrioritas = useMutation({
    mutationFn: (prioritas: boolean) => api.setSpeciesPrioritas(Number(id), prioritas),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["species", id] });
      queryClient.invalidateQueries({ queryKey: ["species"] });
    },
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <Skeleton className="mb-4 h-8 w-72" />
        <Skeleton className="mb-6 h-24 w-full" />
        <TableSkeleton rows={4} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <ErrorState
          message={(error as Error)?.message || "Tidak bisa memuat data spesies."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!species) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <EmptyState
          title="Spesies tidak ditemukan"
          message="Spesies ini tidak ada di basis data. Kembali ke daftar spesies untuk memilih yang lain."
          action={
            <Link
              href="/species"
              className="rounded border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)]"
            >
              Ke daftar spesies
            </Link>
          }
        />
      </div>
    );
  }

  const list = Array.isArray(detections) ? detections : [];
  const verifiedCount = list.filter((d: any) => d.verified_status === "correct").length;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link
        href="/species"
        className="mb-4 inline-block text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        Kembali ke daftar spesies
      </Link>

      <section className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">
          {species.scientific_name}
        </h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          {[species.common_name_id, species.common_name_en].filter(Boolean).join(", ") ||
            "nama umum belum ada di basis data"}
        </p>

        <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Status IUCN
            </dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {species.iucn_status
                ? `${species.iucn_status}, ${IUCN_LABEL[species.iucn_status] || "status tidak dikenal"}`
                : "-"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Prioritas
            </dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {species.prioritas ? "Ya" : "Tidak"}
              {species.sumber_prioritas ? ` (${species.sumber_prioritas})` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Threshold deteksi
            </dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {species.default_threshold ?? "-"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Total deteksi
            </dt>
            <dd className="mt-1 font-medium text-[var(--foreground)]">
              {species.detection_count ?? 0}
            </dd>
          </div>
        </dl>

        {isAdmin && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded border border-[var(--border)] bg-[var(--card)] p-3">
            <span className="text-sm text-[var(--foreground)]">Tandai spesies prioritas:</span>
            <button
              type="button"
              disabled={setPrioritas.isPending}
              onClick={() => setPrioritas.mutate(!species.prioritas)}
              className="rounded border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm text-[var(--foreground)] hover:bg-[var(--card-hover)] disabled:opacity-50"
            >
              {species.prioritas ? "Lepas prioritas" : "Tandai prioritas"}
            </button>
          </div>
        )}

        <p className="mt-4 text-xs text-[var(--muted-foreground)]">
          Threshold adalah ambang confidence yang dipakai worker untuk spesies ini. Angkanya
          hasil kalibrasi pada data validasi di ml/reports/thresholds.json, disalin ke database
          lewat make sync-thresholds, jadi yang tampil di sini sama dengan yang dipakai pipeline.
        </p>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">Deteksi terbaru</h2>
          {list.length > 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              {list.length} deteksi terakhir, {verifiedCount} ditandai benar oleh ahli
            </p>
          )}
        </div>

        {loadingDetections ? (
          <TableSkeleton rows={3} />
        ) : list.length === 0 ? (
          <EmptyState
            title="Belum pernah terdeteksi"
            message="Spesies ini belum muncul di rekaman mana pun. Naikkan jumlah rekaman atau turunkan threshold spesies ini."
          />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)] text-left text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Rekaman</th>
                  <th className="px-4 py-3 font-medium">Lokasi</th>
                  <th className="px-4 py-3 font-medium">Tanggal</th>
                  <th className="px-4 py-3 font-medium">Rentang waktu</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Status verifikasi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {list.map((d: any) => (
                  <tr key={d.detection_id} className="hover:bg-[var(--card-hover)]">
                    <td className="px-4 py-3">
                      <Link
                        href={`/recordings/${d.recording_id}`}
                        className="text-[var(--primary-text)] hover:underline"
                      >
                        Rekaman #{d.recording_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">{d.site_name || "-"}</td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {d.recorded_at ? new Date(d.recorded_at).toLocaleDateString("id-ID") : "-"}
                    </td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {formatTime(d.start_s)} sampai {formatTime(d.end_s)}
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {(d.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {VERIFIED_LABEL[d.verified_status] || d.verified_status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
