"""Hapus berkas duplikat berekstensi ganda dari repo dataset HuggingFace.

Batch unggahan pertama pada repo iNatSounds memakai nama dari metadata apa
adanya, sehingga ekstensi .wav tertulis dua kali. Setelah nama berkas
dinormalkan di sisi lokal, versi lama masih tertinggal di repo dan harus
dibuang supaya tidak ada dua salinan audio yang sama dengan nama berbeda.

Jalankan di VPS: python3 /opt/staging/hapus_duplikat.py [--dry-run]
"""

import sys

from huggingface_hub import CommitOperationDelete, HfApi


def main() -> None:
    repo = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") \
        else "azrahudaya/gemahutan-inatsounds-neg"
    pola = sys.argv[2] if len(sys.argv) > 2 else ".wav.wav"

    api = HfApi()
    info = api.dataset_info(repo)
    nama = [s.rfilename for s in (info.siblings or [])]
    hapus = [n for n in nama if n.endswith(pola)]

    print("repo                 :", repo)
    print("pola                 :", pola)
    print("total berkas di repo :", len(nama))
    print("kandidat dihapus     :", len(hapus))

    if not hapus:
        print("tidak ada yang perlu dihapus")
        return

    if "--dry-run" in sys.argv:
        print("dry run, tidak menghapus apa pun")
        return

    api.create_commit(
        repo_id=repo,
        repo_type="dataset",
        operations=[CommitOperationDelete(path_in_repo=p) for p in hapus],
        commit_message="Hapus berkas duplikat dengan ekstensi wav ganda",
    )
    print("hapus selesai:", len(hapus), "berkas")


if __name__ == "__main__":
    main()
