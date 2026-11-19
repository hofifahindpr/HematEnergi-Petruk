"""Modul storage: membaca dan menyimpan data HematEnergi ke file.

- pemakaian.csv   : riwayat pemakaian (CSV)
- pengaturan.json : tarif dan target (JSON)
Semua operasi file memakai `with open()`. Kegagalan file ditangani di sini
agar aplikasi tidak langsung tertutup.
"""
import csv
import json
import os

from models import KOLOM_CSV, CatatanPemakaian, PengaturanAplikasi

FOLDER_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JALUR_CSV = os.path.join(FOLDER_DATA, "pemakaian.csv")
JALUR_JSON = os.path.join(FOLDER_DATA, "pengaturan.json")


class PenyimpananError(Exception):
    """Error yang dilempar bila file tidak bisa dibaca atau ditulis.

    Pesannya sudah ramah pengguna dan siap ditampilkan di UI.
    """


def _tulis_header(jalur):
    """Tulis baris judul kolom ke file CSV (mode 'w')."""
    with open(jalur, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=KOLOM_CSV).writeheader()


def siapkan_file(jalur=JALUR_CSV):
    """Pastikan file CSV ada dan berisi header.

    Mode 'x' membuat file baru; bila file sudah ada (FileExistsError)
    dan ternyata kosong, header ditulis ulang.
    """
    try:
        os.makedirs(os.path.dirname(jalur), exist_ok=True)
        try:
            with open(jalur, "x", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=KOLOM_CSV).writeheader()
        except FileExistsError:
            if os.path.getsize(jalur) == 0:
                _tulis_header(jalur)
    except OSError as galat:
        raise PenyimpananError(f"Gagal menyiapkan file data: {galat}")


def muat_catatan(jalur=JALUR_CSV):
    """Baca semua catatan dari CSV (mode 'r').

    Returns:
        (daftar_catatan, jumlah_baris_rusak)
    File tidak ada -> ([], 0). Baris yang tidak valid dilewati dan dihitung.

    Raises:
        PenyimpananError: jika file ada tetapi tidak bisa dibaca.
    """
    daftar, rusak = [], 0
    try:
        with open(jalur, "r", newline="", encoding="utf-8") as f:
            for baris in csv.DictReader(f):
                try:
                    daftar.append(CatatanPemakaian.dari_baris(baris))
                except ValueError:
                    rusak += 1
    except FileNotFoundError:
        return [], 0
    except (OSError, UnicodeDecodeError, csv.Error) as galat:
        raise PenyimpananError(f"File data tidak dapat dibaca: {galat}")
    return daftar, rusak


def simpan_semua(daftar, jalur=JALUR_CSV):
    """Tulis ulang seluruh catatan ke CSV (mode 'w').

    Dipakai setelah mengedit atau menghapus catatan.
    """
    try:
        os.makedirs(os.path.dirname(jalur), exist_ok=True)
        with open(jalur, "w", newline="", encoding="utf-8") as f:
            penulis = csv.DictWriter(f, fieldnames=KOLOM_CSV)
            penulis.writeheader()
            for catatan in daftar:
                penulis.writerow(catatan.ke_baris())
    except OSError as galat:
        raise PenyimpananError(f"Gagal menyimpan data: {galat}")


def tambah_catatan(catatan, jalur=JALUR_CSV):
    """Tambahkan satu catatan di akhir CSV (mode 'a') tanpa menulis ulang."""
    siapkan_file(jalur)
    try:
        with open(jalur, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=KOLOM_CSV).writerow(catatan.ke_baris())
    except OSError as galat:
        raise PenyimpananError(f"Gagal menambah data: {galat}")


def muat_pengaturan(jalur=JALUR_JSON):
    """Baca tarif dan target dari JSON (mode 'r').

    File hilang, kosong, atau rusak -> pengaturan bawaan (tarif 1500, target 0).
    """
    try:
        with open(jalur, "r", encoding="utf-8") as f:
            return PengaturanAplikasi.dari_dict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, ValueError,
            TypeError, AttributeError):
        return PengaturanAplikasi()
    except OSError as galat:
        raise PenyimpananError(f"Pengaturan tidak dapat dibaca: {galat}")


def simpan_pengaturan(pengaturan, jalur=JALUR_JSON):
    """Simpan tarif dan target ke JSON (mode 'w')."""
    try:
        os.makedirs(os.path.dirname(jalur), exist_ok=True)
        with open(jalur, "w", encoding="utf-8") as f:
            json.dump(pengaturan.ke_dict(), f, indent=2)
    except OSError as galat:
        raise PenyimpananError(f"Gagal menyimpan pengaturan: {galat}")