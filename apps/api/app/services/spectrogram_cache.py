"""Kunci dan lokasi cache spektrogram.

Sebelum ini setiap permintaan spektrogram mengunduh audio dari MinIO lalu
merender ulang gambar dengan matplotlib. Terukur 0,29 detik dan 250 KB per
permintaan, dan halaman dengan sepuluh rekaman berarti sepuluh kali kerja
identik.

Berkas audio tidak pernah berubah setelah diunggah: unggahan baru selalu
mendapat kunci objek baru. Jadi hasil render bisa disimpan di MinIO dengan
kunci turunan dari kunci audio, dan tidak perlu invalidasi manual.
"""
CACHE_PREFIX = "cache/spectrogram"


def cache_spectrogram_key(storage_key: str) -> str:
    return f"{CACHE_PREFIX}/{storage_key}.png"
