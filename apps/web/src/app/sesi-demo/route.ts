import { NextResponse, type NextRequest } from "next/server";

// Membuat akun tamu baru untuk satu pengunjung halaman depan. Rahasia server web
// (TAMU_RAHASIA) dibaca saat permintaan masuk dan tidak pernah dikirim ke peramban;
// peramban hanya menerima token akun tamunya sendiri.
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  if (process.env.DEMO_AKTIF !== "1") {
    return NextResponse.json({ detail: "Mode demo tidak aktif." }, { status: 404 });
  }
  const rahasia = process.env.TAMU_RAHASIA;
  if (!rahasia) {
    return NextResponse.json({ detail: "Akun tamu belum diatur. Isi TAMU_RAHASIA di .env." }, { status: 500 });
  }

  // Caddy menaruh IP pengunjung di X-Forwarded-For; API memakainya untuk membatasi
  // jumlah sesi baru per jaringan.
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "";
  const apiInternal = process.env.API_INTERNAL_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiInternal}/api/v1/auth/tamu`, {
      method: "POST",
      headers: { "x-tamu-rahasia": rahasia, "x-pengunjung-ip": ip },
      cache: "no-store",
    });
    if (res.status === 429) {
      return NextResponse.json({ detail: "Terlalu banyak sesi baru dari jaringan ini. Coba lagi nanti." }, { status: 429 });
    }
    if (!res.ok) {
      return NextResponse.json({ detail: "Server menolak membuat sesi tamu." }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ access_token: data.access_token, refresh_token: data.refresh_token });
  } catch {
    return NextResponse.json(
      { detail: "Server analisis belum menyala. Jalankan docker compose up -d lalu muat ulang." },
      { status: 503 }
    );
  }
}
