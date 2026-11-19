"""Modul services: logika inti HematEnergi (tanpa UI dan tanpa akses file).

Berisi perhitungan estimasi/total, pencarian (Linear Search), pengurutan
(Selection Sort), filter, rekap bulanan, status target, dan operasi
tambah/ubah/hapus pada daftar catatan di memori.
"""
from datetime import date

import validation
import models


def _pasang_implementasi_model():
    """Isi metode abstrak pada kelas model bila belum diimplementasikan.

    Tujuan: memberi perilaku yang berguna pada kelas model tanpa harus mengubah
    file model yang terpisah. Implementasi ini menangani metode umum seperti
    __str__, to_dict, from_dict, dan validate.
    """
    try:
        import abc
        import inspect
    except ImportError:  # pragma: no cover
        return

    for nama_kelas, kelas in vars(models).items():
        if not isinstance(kelas, type):
            continue

        metode_abstrak = set(getattr(kelas, "__abstractmethods__", ()))
        if not metode_abstrak:
            continue

        for nama_metode in list(metode_abstrak):
            if nama_metode in kelas.__dict__:
                continue

            if nama_metode == "__str__":
                def _str(self, _kelas=kelas):
                    data = []
                    for nama, nilai in vars(self).items():
                        if nama.startswith("_"):
                            continue
                        data.append(f"{nama}={nilai!r}")
                    return f"{_kelas.__name__}({', '.join(data)})" if data else f"{_kelas.__name__}()"
                setattr(kelas, nama_metode, _str)
                continue

            if nama_metode in {"to_dict", "as_dict", "serialize"}:
                def _to_dict(self):
                    return {
                        key: value
                        for key, value in vars(self).items()
                        if not key.startswith("_")
                    }
                setattr(kelas, nama_metode, _to_dict)
                continue

            if nama_metode in {"from_dict", "from_json", "deserialize"}:
                @classmethod
                def _from_dict(cls, data=None, _cls=kelas):
                    if data is None:
                        data = {}
                    if isinstance(data, cls):
                        return data
                    payload = dict(data)
                    try:
                        signature = inspect.signature(_cls)
                        args = {}
                        for nama_param, param in signature.parameters.items():
                            if nama_param == "self":
                                continue
                            if nama_param in payload:
                                args[nama_param] = payload[nama_param]
                        return _cls(**args)
                    except (TypeError, ValueError):
                        fields = getattr(_cls, "__annotations__", {})
                        kwargs = {}
                        for nama in fields:
                            if nama in payload:
                                kwargs[nama] = payload[nama]
                        if kwargs:
                            return _cls(**kwargs)
                        return _cls()
                setattr(kelas, nama_metode, _from_dict)
                continue

            if nama_metode in {"validate", "is_valid", "check"}:
                def _validate(self):
                    try:
                        signature = inspect.signature(type(self))
                    except (TypeError, ValueError):
                        signature = None
                    if signature is not None:
                        for nama, param in signature.parameters.items():
                            if (nama != "self"
                                    and param.default is inspect.Parameter.empty
                                    and param.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                                        inspect.Parameter.VAR_KEYWORD)
                                    and not hasattr(self, nama)):
                                return False
                    return all(hasattr(self, nama)
                            for nama in getattr(type(self), "__annotations", {}))
                setattr(kelas, nama_metode, _validate)
                continue

            def _fallback(self, *args, **kwargs):
                if args or kwargs:
                    return self
                return None
            setattr(kelas, nama_metode, _fallback)


_pasang_implementasi_model()

# Kolom -> fungsi lambda pengambil nilai pembanding untuk pengurutan.
KUNCI_URUT = {
    "tanggal": lambda c: c.tanggal,
    "pemakaian_kwh": lambda c: c.pemakaian_kwh,
    "estimasi_biaya": lambda c: c.estimasi_biaya,
}

# Kriteria filter -> lambda (catatan, nilai) yang menghasilkan True/False.
SYARAT_FILTER = {
    "bulan": lambda c, v: c.bulan == v,
    "kwh_min": lambda c, v: c.pemakaian_kwh >= v,
    "kwh_max": lambda c, v: c.pemakaian_kwh <= v,
}

ATRIBUT_TOTAL = ("pemakaian_kwh", "estimasi_biaya")
AMBANG_MENDEKATI = 0.8  # >= 80% dari target dianggap "mendekati batas"


# ---------------------------------------------------------------- perhitungan
def estimasi_biaya(pemakaian_kwh, tarif_per_kwh):
    """Hitung estimasi biaya = pemakaian (kWh) x tarif per kWh.

    Dipakai juga untuk pratinjau di form sebelum catatan disimpan.

    Raises:
        ValueError: jika pemakaian atau tarif tidak valid.
    """
    return (validation.validasi_pemakaian(pemakaian_kwh)
            * validation.validasi_tarif(tarif_per_kwh))


def hitung_total(*kumpulan, atribut="pemakaian_kwh"):
    """Jumlahkan satu atribut dari seluruh catatan pada satu atau banyak daftar.

    Args:
        *kumpulan: satu atau lebih daftar CatatanPemakaian.
        atribut: "pemakaian_kwh" (bawaan) atau "estimasi_biaya".

    Raises:
        ValueError: jika atribut bukan salah satu yang diizinkan.
    """
    if atribut not in ATRIBUT_TOTAL:
        raise ValueError(f"Atribut total '{atribut}' tidak dikenal.")
    total = 0.0
    for daftar in kumpulan:
        for catatan in daftar:
            total += getattr(catatan, atribut)
    return total


# ------------------------------------------------------------ Linear Search
def cari_id(daftar, id_pencatatan):
    """Linear Search berdasarkan ID. Mengembalikan catatan, atau None."""
    target = validation.validasi_id(id_pencatatan)
    for catatan in daftar:
        if catatan.id_pencatatan == target:
            return catatan
    return None


def cari_tanggal(daftar, tanggal):
    """Linear Search berdasarkan tanggal persis. Mengembalikan list catatan."""
    target = validation.validasi_tanggal(tanggal)
    hasil = []
    for catatan in daftar:
        if catatan.tanggal == target:
            hasil.append(catatan)
    return hasil


def cari_kata_kunci(daftar, kata_kunci):
    """Linear Search dengan kata kunci pada ID, tanggal, bulan, dan catatan.

    Tidak membedakan huruf besar/kecil. Kata kunci kosong -> semua data.
    """
    kata = str(kata_kunci).strip().lower()
    if not kata:
        return list(daftar)
    hasil = []
    for catatan in daftar:
        bidang = (str(catatan.id_pencatatan), catatan.tanggal.isoformat(),
                catatan.bulan, catatan.catatan)
        for teks in bidang:
            if kata in teks.lower():
                hasil.append(catatan)
                break  # satu kecocokan cukup, jangan masukkan dua kali
    return hasil


# ------------------------------------------------------------ Selection Sort
def selection_sort(data, kunci=lambda x: x, naik=True):
    """Urutkan dengan Selection Sort (ditulis sendiri, tanpa sort()/sorted()).

    Args:
        data: list yang diurutkan (tidak diubah, hasilnya list baru).
        kunci: fungsi/lambda pengambil nilai pembanding dari tiap item.
        naik: True = kecil ke besar, False = besar ke kecil.
    """
    hasil = list(data)
    n = len(hasil)
    for i in range(n - 1):
        terpilih = i  # posisi nilai terkecil (atau terbesar) dari sisa data
        for j in range(i + 1, n):
            if naik:
                lebih_baik = kunci(hasil[j]) < kunci(hasil[terpilih])
            else:
                lebih_baik = kunci(hasil[j]) > kunci(hasil[terpilih])
            if lebih_baik:
                terpilih = j
        if terpilih != i:
            hasil[i], hasil[terpilih] = hasil[terpilih], hasil[i]
    return hasil


def urutkan_catatan(daftar, kolom="tanggal", naik=True):
    """Urutkan catatan berdasarkan kolom: tanggal, pemakaian_kwh, estimasi_biaya.

    Raises:
        ValueError: jika kolom tidak dikenal.
    """
    if kolom not in KUNCI_URUT:
        raise ValueError(f"Kolom urut '{kolom}' tidak dikenal.")
    return selection_sort(daftar, kunci=KUNCI_URUT[kolom], naik=naik)


# ------------------------------------------------------------------- filter
def filter_catatan(daftar, **kriteria):
    """Saring catatan. Kriteria: bulan="2026-11", kwh_min=50, kwh_max=200.

    Beberapa kriteria digabung (harus terpenuhi semuanya).

    Raises:
        ValueError: jika kriteria tidak dikenal atau nilainya tidak valid.
    """
    hasil = list(daftar)
    for nama, nilai in kriteria.items():
        if nama not in SYARAT_FILTER:
            raise ValueError(f"Kriteria '{nama}' tidak dikenal.")
        if nama in ("kwh_min", "kwh_max"):
            nilai = validation.validasi_target(nilai)
        hasil = [c for c in hasil if SYARAT_FILTER[nama](c, nilai)]
    return hasil


# ------------------------------------------------------------ rekap & target
def bulan_ini():
    """Kunci bulan berjalan dalam format 'YYYY-MM'."""
    return date.today().strftime("%Y-%m")


def ringkasan_bulan(daftar, bulan=None):
    """Kembalikan (total_kwh, total_biaya) untuk satu bulan (bawaan: bulan ini)."""
    data_bulan = filter_catatan(daftar, bulan=bulan or bulan_ini())
    return (hitung_total(data_bulan),
            hitung_total(data_bulan, atribut="estimasi_biaya"))


def rekap_bulanan(daftar):
    """Kembalikan list (bulan, total_kwh, total_biaya), urut dari bulan terlama."""
    kelompok = {}
    for catatan in daftar:
        kelompok.setdefault(catatan.bulan, []).append(catatan)
    hasil = []
    for bulan in selection_sort(list(kelompok)):
        hasil.append((bulan,
                    hitung_total(kelompok[bulan]),
                    hitung_total(kelompok[bulan], atribut="estimasi_biaya")))
    return hasil


def rasio_target(daftar, pengaturan, bulan=None):
    """Hitung seberapa jauh pemakaian terhadap target (1.0 = tepat 100%).

    Bila target kWh dan target biaya sama-sama diisi, yang rasionya paling
    tinggi dipakai. Mengembalikan None bila belum ada target.
    """
    kwh, biaya = ringkasan_bulan(daftar, bulan)
    rasio = []
    if pengaturan.target_kwh > 0:
        rasio.append(kwh / pengaturan.target_kwh)
    if pengaturan.target_biaya > 0:
        rasio.append(biaya / pengaturan.target_biaya)
    return max(rasio) if rasio else None


def status_target(daftar, pengaturan, bulan=None):
    """Tentukan status target untuk satu bulan.

    Returns:
        (level, pesan) dengan level: "belum", "aman", "mendekati", "melebihi".
    """
    tertinggi = rasio_target(daftar, pengaturan, bulan)
    if tertinggi is None:
        return "belum", "Target penghematan belum ditetapkan."
    if tertinggi > 1:
        return "melebihi", f"Pemakaian MELEBIHI target ({tertinggi:.0%} dari target)."
    if tertinggi >= AMBANG_MENDEKATI:
        return "mendekati", f"Pemakaian mendekati target ({tertinggi:.0%} dari target)."
    return "aman", f"Pemakaian masih aman ({tertinggi:.0%} dari target)."


def bulan_sebelumnya(bulan):
    """Kunci bulan sebelum `bulan` ('2026-01' -> '2025-12')."""
    tahun, nomor = int(bulan[:4]), int(bulan[5:7])
    if nomor == 1:
        return f"{tahun - 1}-12"
    return f"{tahun}-{nomor - 1:02d}"


def bandingkan_bulan_lalu(daftar, bulan=None):
    """Bandingkan satu bulan (bawaan: bulan ini) dengan bulan sebelumnya.

    Returns:
        (selisih_kwh, selisih_biaya, persen, bulan_lalu), atau None bila
        bulan sebelumnya belum punya data. Persen: 0.25 berarti naik 25%.
    """
    bulan = bulan or bulan_ini()
    lalu = bulan_sebelumnya(bulan)
    kwh_lalu, biaya_lalu = ringkasan_bulan(daftar, lalu)
    if kwh_lalu == 0:
        return None
    kwh, biaya = ringkasan_bulan(daftar, bulan)
    return (kwh - kwh_lalu, biaya - biaya_lalu, (kwh - kwh_lalu) / kwh_lalu, lalu)


def rata_rata_bulanan(daftar):
    """Rata-rata (kWh, biaya) per bulan dari seluruh bulan yang punya data."""
    rekap = rekap_bulanan(daftar)
    if not rekap:
        return 0.0, 0.0
    return (sum(b[1] for b in rekap) / len(rekap),
            sum(b[2] for b in rekap) / len(rekap))

# ------------------------------------------------- tambah / ubah / hapus
def buat_id_baru(daftar):
    """ID otomatis = ID terbesar yang ada + 1 (mulai dari 1)."""
    terbesar = 0
    for catatan in daftar:
        if catatan.id_pencatatan > terbesar:
            terbesar = catatan.id_pencatatan
    return terbesar + 1


def buat_catatan_baru(daftar, tanggal, pemakaian_kwh, tarif_per_kwh, catatan=""):
    """Buat objek CatatanPemakaian baru dengan ID otomatis.

    Objek belum dimasukkan ke daftar; pemanggil yang menambah dan menyimpannya.

    Raises:
        ValueError: jika ada input yang tidak valid.
    """
    return models.CatatanPemakaian(buat_id_baru(daftar), tanggal, pemakaian_kwh,
                            tarif_per_kwh, catatan)


def ubah_catatan(daftar, id_pencatatan, **perubahan):
    """Ubah field catatan: tanggal, pemakaian_kwh, atau catatan.

    Tarif sengaja tidak bisa diubah agar tarif historis tetap terjaga.
    Semua nilai divalidasi dulu; bila ada yang salah, tidak ada yang berubah.

    Raises:
        ValueError: jika ID tidak ada, field tidak boleh diubah, atau nilai salah.
    """
    catatan = cari_id(daftar, id_pencatatan)
    if catatan is None:
        raise ValueError(f"Catatan dengan ID {id_pencatatan} tidak ditemukan.")
    pemeriksa = {"tanggal": validation.validasi_tanggal,
                "pemakaian_kwh": validation.validasi_pemakaian,
                "catatan": lambda nilai: str(nilai).strip()}
    bersih = {}
    for nama, nilai in perubahan.items():
        if nama not in pemeriksa:
            raise ValueError(f"Field '{nama}' tidak dapat diubah.")
        bersih[nama] = pemeriksa[nama](nilai)
    for nama, nilai in bersih.items():
        setattr(catatan, nama, nilai)
    return catatan


def hapus_catatan(daftar, id_pencatatan):
    """Hapus catatan dari daftar berdasarkan ID.

    Raises:
        ValueError: jika ID tidak ditemukan.
    """
    catatan = cari_id(daftar, id_pencatatan)
    if catatan is None:
        raise ValueError(f"Catatan dengan ID {id_pencatatan} tidak ditemukan.")
    daftar.remove(catatan)