"use client";

import { Navbar } from "@/components/layout";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <Navbar>{children}</Navbar>;
}
