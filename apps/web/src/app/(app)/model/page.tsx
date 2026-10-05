"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ModelInfo } from "@/lib/api";
import { Skeleton, EmptyState, ErrorState } from "@/components/ui";

export default function ModelPage() {
  const { data, isLoading, isError, error, refetch } = useQuery<ModelInfo>({
    queryKey: ["model-info-page"],
    queryFn: () => api.getModelInfo(),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="mb-6 h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <ErrorState
          title="Informasi model tidak bisa dimuat"
          message={(error as Error)?.message || "Endpoint /api/v1/model/info tidak menjawab."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const tracks = data.tracks || [];
  const ambang = data.thresholds || {};
  const jumlahAmbang = Object.keys(ambang).filter((k) => k !== "_negative").length;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--foreground)]">Status Model</h1>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Apa yang sebenarnya dipakai pipeline, dan sampai mana cakupannya. Angka di halaman
          ini dibaca dari berkas laporan dan heartbeat worker, bukan ditulis manual.
        </p>
      </div>

      <div className="mb-6 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm font-medium ${
              data.worker_alive
                ? "bg-[var(--primary-surface)] text-[var(--accent)]"
                : "bg-[var(--destructive-surface)] text-[var(--destructive)]"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                data.worker_alive ? "bg-[var(--accent)]" : "bg-[var(--destructive)]"
              }`}
              aria-hidden="true"
            />
            {data.worker_alive ? "Worker aktif" : "Worker tidak aktif"}
          </span>
          <span className="text-sm text-[var(--muted-foreground)]">
            Mesin aktif: {data.engine || "belum diketahui"}
          </span>
        </div>
        {data.status_detail && (
          <p className="mt-3 text-sm text-[var(--muted-foreground)]">{data.status_detail}</p>
        )}
        {data.worker_heartbeat_age_s != null && (
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
            Heartbeat terakhir {Math.round(data.worker_heartbeat_age_s)} detik lalu
          </p>
        )}
      </div>

      <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">Dua jalur deteksi</h2>
      {tracks.length === 0 ? (
        <EmptyState message="Belum ada informasi jalur model dari API." />
      ) : (
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          {tracks.map((t) => (
            <div key={t.id} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-medium text-[var(--foreground)]">{t.name}</h3>
                <span className="text-xs text-[var(--muted-foreground)]">jalur {t.id}</span>
              </div>
              <dl className="mt-3 space-y-1 text-sm">
                {t.version && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-[var(--muted-foreground)]">Versi</dt>
                    <dd className="text-[var(--foreground)]">{t.version}</dd>
                  </div>
                )}
                {t.species_count != null && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-[var(--muted-foreground)]">Cakupan spesies</dt>
                    <dd className="text-[var(--foreground)]">{t.species_count}</dd>
                  </div>
                )}
                {t.macro_f1 != null && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-[var(--muted-foreground)]">Macro F1 uji</dt>
                    <dd className="text-[var(--foreground)]">{t.macro_f1.toFixed(4)}</dd>
                  </div>
                )}
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--muted-foreground)]">Dimuat worker</dt>
                  <dd className="text-[var(--foreground)]">
                    {t.loaded_by_worker ? "ya" : "tidak"}
                  </dd>
                </div>
              </dl>
              {t.role && (
                <p className="mt-3 text-xs text-[var(--muted-foreground)]">{t.role}</p>
              )}
              {t.notes && <p className="mt-2 text-xs text-[var(--muted-foreground)]">{t.notes}</p>}
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">Ambang keputusan</h2>
      <div className="mb-6 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
        <p className="text-sm text-[var(--foreground)]">
          {jumlahAmbang} spesies punya ambang hasil kalibrasi. Ambang ini yang dipakai worker
          untuk memutuskan sebuah deteksi ditampilkan atau tidak.
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-[var(--muted-foreground)]">
              <tr>
                <th className="py-2 font-medium">Spesies</th>
                <th className="py-2 font-medium">Ambang</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {Object.entries(ambang)
                .filter(([nama]) => nama !== "_negative")
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([nama, nilai]) => (
                  <tr key={nama}>
                    <td className="py-2 text-[var(--foreground)]">{nama}</td>
                    <td className="py-2 text-[var(--muted-foreground)]">{nilai}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {Array.isArray(data.limits) && data.limits.length > 0 && (
        <>
          <h2 className="mb-3 text-lg font-semibold text-[var(--foreground)]">Batas yang diketahui</h2>
          <ul className="list-disc space-y-1 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5 pl-8 text-sm text-[var(--muted-foreground)]">
            {data.limits.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-6 text-xs text-[var(--muted-foreground)]">
        Rincian evaluasi: ml/reports/eval.md, ml/reports/field_eval.md, ml/reports/field_experiments.md.
        Peta ambang yang dipakai aplikasi disamakan dengan hasil kalibrasi lewat make sync-thresholds.
      </p>
    </div>
  );
}
