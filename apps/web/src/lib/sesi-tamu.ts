/**
 * Pastikan peramban punya token akun tamu untuk halaman depan. Token tamu lama
 * dipakai ulang supaya memuat ulang halaman tidak membuat akun tamu baru setiap
 * kali; kalau token itu sudah tidak berlaku, klien API menghapusnya dan halaman
 * dimuat ulang ke sini.
 *
 * Token tamu dan token petugas TIDAK boleh tercampur: sesi tamu ditandai dengan
 * `sesi_tamu`, dan fungsi ini tidak membuat sesi baru kalau peramban sudah
 * memegang token petugas.
 */
export const SESI_TAMU = "sesi_tamu";

export async function pastikanSesiTamu(): Promise<void> {
  const adaToken = Boolean(
    localStorage.getItem("access_token") && localStorage.getItem("refresh_token"),
  );
  if (adaToken) return; // sudah ada token (tamu atau petugas): jangan timpa.
  const res = await fetch("/sesi-demo", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || `Request failed: ${res.status}`);
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  localStorage.setItem(SESI_TAMU, "1");
}
