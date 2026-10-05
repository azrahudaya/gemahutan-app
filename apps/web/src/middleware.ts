import { NextResponse, type NextRequest } from "next/server";

/*
 * Pendaftaran mandiri ditutup di produksi. Halaman /register tidak ada lagi,
 * jadi jalur ini dialihkan ke halaman masuk.
 */
export function middleware(request: NextRequest) {
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/register/:path*"],
};
