import unittest

import models as m
import services as svc
import validation as val


class TestHematEnergiCore(unittest.TestCase):
    """Kelas pengujian fungsi pengolahan data, searching, sorting, filter, dan validasi."""

    def setUp(self):
        """Siapkan data uji awal sebelum setiap test case dijalankan."""
        self.catatan_1 = m.CatatanPemakaian(
            1, "2026-10-10", 50.0, 1500.0, "Pemakaian awal Oktober"
        )
        self.catatan_2 = m.CatatanPemakaian(
            2, "2026-11-05", 120.0, 1500.0, "AC ruang tamu"
        )
        self.catatan_3 = m.CatatanPemakaian(
            3, "2026-11-18", 25.5, 2000.0, "Pompa air & lampu"
        )
        self.daftar_uji = [self.catatan_2, self.catatan_1, self.catatan_3]

    def test_estimasi_biaya_valid_dan_koma(self):
        """Menguji perhitungan estimasi biaya termasuk input desimal pakai koma."""
        biaya = svc.estimasi_biaya("12,5", "1500")
        self.assertAlmostEqual(biaya, 18750.0)

    def test_cari_kata_kunci_linear_search(self):
        """Menguji pencarian kata kunci (Linear Search) tanpa membedakan huruf besar/kecil."""
        hasil = svc.cari_kata_kunci(self.daftar_uji, "ruang tamu")
        self.assertEqual(len(hasil), 1)
        self.assertEqual(hasil[0].id_pencatatan, 2)

    def test_selection_sort_naik_dan_turun(self):
        """Menguji Selection Sort berdasarkan pemakaian_kwh secara menaik dan menurun."""
        urut_naik = svc.urutkan_catatan(self.daftar_uji, kolom="pemakaian_kwh", naik=True)
        self.assertEqual([c.id_pencatatan for c in urut_naik], [3, 1, 2])

        urut_turun = svc.urutkan_catatan(self.daftar_uji, kolom="pemakaian_kwh", naik=False)
        self.assertEqual([c.id_pencatatan for c in urut_turun], [2, 1, 3])

    def test_filter_catatan_bulan_dan_kwh(self):
        """Menguji penyaringan catatan berdasarkan bulan dan batas minimum kWh."""
        hasil = svc.filter_catatan(self.daftar_uji, bulan="2026-11", kwh_min=50.0)
        self.assertEqual(len(hasil), 1)
        self.assertEqual(hasil[0].id_pencatatan, 2)

    def test_validasi_input_tidak_valid_melempar_value_error(self):
        """Menguji bahwa input kWh nol/negatif dan format tanggal salah memicu ValueError."""
        with self.assertRaises(ValueError):
            val.validasi_pemakaian("0")
        with self.assertRaises(ValueError):
            val.validasi_pemakaian("-10")
        with self.assertRaises(ValueError):
            val.validasi_tanggal("19-11-2026")


if __name__ == "__main__":
    unittest.main()