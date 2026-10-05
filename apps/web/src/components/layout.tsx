"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const SEMUA = ["admin", "researcher", "ranger"];
const ANALIS = ["admin", "researcher"];

const navItems = [
  { label: "Dasbor", href: "/dashboard", roles: ANALIS },
  { label: "Rekam", href: "/rekam", roles: SEMUA },
  { label: "Unggah", href: "/upload", roles: SEMUA },
  { label: "Rekaman", href: "/recordings", roles: SEMUA },
  { label: "Simulasi", href: "/simulasi", roles: SEMUA },
  { label: "Lokasi", href: "/sites", roles: ANALIS },
  { label: "Spesies", href: "/species", roles: ANALIS },
  { label: "Perangkat", href: "/devices", roles: ANALIS },
  { label: "Model", href: "/model", roles: ANALIS },
  { label: "Laporan", href: "/laporan", roles: ANALIS },
  { label: "Dokumentasi", href: "/dokumentasi", roles: SEMUA },
  { label: "Pengguna", href: "/admin/users", roles: ["admin"] },
];

// Jalur aplikasi yang dibatasi peran. Yang tidak disebut bebas untuk semua peran.
const ROLES_PER_PATH: Array<{ prefix: string; roles: string[] }> = [
  { prefix: "/admin", roles: ["admin"] },
  { prefix: "/dashboard", roles: ANALIS },
  { prefix: "/sites", roles: ANALIS },
  { prefix: "/species", roles: ANALIS },
  { prefix: "/devices", roles: ANALIS },
  { prefix: "/model", roles: ANALIS },
  { prefix: "/laporan", roles: ANALIS },
];

function tujuanPeran(role: string | undefined): string {
  return role === "ranger" ? "/rekam" : "/dashboard";
}

function labelItem(item: { label: string; href: string }, role: string | undefined): string {
  if (item.href === "/recordings" && role === "ranger") return "Rekamanku";
  return item.label;
}

/** Status pipeline dari heartbeat worker, bukan label statis. */
function PipelineStatus() {
  const { data, isLoading } = useQuery({
    queryKey: ["model-info"],
    queryFn: () => api.getModelInfo(),
    refetchInterval: 60000,
  });

  if (isLoading || !data) {
    return <span className="text-xs text-base-content/70">Memeriksa pipeline</span>;
  }

  const alive = Boolean(data.worker_alive);
  return (
    <span
      className="flex items-center gap-2 text-xs text-base-content/70"
      title={data.status_detail || undefined}
    >
      <span
        className={`h-2 w-2 rounded-full ${alive ? "bg-success" : "bg-error"}`}
        aria-hidden="true"
      />
      {alive ? "Pemrosesan aktif" : "Pemrosesan tidak aktif"}
    </span>
  );
}

export function Navbar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, loading, logout, user } = useAuth();
  const initials = (user?.email || "?").slice(0, 2).toUpperCase();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const menuItems = navItems.filter((item) => item.roles.includes(user?.role ?? ""));

  // Peran tidak boleh membuka halaman di luar daftar menunya. Diarahkan ke
  // halaman awal perannya, bukan menampilkan galat API.
  useEffect(() => {
    if (loading || !user) return;
    const aturan = ROLES_PER_PATH.find(
      (r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`)
    );
    if (aturan && !aturan.roles.includes(user.role)) {
      router.replace(tujuanPeran(user.role));
    }
  }, [loading, user, pathname, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-base-100">
        <span className="loading loading-spinner loading-lg text-primary" />
      </div>
    );
  }

  if (!isAuthenticated && pathname !== "/login") {
    router.push("/login");
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-base-100 text-base-content">
      {/* Navigation Rail (Desktop) */}
      <aside className="fixed left-0 top-0 z-50 hidden h-screen w-64 border-r border-base-300 bg-base-100 p-4 lg:block">
        {/* Logo */}
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary text-xs font-bold text-primary-content">
            GH
          </div>
          <div>
            <span className="text-sm font-semibold">GemaHutan</span>
            <p className="text-xs text-base-content/70">Pemantauan satwa lewat suara</p>
          </div>
        </div>

        {/* Navigation */}
        <ul className="menu w-full gap-1">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={isActive ? "active" : ""}
                >
                  {labelItem(item, user?.role)}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* User Profile */}
        <div className="mt-auto border-t border-base-300 pt-6">
          <div className="mb-4 flex items-center gap-3 px-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-content">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {user?.email ? user.email.split("@")[0] : "Memuat akun"}
              </p>
              <p className="truncate text-xs text-base-content/70">
                {user?.email || "belum ada sesi"} {user?.role ? `, peran ${user.role}` : ""}
              </p>
            </div>
          </div>
          <button onClick={logout} className="btn btn-outline btn-sm w-full">
            Keluar
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-base-300 bg-base-100 px-6">
          <div className="flex items-center gap-4 lg:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label={isMobileMenuOpen ? "Tutup menu navigasi" : "Buka menu navigasi"}
              aria-expanded={isMobileMenuOpen}
              className="btn btn-ghost btn-circle"
            >
              {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span className="font-semibold">GemaHutan</span>
          </div>
          <div className="flex-1" />
          <div className="hidden items-center gap-2 md:flex">
            <PipelineStatus />
          </div>
        </header>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-50 border-r border-base-300 bg-base-100 p-4 lg:hidden">
            <div className="mb-6 flex items-center justify-between">
              <span className="font-semibold">GemaHutan</span>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                aria-label="Tutup menu navigasi"
                className="btn btn-ghost btn-circle"
              >
                <X size={20} />
              </button>
            </div>
            <ul className="menu w-full gap-1">
              {menuItems.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} onClick={() => setIsMobileMenuOpen(false)}>
                    {labelItem(item, user?.role)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Content */}
        <main className="min-w-0 flex-1 overflow-y-auto p-6 lg:p-8">{children}</main>

        {/* Footer */}
        <footer className="border-t border-base-300 bg-base-100 py-6">
          <div className="mx-auto max-w-7xl px-6 text-center text-xs text-base-content/70">
            <p>GemaHutan, pemantauan satwa hutan Indonesia lewat suara.</p>
          </div>
        </footer>
      </div>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-base-300 bg-base-100 py-6">
      <div className="mx-auto max-w-7xl px-6 text-center text-xs text-base-content/70">
        <p>GemaHutan, pemantauan satwa hutan Indonesia lewat suara.</p>
      </div>
    </footer>
  );
}
