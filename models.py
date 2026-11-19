"""Modul models: class data HematEnergi.

- CatatanPemakaian   : satu catatan pemakaian listrik.
- PengaturanAplikasi : tarif dan target penghematan.
Nilai selalu divalidasi lewat setter sehingga objek tidak pernah berisi
data yang salah.
"""
import validation

# Urutan kolom pada file pemakaian.csv
KOLOM_CSV = ("id_pencatatan", "tanggal", "bulan", "pemakaian_kwh",
            "tarif_per_kwh", "estimasi_biaya", "catatan")


class CatatanPemakaian:
    """Satu catatan pemakaian listrik.

    Tarif disimpan di setiap catatan, jadi mengubah tarif di pengaturan
    tidak mengubah perhitungan catatan lama.
    """

    def __init__(self, id_pencatatan, tanggal, pemakaian_kwh,
                tarif_per_kwh, catatan=""):
        self._id_pencatatan = validation.validasi_id(id_pencatatan)
        self.tanggal = tanggal              # lewat setter (divalidasi)
        self.pemakaian_kwh = pemakaian_kwh  # lewat setter (divalidasi)
        self.tarif_per_kwh = tarif_per_kwh  # lewat setter (divalidasi)
        self.catatan = catatan

    # ---------- getter & setter ----------
    @property
    def id_pencatatan(self):
        """ID unik catatan (hanya bisa dibaca, tidak boleh diubah)."""
        return self._id_pencatatan

    @property
    def tanggal(self):
        """Tanggal pencatatan (objek date)."""
        return self._tanggal

    @tanggal.setter
    def tanggal(self, nilai):
        self._tanggal = validation.validasi_tanggal(nilai)

    @property
    def pemakaian_kwh(self):
        """Pemakaian listrik dalam kWh."""
        return self._pemakaian_kwh

    @pemakaian_kwh.setter
    def pemakaian_kwh(self, nilai):
        self._pemakaian_kwh = validation.validasi_pemakaian(nilai)

    @property
    def tarif_per_kwh(self):
        """Tarif per kWh yang berlaku saat catatan dibuat."""
        return self._tarif_per_kwh

    @tarif_per_kwh.setter
    def tarif_per_kwh(self, nilai):
        self._tarif_per_kwh = validation.validasi_tarif(nilai)

    @property
    def catatan(self):
        """Catatan tambahan (boleh kosong)."""
        return self._catatan

    @catatan.setter
    def catatan(self, nilai):
        self._catatan = str(nilai).strip()

    # ---------- nilai turunan ----------
    @property
    def bulan(self):
        """Bulan dalam format 'YYYY-MM', dipakai untuk filter dan rekap."""
        return self._tanggal.strftime("%Y-%m")

    @property
    def estimasi_biaya(self):
        """Estimasi biaya = pemakaian (kWh) x tarif per kWh."""
        return self._pemakaian_kwh * self._tarif_per_kwh

    # ---------- konversi ke/dari baris CSV ----------
    def ke_baris(self):
        """Ubah menjadi dict dengan kunci sesuai KOLOM_CSV."""
        return {
            "id_pencatatan": self._id_pencatatan,
            "tanggal": self._tanggal.isoformat(),
            "bulan": self.bulan,
            "pemakaian_kwh": self._pemakaian_kwh,
            "tarif_per_kwh": self._tarif_per_kwh,
            "estimasi_biaya": self.estimasi_biaya,
            "catatan": self._catatan,
        }

    @classmethod
    def dari_baris(cls, baris):
        """Buat objek dari satu baris CSV (dict).

        Kolom bulan dan estimasi_biaya di file diabaikan lalu dihitung ulang,
        supaya data yang diedit manual di CSV tidak membuat angka tidak cocok.

        Raises:
            ValueError: jika ada kolom hilang atau nilainya tidak valid.
        """
        try:
            return cls(baris["id_pencatatan"], baris["tanggal"],
                    baris["pemakaian_kwh"], baris["tarif_per_kwh"],
                    baris.get("catatan") or "")
        except KeyError as galat:
            raise ValueError(f"Kolom {galat} tidak ditemukan pada baris data.")

    def __repr__(self):
        return (f"CatatanPemakaian(id={self._id_pencatatan}, "
                f"tanggal={self._tanggal}, kwh={self._pemakaian_kwh})")


class PengaturanAplikasi:
    """Tarif listrik dan target penghematan bulanan."""

    def __init__(self, tarif_listrik=1500.0, target_kwh=0.0, target_biaya=0.0):
        self.tarif_listrik = tarif_listrik
        self.target_kwh = target_kwh
        self.target_biaya = target_biaya

    @property
    def tarif_listrik(self):
        """Tarif per kWh yang dipakai untuk catatan baru."""
        return self._tarif_listrik

    @tarif_listrik.setter
    def tarif_listrik(self, nilai):
        self._tarif_listrik = validation.validasi_tarif(nilai)

    @property
    def target_kwh(self):
        """Batas maksimum pemakaian per bulan (0 = tidak dipakai)."""
        return self._target_kwh

    @target_kwh.setter
    def target_kwh(self, nilai):
        self._target_kwh = validation.validasi_target(nilai)

    @property
    def target_biaya(self):
        """Batas maksimum biaya per bulan (0 = tidak dipakai)."""
        return self._target_biaya

    @target_biaya.setter
    def target_biaya(self, nilai):
        self._target_biaya = validation.validasi_target(nilai)

    def ke_dict(self):
        """Ubah menjadi dict untuk disimpan ke pengaturan.json."""
        return {"tarif_listrik": self._tarif_listrik,
                "target_kwh": self._target_kwh,
                "target_biaya": self._target_biaya}

    @classmethod
    def dari_dict(cls, data):
        """Buat objek dari dict JSON. Kunci yang hilang memakai nilai bawaan."""
        return cls(data.get("tarif_listrik", 1500.0),
                data.get("target_kwh", 0.0),
                data.get("target_biaya", 0.0))