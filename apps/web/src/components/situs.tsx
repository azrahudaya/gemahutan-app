"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight, AudioLines, Menu } from "lucide-react";

/*
 * Kepala dan kaki halaman yang dipakai bersama oleh halaman depan dan dokumentasi.
 * `awalan` mengarahkan tautan bagian: "" di halaman depan, "/" dari halaman lain.
 */

export const GITHUB = "https://github.com/azrahudaya/gemahutan";

const BAGIAN = [
  { href: "#cara-kerja", label: "Cara kerja" },
  { href: "#untuk-siapa", label: "Untuk siapa" },
  { href: "#simulasi", label: "Simulasi" },
];

export function KepalaSitus({ aksi, docsAktif = false, tentangAktif = false }: { aksi: ReactNode; docsAktif?: boolean; tentangAktif?: boolean }) {
  const [tergulir, setTergulir] = useState(false);

  // Bayangan pil sedikit menebal setelah halaman digulir.
  useEffect(() => {
    const cek = () => setTergulir(window.scrollY > 8);
    cek();
    window.addEventListener("scroll", cek, { passive: true });
    return () => window.removeEventListener("scroll", cek);
  }, []);

  const tutupMenu = () => (document.getElementById("menu-hp") as HTMLElement & { hidePopover?: () => void })?.hidePopover?.();

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6">
      <nav
        data-gulir={tergulir}
        className="navbar mx-auto min-h-14 max-w-5xl rounded-full border border-base-300 bg-base-100/95 px-2 shadow-sm transition-shadow data-[gulir=true]:shadow-md sm:px-3"
        aria-label="Navigasi utama"
      >
        <div className="navbar-start">
          <Link href="/" className="flex items-center gap-2 pl-2 text-lg font-bold tracking-tight text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            <AudioLines className="size-6 text-primary" aria-hidden="true" />
            GemaHutan
          </Link>
        </div>
        <div className="navbar-center hidden lg:flex">
          <ul className="menu menu-horizontal gap-1 text-base-content">
            <li>
              <Link href="/tentang" aria-current={tentangAktif ? "page" : undefined} className={tentangAktif ? "rounded-full bg-secondary font-semibold text-secondary-content hover:text-secondary-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid" : "rounded-full text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid"}>
                Tentang
              </Link>
            </li>
            <li>
              <Link href="/dokumentasi" aria-current={docsAktif ? "page" : undefined} className={docsAktif ? "rounded-full bg-secondary font-semibold text-secondary-content hover:text-secondary-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid" : "rounded-full text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid"}>
                Docs
              </Link>
            </li>
            <li>
              <a href={GITHUB} target="_blank" rel="noreferrer" className="rounded-full text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                GitHub
                <ArrowUpRight className="size-3.5" aria-hidden="true" />
                <span className="sr-only">(membuka tab baru)</span>
              </a>
            </li>
          </ul>
        </div>
        <div className="navbar-end gap-1">
          {aksi}
          <Link href="/login" className="btn btn-primary btn-sm rounded-full hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            Masuk
          </Link>
          <button type="button" className="btn btn-ghost btn-sm btn-circle [anchor-name:--menu-hp] lg:hidden" popoverTarget="menu-hp" aria-label="Buka menu">
            <Menu className="size-5" aria-hidden="true" />
          </button>
          <ul
            className="dropdown dropdown-end menu z-40 mt-2 w-56 rounded-box bg-base-100 p-2 text-base-content shadow-lg [position-anchor:--menu-hp]"
            popover="auto"
            id="menu-hp"
          >
            <li>
              <Link href="/tentang" onClick={tutupMenu} aria-current={tentangAktif ? "page" : undefined} className="text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                Tentang
              </Link>
            </li>
            <li>
              <Link href="/dokumentasi" onClick={tutupMenu} className="text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                Docs
              </Link>
            </li>
            <li>
              <a href={GITHUB} target="_blank" rel="noreferrer" className="text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
                GitHub
                <ArrowUpRight className="size-3.5" aria-hidden="true" />
                <span className="sr-only">(membuka tab baru)</span>
              </a>
            </li>
          </ul>
        </div>
      </nav>
    </header>
  );
}

export function KakiSitus({ awalan = "" }: { awalan?: string }) {
  return (
    <footer className="border-t border-base-300 bg-base-200">
      <div className="footer mx-auto max-w-6xl px-4 py-12 max-sm:grid-cols-2 max-sm:gap-x-4 sm:footer-horizontal sm:px-6">
        <div className="max-w-xs max-sm:col-span-2">
          <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <AudioLines className="size-6 text-primary" aria-hidden="true" />
            GemaHutan
          </span>
          <p className="text-base-content/70">Pantau satwa hutan lewat suara.</p>
        </div>
        <nav aria-label="Bagian halaman depan">
          <h2 className="footer-title">Halaman</h2>
          {BAGIAN.map((t) => (
            <a key={t.href} href={`${awalan}${t.href}`} className="link link-hover py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
              {t.label}
            </a>
          ))}
        </nav>
        <nav aria-label="Sumber">
          <h2 className="footer-title">Sumber</h2>
          <Link href="/dokumentasi" className="link link-hover py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            Dokumentasi
          </Link>
          <a href={GITHUB} target="_blank" rel="noreferrer" className="link link-hover inline-flex items-center gap-1 py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            GitHub
            <ArrowUpRight className="size-3.5" aria-hidden="true" />
            <span className="sr-only">(membuka tab baru)</span>
          </a>
        </nav>
        <nav aria-label="Tentang GemaHutan" className="max-sm:col-span-2">
          <h2 className="footer-title">Tentang</h2>
          <Link href="/tentang" className="link link-hover py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            Tentang GemaHutan
          </Link>
          <Link href="/tentang#tim" className="link link-hover py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            Tim
          </Link>
          <Link href="/tentang#sumber" className="link link-hover py-1 text-base-content hover:text-base-content hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">
            Data dan teknologi
          </Link>
        </nav>
      </div>
      <div className="border-t border-base-300">
        <p className="mx-auto max-w-6xl px-4 py-5 text-sm text-base-content/70 sm:px-6">© 2026 GemaHutan</p>
      </div>
    </footer>
  );
}
