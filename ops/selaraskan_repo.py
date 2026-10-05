"""Selaraskan repo dataset HF dengan folder lokal: hapus berkas yang tidak ada di lokal.

Dipakai setelah pembersihan lisensi ND dan penormalan nama berkas. Berkas yang
sudah dihapus di sisi lokal harus ikut hilang di repo, kalau tidak repo tetap
memuat klip berlisensi ND dan klaim "data bersih ND" jadi salah.

Jalankan di VPS:
    python3 /opt/staging/selaraskan_repo.py <repo_id> <folder_lokal> [--dry-run]
"""

import sys
from pathlib import Path

from huggingface_hub import CommitOperationDelete, HfApi


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return

    repo = sys.argv[1]
    folder = Path(sys.argv[2])
    dry = "--dry-run" in sys.argv

    if not folder.exists():
        print("folder lokal tidak ada:", folder)
        return

    lokal = {
        str(p.relative_to(folder))
        for p in folder.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    }

    api = HfApi()
    info = api.dataset_info(repo)
    repo_files = {
        s.rfilename
        for s in (info.siblings or [])
        if not s.rfilename.startswith(".")
    }

    # Hanya berkas audio yang dihapus. README, metadata, dan berkas repo lain
    # dibiarkan, karena tujuan skrip ini menghapus klip yang tidak lolos filter
    # lisensi, bukan membersihkan dokumentasi repo.
    hapus = sorted(
        n for n in (repo_files - lokal) if n.lower().endswith((".wav", ".mp3", ".flac", ".ogg"))
    )
    print("repo            :", repo)
    print("berkas di repo  :", len(repo_files))
    print("berkas di lokal :", len(lokal))
    print("harus dihapus   :", len(hapus))
    for n in hapus[:10]:
        print("   -", n)
    if len(hapus) > 10:
        print("   ... dan", len(hapus) - 10, "lagi")

    if not hapus:
        print("repo sudah selaras")
        return
    if dry:
        print("dry run, tidak menghapus")
        return

    # HuggingFace membatasi jumlah operasi per commit, jadi dipecah per 500.
    for awal in range(0, len(hapus), 500):
        potongan = hapus[awal : awal + 500]
        api.create_commit(
            repo_id=repo,
            repo_type="dataset",
            operations=[CommitOperationDelete(path_in_repo=p) for p in potongan],
            commit_message=f"Hapus berkas yang tidak lolos filter lisensi ND (bagian {awal // 500 + 1})",
        )
        print("hapus bagian", awal // 500 + 1, ":", len(potongan), "berkas")

    print("selesai, total dihapus:", len(hapus))


if __name__ == "__main__":
    main()
