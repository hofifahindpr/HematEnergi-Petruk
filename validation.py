"""Modul validation: pemeriksaan input pengguna untuk HematEnergi.

Setiap fungsi mengembalikan nilai yang sudah bersih (tipe benar), atau
melempar ValueError berisi pesan yang siap ditampilkan ke pengguna.
Semua pemeriksaan dikumpulkan di sini agar tidak tersebar di UI.
"""
from datetime import date, datetime


def validasi_tanggal(nilai):
    """Ubah teks 'YYYY-MM-DD' (atau objek date) menjadi objek date.

    Raises:
        ValueError: jika kosong atau formatnya salah.
    """
    if isinstance(nilai, date):
        return nilai
    teks = str(nilai).strip()
    if not teks:
        raise ValueError("Tanggal wajib diisi.")
    try:
        return datetime.strptime(teks, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Tanggal harus berformat YYYY-MM-DD, contoh 2026-11-12.")


def _ke_angka(nilai, nama_field):
    """Ubah input menjadi float. Koma desimal (1,5) diterima.

    Raises:
        ValueError: jika kosong atau bukan angka.
    """
    teks = str(nilai).strip().replace(",", ".")
    if not teks:
        raise ValueError(f"{nama_field} wajib diisi.")
    try:
        return float(teks)
    except ValueError:
        raise ValueError(f"{nama_field} harus berupa angka.")


def validasi_pemakaian(nilai):
    """Pemakaian listrik (kWh) harus angka lebih besar dari 0."""
    angka = _ke_angka(nilai, "Pemakaian (kWh)")
    if angka <= 0:
        raise ValueError("Pemakaian (kWh) harus lebih besar dari 0.")
    return angka


def validasi_tarif(nilai):
    """Tarif per kWh harus angka lebih besar dari 0 (tidak boleh nol/negatif)."""
    angka = _ke_angka(nilai, "Tarif per kWh")
    if angka <= 0:
        raise ValueError("Tarif per kWh harus lebih besar dari 0.")
    return angka


def validasi_target(nilai):
    """Target boleh 0 (artinya tidak dipakai), tapi tidak boleh negatif.

    Input kosong dianggap 0.
    """
    if str(nilai).strip() == "":
        return 0.0
    angka = _ke_angka(nilai, "Target")
    if angka < 0:
        raise ValueError("Target tidak boleh negatif.")
    return angka


def validasi_id(nilai):
    """ID pencatatan harus bilangan bulat positif."""
    try:
        angka = int(str(nilai).strip())
    except ValueError:
        raise ValueError("ID pencatatan harus berupa bilangan bulat.")
    if angka <= 0:
        raise ValueError("ID pencatatan harus lebih besar dari 0.")
    return angka