"""Modul ui: seluruh tampilan dan navigasi HematEnergi berbasis Flet."""
from datetime import date
import flet as ft

import services
import storage
from models import PengaturanAplikasi
from storage import PenyimpananError

# ---------------------------------------------------------------- tema & palet
WARNA = {
    "biru_tua": "#004A8F",
    "biru": "#0072CE",
    "biru_cerah": "#2196F3",
    "biru_muda": "#BBDEFB",
    "biru_pucat": "#E8F3FD",
    "batang": "#90CAF9",
    "latar": "#F2F6FA",
    "kartu": "#FFFFFF",
    "garis": "#E2E8F0",
    "teks": "#1E293B",
    "teks_samar": "#64748B",
    "kuning": "#F59E0B",
    "oranye": "#EA580C",
    "hijau": "#059669",
}

WARNA_STATUS = {
    "belum": "#64748B",
    "aman": "#059669",
    "mendekati": "#F59E0B",
    "melebihi": "#EA580C",
}

LABEL_STATUS = {
    "belum": "Belum diatur",
    "aman": "Aman",
    "mendekati": "Mendekati batas",
    "melebihi": "Melebihi batas",
}

NAMA_BULAN = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
)

SEMUA_BULAN = "Semua bulan"
KOLOM_URUT = {
    "Tanggal": "tanggal",
    "Pemakaian (kWh)": "pemakaian_kwh",
    "Estimasi biaya": "estimasi_biaya",
}


# ----------------------------------------------------------- fungsi bantu
def rupiah(angka):
    return "Rp{:,.0f}".format(angka).replace(",", ".")


def label_bulan(kunci):
    tahun, nomor = kunci.split("-")
    return f"{NAMA_BULAN[int(nomor) - 1][:3]} {tahun[2:]}"


def nama_bulan(kunci):
    return NAMA_BULAN[int(kunci[5:7]) - 1]


def nama_bulan_tahun(kunci):
    return f"{NAMA_BULAN[int(kunci[5:7]) - 1]} {kunci[:4]}"


def tanggal_hari_ini():
    hari = date.today()
    return f"Hari ini, {hari.day} {NAMA_BULAN[hari.month - 1]} {hari.year}"


def gaya_kartu(padding=20, bgcolor=WARNA["kartu"]):
    return dict(
        bgcolor=bgcolor,
        border_radius=16,
        padding=padding,
        border=ft.Border.all(1, WARNA["garis"]),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=12,
            color="#0F172A0D",
            offset=ft.Offset(0, 4),
        ),
    )


# ----------------------------------------------------------- aplikasi utama
class HematEnergiFlet:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "HematEnergi - Pencatatan & Estimasi Listrik"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=WARNA["biru"])
        self.page.bgcolor = WARNA["latar"]
        self.page.padding = 0
        self.page.window.width = 1280
        self.page.window.height = 780
        self.page.window.min_width = 1080
        self.page.window.min_height = 680

        self.daftar = []
        self.pengaturan = PengaturanAplikasi()
        self.halaman_aktif = "dashboard"

        # State halaman Riwayat
        self.kata_cari = ""
        self.filter_bulan = SEMUA_BULAN
        self.urut_kolom = "Tanggal"
        self.urut_naik = False
        self.peta_bulan = {}

        self._muat_data()
        self._bangun_komponen()
        self.segarkan_semua()

    def _muat_data(self):
        try:
            storage.siapkan_file()
            self.daftar, rusak = storage.muat_catatan()
            self.pengaturan = storage.muat_pengaturan()
            if rusak:
                self._tampilkan_popup(
                    "Sebagian Data Dilewati",
                    f"{rusak} baris pada pemakaian.csv tidak valid dan dilewati.",
                    jenis="peringatan",
                )
        except PenyimpananError as galat:
            self._tampilkan_popup(
                "Gagal Memuat Data",
                str(galat),
                jenis="error",
            )

    def _tampilkan_popup(self, judul, pesan, jenis="info"):
        """Tampilkan pop-up pemberitahuan (AlertDialog) yang jelas di tengah layar."""
        ikon_peta = {
            "sukses": (ft.Icons.CHECK_CIRCLE_ROUNDED, WARNA["hijau"]),
            "peringatan": (ft.Icons.WARNING_AMBER_ROUNDED, WARNA["kuning"]),
            "error": (ft.Icons.ERROR_ROUNDED, WARNA["oranye"]),
            "info": (ft.Icons.INFO_ROUNDED, WARNA["biru_tua"]),
        }
        ikon, warna_ikon = ikon_peta.get(jenis, ikon_peta["info"])

        def tutup(_):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ikon, color=warna_ikon, size=24),
                    ft.Text(judul, size=18, weight=ft.FontWeight.BOLD, color=WARNA["teks"]),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=380,
                content=ft.Text(pesan, size=14, color=WARNA["teks"]),
            ),
            actions=[
                ft.Button(
                    content="OK",
                    bgcolor=warna_ikon,
                    color="white",
                    on_click=tutup,
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    # ========================================================== KERANGKA UTAMA
    def _bangun_komponen(self):
        self.nav_items = {}
        daftar_menu = [
            ("dashboard", ft.Icons.DASHBOARD_ROUNDED, "Dashboard"),
            ("catat", ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, "Catat"),
            ("riwayat", ft.Icons.HISTORY_ROUNDED, "Riwayat"),
            ("target", ft.Icons.TRACK_CHANGES_ROUNDED, "Target"),
        ]

        kolom_menu = []
        for kode, ikon, label in daftar_menu:
            btn = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ikon, size=24, color=WARNA["teks_samar"]),
                        ft.Text(
                            label,
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=WARNA["teks_samar"],
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                ),
                width=76,
                padding=ft.Padding.symmetric(vertical=12, horizontal=6),
                border_radius=14,
                ink=True,
                on_click=lambda e, k=kode: self._ganti_halaman(k),
            )
            self.nav_items[kode] = btn
            kolom_menu.append(btn)

        sidebar = ft.Container(
            width=104,
            bgcolor=WARNA["kartu"],
            border=ft.Border.only(right=ft.BorderSide(1, WARNA["garis"])),
            padding=ft.Padding.symmetric(vertical=24, horizontal=12),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.BOLT_ROUNDED, color="white", size=28),
                        width=50,
                        height=50,
                        border_radius=25,
                        bgcolor=WARNA["biru"],
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(
                        "HematEnergi",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=WARNA["biru_tua"],
                    ),
                    ft.Divider(height=16, color="transparent"),
                    *kolom_menu,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        self.txt_judul_halaman = ft.Text(
            "Dashboard",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=WARNA["biru_tua"],
        )
        header = ft.Row(
            [
                ft.Column(
                    [
                        self.txt_judul_halaman,
                        ft.Text(
                            "Pantau konsumsi listrik harian & estimasi tagihan bulanan",
                            size=13,
                            color=WARNA["teks_samar"],
                        ),
                    ],
                    spacing=2,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CALENDAR_TODAY_ROUNDED,
                                size=15,
                                color=WARNA["biru"],
                            ),
                            ft.Text(
                                tanggal_hari_ini(),
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=WARNA["teks"],
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor=WARNA["kartu"],
                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    border_radius=12,
                    border=ft.Border.all(1, WARNA["garis"]),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.view_dashboard = self._buat_halaman_dashboard()
        self.view_catat = self._buat_halaman_catat()
        self.view_riwayat = self._buat_halaman_riwayat()
        self.view_target = self._buat_halaman_target()

        self.wadah_halaman = ft.Container(content=self.view_dashboard, expand=True)

        area_kanan = ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=28, vertical=22),
            content=ft.Column(
                [
                    header,
                    ft.Divider(height=12, color="transparent"),
                    self.wadah_halaman,
                ],
                expand=True,
            ),
        )

        self.page.add(ft.Row([sidebar, area_kanan], spacing=0, expand=True))
        self._perbarui_sorotan_menu()

    def _ganti_halaman(self, kode):
        self.halaman_aktif = kode
        judul_peta = {
            "dashboard": "Dashboard",
            "catat": "Catat Pemakaian",
            "riwayat": "Riwayat Pemakaian",
            "target": "Target & Tarif Listrik",
        }
        view_peta = {
            "dashboard": self.view_dashboard,
            "catat": self.view_catat,
            "riwayat": self.view_riwayat,
            "target": self.view_target,
        }
        self.txt_judul_halaman.value = judul_peta[kode]
        self.wadah_halaman.content = view_peta[kode]
        self._perbarui_sorotan_menu()
        self.segarkan_semua()

    def _perbarui_sorotan_menu(self):
        for kode, btn in self.nav_items.items():
            aktif = kode == self.halaman_aktif
            btn.bgcolor = WARNA["biru_pucat"] if aktif else "transparent"
            ikon_ctrl, teks_ctrl = btn.content.controls
            ikon_ctrl.color = WARNA["biru_tua"] if aktif else WARNA["teks_samar"]
            teks_ctrl.color = WARNA["biru_tua"] if aktif else WARNA["teks_samar"]

    # ========================================================== 1. DASHBOARD
    def _buat_halaman_dashboard(self):
        self.txt_banner = ft.Text(
            "", size=13, weight=ft.FontWeight.W_600, color="white"
        )
        self.banner_peringatan = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=12,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="white", size=20),
                    self.txt_banner,
                ],
                spacing=10,
            ),
        )

        self.stat_biaya = self._buat_kartu_stat(
            "Estimasi Biaya Bulan Ini",
            "-",
            "Berjalan",
            ft.Icons.PAYMENTS_ROUNDED,
            WARNA["biru"],
        )
        self.stat_kwh = self._buat_kartu_stat(
            "Total Pemakaian Bulan Ini",
            "-",
            "Berjalan",
            ft.Icons.ELECTRIC_BOLT_ROUNDED,
            WARNA["hijau"],
        )
        self.stat_rata = self._buat_kartu_stat(
            "Rata-Rata Bulanan",
            "-",
            "Semua riwayat",
            ft.Icons.ANALYTICS_ROUNDED,
            WARNA["biru_tua"],
        )
        self.stat_tarif = self._buat_kartu_stat(
            "Tarif Listrik Aktif",
            "-",
            "Per kWh",
            ft.Icons.PRICE_CHANGE_ROUNDED,
            WARNA["kuning"],
        )

        baris_stat = ft.Row(
            [
                self.stat_biaya["card"],
                self.stat_kwh["card"],
                self.stat_rata["card"],
                self.stat_tarif["card"],
            ],
            spacing=14,
        )

        self.wadah_grafik = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.END,
            height=185,
        )
        self.txt_banding = ft.Text("", size=12, color=WARNA["teks_samar"])

        kartu_grafik = ft.Container(
            **gaya_kartu(padding=20),
            expand=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Pemakaian Listrik per Bulan (kWh)",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=WARNA["teks"],
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "6 Bulan Terakhir",
                                    size=11,
                                    color=WARNA["biru_tua"],
                                    weight=ft.FontWeight.W_600,
                                ),
                                bgcolor=WARNA["biru_pucat"],
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                border_radius=8,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=8, color="transparent"),
                    self.wadah_grafik,
                    ft.Divider(height=12, color=WARNA["garis"]),
                    self.txt_banding,
                ],
                spacing=6,
            ),
        )

        self.ring_target = ft.ProgressRing(
            width=140,
            height=140,
            stroke_width=14,
            value=0,
            bgcolor=WARNA["biru_pucat"],
            color=WARNA["hijau"],
        )
        self.txt_persen_target = ft.Text(
            "-", size=26, weight=ft.FontWeight.BOLD, color=WARNA["biru_tua"]
        )
        self.txt_sub_target = ft.Text("dari target", size=11, color=WARNA["teks_samar"])
        self.txt_chip_status = ft.Text(
            "Belum diatur", size=12, weight=ft.FontWeight.BOLD, color="white"
        )
        self.chip_status = ft.Container(
            content=self.txt_chip_status,
            bgcolor=WARNA["teks_samar"],
            padding=ft.Padding.symmetric(horizontal=14, vertical=6),
            border_radius=20,
        )
        self.txt_detail_target = ft.Text(
            "", size=12, color=WARNA["teks_samar"], text_align=ft.TextAlign.CENTER
        )

        kartu_target = ft.Container(
            **gaya_kartu(padding=20),
            width=330,
            content=ft.Column(
                [
                    ft.Text(
                        "Target Penghematan",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=WARNA["teks"],
                    ),
                    ft.Divider(height=8, color="transparent"),
                    ft.Stack(
                        [
                            self.ring_target,
                            ft.Container(
                                width=140,
                                height=140,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Column(
                                    [self.txt_persen_target, self.txt_sub_target],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=0,
                                ),
                            ),
                        ],
                        width=140,
                        height=140,
                    ),
                    ft.Divider(height=6, color="transparent"),
                    self.chip_status,
                    self.txt_detail_target,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        self.kolom_terbaru = ft.Column(spacing=6)
        kartu_terbaru = ft.Container(
            **gaya_kartu(padding=20),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Catatan Terbaru",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=WARNA["teks"],
                            ),
                            ft.TextButton(
                                content="Lihat Semua →",
                                on_click=lambda _: self._ganti_halaman("riwayat"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.kolom_terbaru,
                ],
                spacing=10,
            ),
        )

        return ft.Column(
            [
                self.banner_peringatan,
                baris_stat,
                ft.Row(
                    [kartu_grafik, kartu_target],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                kartu_terbaru,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _buat_kartu_stat(self, judul, nilai, ket, ikon, warna_ikon):
        txt_nilai = ft.Text(nilai, size=20, weight=ft.FontWeight.BOLD, color=WARNA["teks"])
        txt_ket = ft.Text(ket, size=12, color=WARNA["teks_samar"])
        card = ft.Container(
            **gaya_kartu(padding=16),
            expand=True,
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ikon, color=warna_ikon, size=22),
                        width=44,
                        height=44,
                        border_radius=12,
                        bgcolor=WARNA["biru_pucat"],
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            ft.Text(judul, size=12, color=WARNA["teks_samar"]),
                            txt_nilai,
                            txt_ket,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
        )
        return {"card": card, "nilai": txt_nilai, "ket": txt_ket}

    # ========================================================== 2. CATAT PEMAKAIAN
    def _buat_halaman_catat(self):
        self.in_id = ft.TextField(
            label="ID Pencatatan (Otomatis)",
            hint_text="Terisi otomatis oleh sistem",
            read_only=True,
            border_radius=10,
            bgcolor=WARNA["latar"],
            expand=True,
        )
        self.in_tanggal = ft.TextField(
            label="Tanggal Pemakaian",
            hint_text="Contoh: 2026-11-19 (Format: YYYY-MM-DD)",
            value=date.today().isoformat(),
            border_radius=10,
            expand=True,
        )
        self.in_kwh = ft.TextField(
            label="Pemakaian Listrik (kWh)",
            hint_text="Contoh: 12.5 (gunakan titik untuk desimal)",
            border_radius=10,
            expand=True,
            on_change=lambda _: self._hitung_pratinjau(),
        )
        self.in_tarif = ft.TextField(
            label="Tarif per kWh (Rp)",
            hint_text="Contoh: 1500",
            value="",
            border_radius=10,
            expand=True,
            on_change=lambda _: self._hitung_pratinjau(),
        )
        self.in_catatan = ft.TextField(
            label="Catatan Tambahan (Opsional)",
            hint_text="Contoh: Pemakaian AC ruang tamu & mesin cuci",
            border_radius=10,
            expand=True,
        )

        kartu_form = ft.Container(
            **gaya_kartu(padding=24),
            expand=True,
            content=ft.Column(
                [
                    ft.Text(
                        "Formulir Pencatatan Baru",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=WARNA["teks"],
                    ),
                    ft.Text(
                        "Masukkan data pemakaian listrik untuk menghitung estimasi biaya.",
                        size=13,
                        color=WARNA["teks_samar"],
                    ),
                    ft.Divider(height=6, color="transparent"),
                    self.in_id,
                    self.in_tanggal,
                    self.in_kwh,
                    self.in_tarif,
                    self.in_catatan,
                    ft.Divider(height=8, color="transparent"),
                    ft.Row(
                        [
                            ft.Button(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.SAVE_ROUNDED, size=18),
                                        ft.Text("Simpan Catatan"),
                                    ],
                                    spacing=8,
                                ),
                                bgcolor=WARNA["biru_tua"],
                                color="white",
                                height=44,
                                on_click=self._aksi_simpan_catatan,
                            ),
                            ft.OutlinedButton(
                                content="Reset Form",
                                height=44,
                                on_click=self._aksi_reset_form,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        self.txt_estimasi_live = ft.Text(
            "Rp0", size=34, weight=ft.FontWeight.BOLD, color=WARNA["biru_tua"]
        )
        kartu_preview = ft.Container(
            bgcolor=WARNA["biru_pucat"],
            border_radius=16,
            padding=24,
            width=360,
            border=ft.Border.all(1, WARNA["biru_muda"]),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CALCULATE_ROUNDED,
                                color=WARNA["biru_tua"],
                                size=24,
                            ),
                            ft.Text(
                                "Pratinjau Estimasi Biaya",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=WARNA["biru_tua"],
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=8, color="transparent"),
                    self.txt_estimasi_live,
                    ft.Text(
                        "Rumus: Pemakaian (kWh) × Tarif per kWh",
                        size=12,
                        color=WARNA["teks_samar"],
                    ),
                    ft.Divider(height=16, color=WARNA["biru_muda"]),
                    ft.Text(
                        "Catatan: Tarif disimpan bersama masing-masing transaksi, sehingga perubahan tarif di masa depan tidak mengubah histori tagihan lama.",
                        size=12,
                        color=WARNA["teks"],
                    ),
                ],
                spacing=8,
            ),
        )

        return ft.Row(
            [kartu_form, kartu_preview],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _hitung_pratinjau(self):
        try:
            nilai = services.estimasi_biaya(self.in_kwh.value, self.in_tarif.value)
            self.txt_estimasi_live.value = rupiah(nilai)
        except ValueError:
            self.txt_estimasi_live.value = "-"
        self.page.update()

    def _aksi_reset_form(self, _=None):
        self.in_tanggal.value = date.today().isoformat()
        self.in_kwh.value = ""
        self.in_tarif.value = ""
        self.in_catatan.value = ""
        self.txt_estimasi_live.value = "Rp0"
        self.page.update()

    def _aksi_simpan_catatan(self, _):
        try:
            catatan = services.buat_catatan_baru(
                self.daftar,
                self.in_tanggal.value,
                self.in_kwh.value,
                self.in_tarif.value,
                self.in_catatan.value,
            )
        except ValueError as galat:
            self._tampilkan_popup("Input Tidak Valid", str(galat), jenis="error")
            return

        self.daftar.append(catatan)
        try:
            storage.tambah_catatan(catatan)
        except PenyimpananError as galat:
            self.daftar.remove(catatan)
            self._tampilkan_popup("Gagal Menyimpan", str(galat), jenis="error")
            return

        self._aksi_reset_form()
        self.segarkan_semua()

        level, pesan = services.status_target(self.daftar, self.pengaturan)
        if catatan.bulan == services.bulan_ini() and level in ("mendekati", "melebihi"):
            self._tampilkan_popup(
                "Tersimpan — Peringatan Target",
                f"Catatan ID {catatan.id_pencatatan} berhasil disimpan.\n\n{pesan}",
                jenis="peringatan",
            )
        else:
            self._tampilkan_popup(
                "Berhasil Disimpan",
                f"Catatan pemakaian ID {catatan.id_pencatatan} berhasil disimpan ke riwayat.",
                jenis="sukses",
            )

    # ========================================================== 3. RIWAYAT PEMAKAIAN
    def _buat_halaman_riwayat(self):
        self.in_cari = ft.TextField(
            hint_text="Cari ID, tanggal, atau catatan...",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            border_radius=10,
            height=42,
            width=280,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=0),
            on_change=self._ubah_cari,
        )

        self.dd_bulan = ft.Dropdown(
            width=180,
            value=SEMUA_BULAN,
            options=[ft.dropdown.Option(SEMUA_BULAN)],
            border_radius=10,
            on_select=self._ubah_filter_bulan,
        )

        self.dd_urut = ft.Dropdown(
            width=170,
            value="Tanggal",
            options=[ft.dropdown.Option(k) for k in KOLOM_URUT],
            border_radius=10,
            on_select=self._ubah_urut_kolom,
        )

        self.btn_arah = ft.OutlinedButton(
            content="Urutan: Turun ▼",
            height=42,
            on_click=self._toggle_arah_urut,
        )

        toolbar = ft.Container(
            **gaya_kartu(padding=14),
            content=ft.Row(
                [
                    self.in_cari,
                    self.dd_bulan,
                    self.dd_urut,
                    self.btn_arah,
                    ft.TextButton(
                        content="Reset", on_click=self._reset_filter_riwayat
                    ),
                ],
                spacing=10,
                wrap=True,
            ),
        )

        self.tabel_riwayat = ft.DataTable(
            heading_row_color=WARNA["biru_pucat"],
            heading_row_height=44,
            data_row_min_height=44,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tanggal", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Bulan", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Pemakaian", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Tarif/kWh", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(
                    ft.Text("Estimasi Biaya", weight=ft.FontWeight.BOLD), numeric=True
                ),
                ft.DataColumn(ft.Text("Catatan", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Aksi", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
        )

        wadah_tabel = ft.Container(
            **gaya_kartu(padding=12),
            expand=True,
            content=ft.Column(
                [ft.Row([self.tabel_riwayat], scroll=ft.ScrollMode.AUTO)],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

        self.txt_ringkasan_riwayat = ft.Text(
            "", size=13, weight=ft.FontWeight.W_500, color=WARNA["teks_samar"]
        )

        return ft.Column(
            [toolbar, wadah_tabel, self.txt_ringkasan_riwayat],
            spacing=12,
            expand=True,
        )

    def _ubah_cari(self, e):
        self.kata_cari = e.control.value
        self._perbarui_tabel_riwayat()
        self.page.update()

    def _ubah_filter_bulan(self, e):
        self.filter_bulan = e.control.value
        self._perbarui_tabel_riwayat()
        self.page.update()

    def _ubah_urut_kolom(self, e):
        self.urut_kolom = e.control.value
        self._perbarui_tabel_riwayat()
        self.page.update()

    def _toggle_arah_urut(self, _):
        self.urut_naik = not self.urut_naik
        self.btn_arah.content = "Urutan: Naik ▲" if self.urut_naik else "Urutan: Turun ▼"
        self._perbarui_tabel_riwayat()
        self.page.update()

    def _reset_filter_riwayat(self, _):
        self.kata_cari = ""
        self.in_cari.value = ""
        self.filter_bulan = SEMUA_BULAN
        self.dd_bulan.value = SEMUA_BULAN
        self.urut_kolom = "Tanggal"
        self.dd_urut.value = "Tanggal"
        self.urut_naik = False
        self.btn_arah.content = "Urutan: Turun ▼"
        self._perbarui_tabel_riwayat()
        self.page.update()

    def _buka_dialog_edit(self, catatan):
        in_tgl = ft.TextField(
            label="Tanggal (YYYY-MM-DD)",
            hint_text="Contoh: 2026-11-19",
            value=catatan.tanggal.isoformat(),
            border_radius=10,
        )
        in_kwh = ft.TextField(
            label="Pemakaian (kWh)",
            hint_text="Contoh: 12.5",
            value=f"{catatan.pemakaian_kwh:g}",
            border_radius=10,
        )
        in_cat = ft.TextField(
            label="Catatan",
            hint_text="Catatan tambahan (opsional)",
            value=catatan.catatan,
            border_radius=10,
        )

        def simpan_edit(_):
            lama = {
                "tanggal": catatan.tanggal,
                "pemakaian_kwh": catatan.pemakaian_kwh,
                "catatan": catatan.catatan,
            }
            try:
                services.ubah_catatan(
                    self.daftar,
                    catatan.id_pencatatan,
                    tanggal=in_tgl.value,
                    pemakaian_kwh=in_kwh.value,
                    catatan=in_cat.value,
                )
                storage.simpan_semua(self.daftar)
            except (ValueError, PenyimpananError) as galat:
                for k, v in lama.items():
                    setattr(catatan, k, v)
                self._tampilkan_popup("Input Tidak Valid", str(galat), jenis="error")
                return

            dlg.open = False
            self.segarkan_semua()
            self._tampilkan_popup(
                "Berhasil Diperbarui",
                f"Catatan ID {catatan.id_pencatatan} berhasil diperbarui.",
                jenis="sukses",
            )

        def tutup(_):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Ubah Catatan ID {catatan.id_pencatatan}"),
            content=ft.Column(
                [
                    ft.Text(
                        f"Tarif historis: {rupiah(catatan.tarif_per_kwh)}/kWh",
                        size=12,
                        color=WARNA["teks_samar"],
                    ),
                    in_tgl,
                    in_kwh,
                    in_cat,
                ],
                tight=True,
                spacing=12,
                width=380,
            ),
            actions=[
                ft.TextButton(content="Batal", on_click=tutup),
                ft.Button(
                    content="Simpan",
                    bgcolor=WARNA["biru_tua"],
                    color="white",
                    on_click=simpan_edit,
                ),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _konfirmasi_hapus(self, catatan):
        def lanjut_hapus(_):
            indeks = self.daftar.index(catatan)
            try:
                services.hapus_catatan(self.daftar, catatan.id_pencatatan)
                storage.simpan_semua(self.daftar)
            except (ValueError, PenyimpananError) as galat:
                if catatan not in self.daftar:
                    self.daftar.insert(indeks, catatan)
                self._tampilkan_popup("Gagal Menghapus", str(galat), jenis="error")
                return

            dlg.open = False
            self.segarkan_semua()
            self._tampilkan_popup(
                "Berhasil Dihapus",
                f"Catatan ID {catatan.id_pencatatan} telah dihapus.",
                jenis="sukses",
            )

        def tutup(_):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Hapus Catatan?"),
            content=ft.Text(
                f"Yakin ingin menghapus catatan ID {catatan.id_pencatatan} ({catatan.tanggal.isoformat()}, {catatan.pemakaian_kwh:.1f} kWh)?"
            ),
            actions=[
                ft.TextButton(content="Batal", on_click=tutup),
                ft.Button(
                    content="Hapus",
                    bgcolor=WARNA["oranye"],
                    color="white",
                    on_click=lanjut_hapus,
                ),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    # ========================================================== 4. TARGET & TARIF
    def _buat_halaman_target(self):
        self.in_set_tarif = ft.TextField(
            label="Tarif Listrik Aktif (Rp / kWh)",
            hint_text="Contoh: 1500",
            border_radius=10,
        )
        self.in_set_kwh = ft.TextField(
            label="Target Maksimum Pemakaian (kWh / bulan)",
            hint_text="Contoh: 200 ",
            border_radius=10,
        )
        self.in_set_biaya = ft.TextField(
            label="Target Maksimum Biaya (Rp / bulan)",
            hint_text="Contoh: 300000 ",
            border_radius=10,
        )

        kartu_pengaturan = ft.Container(
            **gaya_kartu(padding=24),
            width=520,
            content=ft.Column(
                [
                    ft.Text(
                        "Pengaturan Tarif & Target Penghematan",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=WARNA["teks"],
                    ),
                    ft.Text(
                        "Atur batas bulanan agar aplikasi memberi peringatan otomatis saat pemakaian mendekati atau melewati batas.",
                        size=13,
                        color=WARNA["teks_samar"],
                    ),
                    ft.Divider(height=6, color="transparent"),
                    self.in_set_tarif,
                    self.in_set_kwh,
                    self.in_set_biaya,
                    ft.Divider(height=6, color="transparent"),
                    ft.Button(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=18),
                                ft.Text("Simpan Pengaturan"),
                            ],
                            spacing=8,
                        ),
                        bgcolor=WARNA["biru_tua"],
                        color="white",
                        height=44,
                        on_click=self._simpan_pengaturan,
                    ),
                ],
                spacing=14,
            ),
        )
        return ft.Column([kartu_pengaturan], spacing=16)

    def _simpan_pengaturan(self, _):
        try:
            baru = PengaturanAplikasi(
                tarif_listrik=self.in_set_tarif.value,
                target_kwh=self.in_set_kwh.value,
                target_biaya=self.in_set_biaya.value,
            )
            storage.simpan_pengaturan(baru)
        except (ValueError, PenyimpananError) as galat:
            self._tampilkan_popup("Input Pengaturan Tidak Valid", str(galat), jenis="error")
            return

        self.pengaturan = baru
        self.segarkan_semua()
        self._tampilkan_popup(
            "Pengaturan Disimpan",
            "Tarif listrik aktif dan target penghematan berhasil disimpan!",
            jenis="sukses",
        )

    # ========================================================== PENYEGARAN DATA
    def segarkan_semua(self):
        kwh_ini, biaya_ini = services.ringkasan_bulan(self.daftar)
        rata_kwh, rata_biaya = services.rata_rata_bulanan(self.daftar)
        level, pesan = services.status_target(self.daftar, self.pengaturan)
        rasio = services.rasio_target(self.daftar, self.pengaturan)
        warna = WARNA_STATUS[level]

        if level in ("mendekati", "melebihi"):
            self.banner_peringatan.visible = True
            self.banner_peringatan.bgcolor = warna
            self.txt_banner.value = pesan
        else:
            self.banner_peringatan.visible = False

        self.stat_biaya["nilai"].value = rupiah(biaya_ini)
        self.stat_kwh["nilai"].value = f"{kwh_ini:.1f} kWh"
        self.stat_rata["nilai"].value = f"{rata_kwh:.1f} kWh"
        self.stat_rata["ket"].value = f"≈ {rupiah(rata_biaya)}/bln"
        self.stat_tarif["nilai"].value = f"{rupiah(self.pengaturan.tarif_listrik)}/kWh"

        self.ring_target.color = warna
        if rasio is None:
            self.ring_target.value = 0
            self.txt_persen_target.value = "-"
            self.txt_sub_target.value = "Belum diatur"
        else:
            self.ring_target.value = min(rasio, 1.0)
            self.txt_persen_target.value = f"{rasio:.0%}"
            self.txt_sub_target.value = "dari target"

        self.chip_status.bgcolor = warna
        self.txt_chip_status.value = LABEL_STATUS[level]

        bagian_target = []
        if self.pengaturan.target_kwh > 0:
            bagian_target.append(f"{self.pengaturan.target_kwh:.0f} kWh")
        if self.pengaturan.target_biaya > 0:
            bagian_target.append(rupiah(self.pengaturan.target_biaya))
        self.txt_detail_target.value = (
            "Maks: " + " / ".join(bagian_target)
            if bagian_target
            else "Atur batas di menu Target"
        )

        self.wadah_grafik.controls.clear()
        rekap = services.rekap_bulanan(self.daftar)[-6:]
        if not rekap:
            self.wadah_grafik.controls.append(
                ft.Text("Belum ada data pemakaian bulanan.", color=WARNA["teks_samar"])
            )
        else:
            maks_kwh = max(k for _, k, _ in rekap) or 1
            bulan_sekarang = services.bulan_ini()
            for bln, kwh_bln, _ in rekap:
                tinggi_batang = max(14, int((kwh_bln / maks_kwh) * 130))
                aktif = bln == bulan_sekarang
                self.wadah_grafik.controls.append(
                    ft.Column(
                        [
                            ft.Text(
                                f"{kwh_bln:.0f}",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=WARNA["teks"],
                            ),
                            ft.Container(
                                width=38,
                                height=tinggi_batang,
                                bgcolor=WARNA["biru_tua"] if aktif else WARNA["batang"],
                                border_radius=ft.BorderRadius.only(
                                    top_left=8, top_right=8
                                ),
                            ),
                            ft.Text(
                                label_bulan(bln),
                                size=11,
                                weight=ft.FontWeight.BOLD if aktif else ft.FontWeight.NORMAL,
                                color=WARNA["biru_tua"] if aktif else WARNA["teks_samar"],
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    )
                )

        banding = services.bandingkan_bulan_lalu(self.daftar)
        if banding is None:
            self.txt_banding.value = "Belum ada data bulan lalu untuk dibandingkan."
            self.txt_banding.color = WARNA["teks_samar"]
        else:
            selisih_kwh, selisih_biaya, persen, lalu = banding
            lebih_tinggi = selisih_kwh > 0
            tanda = "+" if selisih_biaya >= 0 else "-"
            self.txt_banding.value = (
                f"{abs(persen):.1%} {'lebih tinggi' if lebih_tinggi else 'lebih rendah'} "
                f"dari {nama_bulan(lalu)} ({tanda}{rupiah(abs(selisih_biaya))})."
            )
            self.txt_banding.color = WARNA["oranye"] if lebih_tinggi else WARNA["hijau"]

        self.kolom_terbaru.controls.clear()
        terbaru = services.urutkan_catatan(self.daftar, kolom="tanggal", naik=False)[:4]
        if not terbaru:
            self.kolom_terbaru.controls.append(
                ft.Text(
                    "Belum ada catatan pemakaian.", size=13, color=WARNA["teks_samar"]
                )
            )
        else:
            for c in terbaru:
                self.kolom_terbaru.controls.append(
                    ft.Container(
                        bgcolor=WARNA["latar"],
                        border_radius=10,
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                        content=ft.Row(
                            [
                                ft.Text(
                                    c.tanggal.isoformat(),
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    width=110,
                                ),
                                ft.Text(
                                    f"{c.pemakaian_kwh:.1f} kWh",
                                    size=13,
                                    color=WARNA["biru_tua"],
                                    weight=ft.FontWeight.BOLD,
                                    width=100,
                                ),
                                ft.Text(
                                    rupiah(c.estimasi_biaya),
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    width=120,
                                ),
                                ft.Text(
                                    c.catatan or "-",
                                    size=13,
                                    color=WARNA["teks_samar"],
                                    expand=True,
                                ),
                            ],
                        ),
                    )
                )

        # ID otomatis saja yang diperbarui; Tarif per kWh dibiarkan kosong
        self.in_id.value = str(services.buat_id_baru(self.daftar))

        rekap_semua = services.rekap_bulanan(self.daftar)
        self.peta_bulan = {nama_bulan_tahun(b): b for b, _, _ in rekap_semua}
        pilihan_bulan = [SEMUA_BULAN] + list(self.peta_bulan)
        self.dd_bulan.options = [ft.dropdown.Option(p) for p in pilihan_bulan]
        if self.filter_bulan not in pilihan_bulan:
            self.filter_bulan = SEMUA_BULAN
            self.dd_bulan.value = SEMUA_BULAN
        self._perbarui_tabel_riwayat()

        self.in_set_tarif.value = ""
        self.in_set_kwh.value = ""
        self.in_set_biaya.value = ""

        self.page.update()

    def _perbarui_tabel_riwayat(self):
        hasil = services.cari_kata_kunci(self.daftar, self.kata_cari)
        kunci_bln = self.peta_bulan.get(self.filter_bulan)
        if kunci_bln:
            hasil = services.filter_catatan(hasil, bulan=kunci_bln)
        hasil = services.urutkan_catatan(
            hasil, kolom=KOLOM_URUT[self.urut_kolom], naik=self.urut_naik
        )

        self.tabel_riwayat.rows.clear()
        for c in hasil:
            self.tabel_riwayat.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.id_pencatatan))),
                        ft.DataCell(ft.Text(c.tanggal.isoformat())),
                        ft.DataCell(ft.Text(nama_bulan_tahun(c.bulan))),
                        ft.DataCell(ft.Text(f"{c.pemakaian_kwh:.1f} kWh")),
                        ft.DataCell(ft.Text(rupiah(c.tarif_per_kwh))),
                        ft.DataCell(
                            ft.Text(rupiah(c.estimasi_biaya), weight=ft.FontWeight.W_600)
                        ),
                        ft.DataCell(ft.Text(c.catatan or "-")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_ROUNDED,
                                        icon_color=WARNA["biru"],
                                        tooltip="Edit",
                                        on_click=lambda _, item=c: self._buka_dialog_edit(
                                            item
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                        icon_color=WARNA["oranye"],
                                        tooltip="Hapus",
                                        on_click=lambda _, item=c: self._konfirmasi_hapus(
                                            item
                                        ),
                                    ),
                                ],
                                spacing=0,
                            )
                        ),
                    ]
                )
            )

        if not self.daftar:
            self.txt_ringkasan_riwayat.value = "Belum ada catatan pemakaian."
        elif not hasil:
            self.txt_ringkasan_riwayat.value = (
                "Tidak ada catatan yang cocok dengan pencarian atau filter."
            )
        else:
            total_kwh = services.hitung_total(hasil)
            total_biaya = services.hitung_total(hasil, atribut="estimasi_biaya")
            self.txt_ringkasan_riwayat.value = (
                f"Menampilkan {len(hasil)} dari {len(self.daftar)} catatan   |   "
                f"Total: {total_kwh:.1f} kWh   |   Estimasi Biaya: {rupiah(total_biaya)}"
            )


def main(page: ft.Page):
    HematEnergiFlet(page)