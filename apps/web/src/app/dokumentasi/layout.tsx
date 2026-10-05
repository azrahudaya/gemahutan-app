import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dokumentasi",
  description: "Cara memakai GemaHutan, membaca hasil, cara kerja model, dan batasannya.",
};

export default function LayoutDokumentasi({ children }: { children: React.ReactNode }) {
  return children;
}
