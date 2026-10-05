import { labelTahap, normalisasiProgres } from "@/lib/format";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="card border border-base-300 bg-base-100">
      <div className="card-body">
        <Skeleton className="mb-2 h-4 w-24" />
        <Skeleton className="h-8 w-16" />
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title?: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card border border-dashed border-base-300 bg-base-100">
      <div className="card-body items-center py-16 text-center">
        {title ? <p className="text-base font-medium text-base-content">{title}</p> : null}
        <p className="max-w-md text-sm text-base-content/70">{message}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  );
}

export function ErrorState({
  title = "Gagal memuat data",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="alert alert-error">
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-sm text-base-content">{message}</p>
        {onRetry ? (
          <button onClick={onRetry} className="btn btn-outline btn-sm mt-3">
            Coba lagi
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="card border border-base-300 bg-base-100">
      <div className="card-body p-5">
        <p className="text-xs uppercase tracking-wide text-base-content/60">{label}</p>
        <p className="mt-2 text-2xl font-semibold text-base-content">{value}</p>
        {hint ? <p className="mt-1 text-xs text-base-content/70">{hint}</p> : null}
      </div>
    </div>
  );
}

export function Button({
  className = "",
  variant = "primary",
  children,
  onClick,
  ...props
}: {
  className?: string;
  variant?: "primary" | "secondary";
  children: React.ReactNode;
  onClick?: () => void;
  [key: string]: unknown;
}) {
  const variants = {
    primary: "btn-primary",
    secondary: "btn-outline",
  };

  return (
    <button className={`btn ${variants[variant]} ${className}`} onClick={onClick} {...props}>
      {children}
    </button>
  );
}

/**
 * Bilah progres. Nilainya dijepit dan dibulatkan di satu tempat supaya semua
 * halaman melaporkan angka yang sama dengan yang diucapkan pembaca layar.
 */
export function ProgressBar({
  value,
  label,
  className = "",
}: {
  value?: number | null;
  label?: string;
  className?: string;
}) {
  const persen = normalisasiProgres(value);
  return (
    <div className={className}>
      <progress
        className="progress progress-primary w-full"
        value={persen}
        max={100}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={persen}
        aria-label={label || "Progres pemrosesan"}
      />
      {label ? (
        <p className="mt-1 text-xs text-base-content/70">
          {label}: {persen}%
        </p>
      ) : null}
    </div>
  );
}

/** Penanda tahap pipeline. Warna dibedakan tanpa mengandalkan warna saja. */
export function StageBadge({ stage }: { stage?: string | null }) {
  const nada =
    stage === "gagal"
      ? "badge-error"
      : stage === "selesai"
        ? "badge-success"
        : "badge-ghost";
  return <span className={`badge ${nada}`}>{labelTahap(stage)}</span>;
}

/** Penanda sementara untuk kejadian yang baru saja terjadi, misalnya job selesai. */
export function Toast({
  message,
  tone = "info",
  onClose,
}: {
  message: string;
  tone?: "info" | "sukses" | "galat";
  onClose: () => void;
}) {
  const nada = tone === "sukses" ? "alert-success" : tone === "galat" ? "alert-error" : "";
  return (
    <div
      role="status"
      aria-live="polite"
      className={`alert fixed bottom-4 left-4 right-4 z-50 w-auto shadow-lg sm:left-auto sm:right-6 sm:max-w-md ${nada}`}
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onClose}
        aria-label="Tutup pemberitahuan"
        className="btn btn-ghost btn-sm"
      >
        Tutup
      </button>
    </div>
  );
}
