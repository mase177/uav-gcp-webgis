import os
import sys
import argparse
import subprocess
import webbrowser
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QSplitter, QTextEdit, QCheckBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

# Matplotlib integration with PyQt5
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Import our GIS engine
from gis_engine import analyze_intersection, export_results_to_excel, dd_to_dms

# --- WORKER THREAD FOR ASYNC ANALYSIS ---
class AnalysisWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, study_file, boundary_file):
        super().__init__()
        self.study_file = study_file
        self.boundary_file = boundary_file

    def run(self):
        try:
            def callback(msg, pct):
                self.progress_signal.emit(msg, int(pct))

            results = analyze_intersection(self.study_file, self.boundary_file, callback)
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))


# --- STYLESHEET ---
APP_STYLE = """
QMainWindow {
    background-color: #F8FAFC;
}
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1E293B;
}
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px;
}
QFrame#kpi_card {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 10px;
}
QLabel#title {
    font-size: 18px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#subtitle {
    font-size: 12px;
    color: #64748B;
}
QLabel#kpi_num {
    font-size: 18px;
    font-weight: bold;
    color: #0284C7;
}
QLabel#kpi_label {
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
}
QLineEdit {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #FFFFFF;
    selection-background-color: #0284C7;
}
QLineEdit:focus {
    border: 1.5px solid #0284C7;
}
QPushButton {
    background-color: #0284C7;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #0369A1;
}
QPushButton:pressed {
    background-color: #075985;
}
QPushButton:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}
QPushButton#btn_secondary {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#btn_secondary:hover {
    background-color: #E2E8F0;
}
QPushButton#btn_success {
    background-color: #10B981;
    color: #FFFFFF;
}
QPushButton#btn_success:hover {
    background-color: #059669;
}
QPushButton#btn_maps {
    background-color: #EA580C;
    color: #FFFFFF;
}
QPushButton#btn_maps:hover {
    background-color: #C2410C;
}
QProgressBar {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    text-align: center;
    background-color: #E2E8F0;
    height: 18px;
    font-size: 11px;
    font-weight: bold;
    color: #1E293B;
}
QProgressBar::chunk {
    background-color: #0284C7;
    border-radius: 5px;
}
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background: #FFFFFF;
    border-radius: 8px;
}
QTabBar::tab {
    background: #F1F5F9;
    color: #475569;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0284C7;
    border: 1px solid #E2E8F0;
    border-bottom: 2px solid #0284C7;
}
QTableWidget {
    background-color: #FFFFFF;
    gridline-color: #F1F5F9;
    border: none;
    selection-background-color: #E0F2FE;
    selection-color: #0F172A;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #334155;
    padding: 6px 8px;
    border: none;
    border-bottom: 1.5px solid #CBD5E1;
    font-weight: bold;
}
QTextEdit {
    background-color: #0F172A;
    color: #38BDF8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 8px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Công Cụ Khớp Ranh Xã Phường & Khu Vực Nghiên Cứu (GIS Tool)")
        self.resize(1200, 850)
        self.setStyleSheet(APP_STYLE)
        
        self.analysis_results = None
        self.worker = None

        self.init_ui()
        self.load_default_paths()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header Card
        header_card = QFrame()
        header_card.setObjectName("card")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(8, 8, 8, 8)
        
        title_box = QVBoxLayout()
        title = QLabel("🧭 CÔNG CỤ XÁC ĐỊNH RANH XÃ PHƯỜNG & KHU VỰC NGHIÊN CỨU")
        title.setObjectName("title")
        subtitle = QLabel("Tự động phân tích không gian giữa ranh dự án (KMZ/KML) và dữ liệu hành chính 34 tỉnh thành Việt Nam, xuất báo cáo Excel chuẩn")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        h_layout.addLayout(title_box)
        h_layout.addStretch()

        btn_default = QPushButton("🔄 Nạp File Mặc Định")
        btn_default.setObjectName("btn_secondary")
        btn_default.clicked.connect(self.load_default_paths)
        h_layout.addWidget(btn_default)
        main_layout.addWidget(header_card)

        # 2. Input Files Card
        input_card = QFrame()
        input_card.setObjectName("card")
        grid = QGridLayout(input_card)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        # File 1: Study KMZ
        grid.addWidget(QLabel("<b>1. File Ranh Nghiên Cứu / Dự Án (KMZ/KML):</b>"), 0, 0)
        self.txt_study = QLineEdit()
        self.txt_study.setPlaceholderText("Chọn file KMZ hoặc KML chứa ranh giới khu vực nghiên cứu...")
        grid.addWidget(self.txt_study, 0, 1)
        btn_browse_study = QPushButton("📂 Chọn File...")
        btn_browse_study.setObjectName("btn_secondary")
        btn_browse_study.clicked.connect(self.browse_study_file)
        grid.addWidget(btn_browse_study, 0, 2)

        # File 2: Boundary KML
        grid.addWidget(QLabel("<b>2. File Ranh Xã Phường / Tỉnh Thành (KML/KMZ):</b>"), 1, 0)
        self.txt_boundary = QLineEdit()
        self.txt_boundary.setPlaceholderText("Chọn file KML hoặc KMZ ranh xã phường toàn quốc hoặc tỉnh thành...")
        grid.addWidget(self.txt_boundary, 1, 1)
        btn_browse_boundary = QPushButton("📂 Chọn File...")
        btn_browse_boundary.setObjectName("btn_secondary")
        btn_browse_boundary.clicked.connect(self.browse_boundary_file)
        grid.addWidget(btn_browse_boundary, 1, 2)

        # Action Buttons Row
        action_layout = QHBoxLayout()
        self.btn_run = QPushButton("🚀 Bắt Đầu Phân Tích Không Gian")
        self.btn_run.setFixedHeight(36)
        self.btn_run.clicked.connect(self.start_analysis)
        action_layout.addWidget(self.btn_run)

        self.btn_export = QPushButton("📊 Xuất Báo Cáo Excel (.xlsx)")
        self.btn_export.setObjectName("btn_success")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_excel)
        action_layout.addWidget(self.btn_export)

        self.btn_gmaps = QPushButton("🌐 Mở Google Maps Vị Trí Tâm")
        self.btn_gmaps.setObjectName("btn_maps")
        self.btn_gmaps.setFixedHeight(36)
        self.btn_gmaps.setEnabled(False)
        self.btn_gmaps.clicked.connect(self.open_google_maps)
        action_layout.addWidget(self.btn_gmaps)

        self.btn_open_folder = QPushButton("📁 Mở Thư Mục")
        self.btn_open_folder.setObjectName("btn_secondary")
        self.btn_open_folder.setFixedHeight(36)
        self.btn_open_folder.clicked.connect(self.open_current_directory)
        action_layout.addWidget(self.btn_open_folder)

        grid.addLayout(action_layout, 2, 0, 1, 3)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        grid.addWidget(self.progress_bar, 3, 0, 1, 3)

        self.lbl_status = QLabel("Sẵn sàng phân tích.")
        self.lbl_status.setStyleSheet("color: #64748B; font-style: italic;")
        grid.addWidget(self.lbl_status, 4, 0, 1, 3)

        main_layout.addWidget(input_card)

        # 3. KPI Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)
        
        self.card_kpi1 = self.create_kpi_card("SỐ XÃ / PHƯỜNG KHỚP", "0", "#0284C7")
        self.card_kpi2 = self.create_kpi_card("TỈNH / THÀNH PHỐ", "Chưa có", "#0F766E")
        self.card_kpi3 = self.create_kpi_card("TỔNG ĐỐI TƯỢNG KMZ", "0", "#7C3AED")
        self.card_kpi_center = self.create_kpi_card("📍 TỌA ĐỘ TÂM RANH DỰ ÁN", "Chưa xác định", "#D97706")
        self.card_kpi4 = self.create_kpi_card("PHẠM VI BOUNDING BOX", "---", "#334155")
        
        kpi_layout.addWidget(self.card_kpi1)
        kpi_layout.addWidget(self.card_kpi2)
        kpi_layout.addWidget(self.card_kpi3)
        kpi_layout.addWidget(self.card_kpi_center)
        kpi_layout.addWidget(self.card_kpi4)
        main_layout.addLayout(kpi_layout)

        # 4. Results Tab Widget
        self.tabs = QTabWidget()
        
        # Tab 1: Commune Table
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_search_box = QHBoxLayout()
        t1_search_box.addWidget(QLabel("🔍 Tìm kiếm xã/phường/tỉnh:"))
        self.txt_filter_communes = QLineEdit()
        self.txt_filter_communes.setPlaceholderText("Nhập tên xã, mã xã hoặc tỉnh thành...")
        self.txt_filter_communes.textChanged.connect(self.filter_commune_table)
        t1_search_box.addWidget(self.txt_filter_communes)
        t1_layout.addLayout(t1_search_box)

        self.table_communes = QTableWidget()
        self.table_communes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_communes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_communes.setAlternatingRowColors(True)
        t1_layout.addWidget(self.table_communes)
        self.tabs.addTab(tab1, "🏛️ Danh Sách Xã / Phường Giao Cắt")

        # Tab 2: Feature Breakdown Table
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        t2_search_box = QHBoxLayout()
        t2_search_box.addWidget(QLabel("🔍 Tìm đối tượng KMZ:"))
        self.txt_filter_features = QLineEdit()
        self.txt_filter_features.setPlaceholderText("Nhập tên đối tượng (WTG, Polyline, 500kV...)...")
        self.txt_filter_features.textChanged.connect(self.filter_feature_table)
        t2_search_box.addWidget(self.txt_filter_features)
        t2_layout.addLayout(t2_search_box)

        self.table_features = QTableWidget()
        self.table_features.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_features.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_features.setAlternatingRowColors(True)
        t2_layout.addWidget(self.table_features)
        self.tabs.addTab(tab2, "📍 Chi Tiết Đối Tượng Dự Án (KMZ)")

        # Tab 3: Interactive Map Preview
        tab3 = QWidget()
        t3_layout = QVBoxLayout(tab3)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        t3_layout.addWidget(self.toolbar)
        t3_layout.addWidget(self.canvas)
        self.tabs.addTab(tab3, "🗺️ Bản Đồ Trực Quan (Map View)")

        # Tab 4: Logs
        tab4 = QWidget()
        t4_layout = QVBoxLayout(tab4)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        t4_layout.addWidget(self.log_console)
        self.tabs.addTab(tab4, "📋 Nhật Ký Hoạt Động (Logs)")

        main_layout.addWidget(self.tabs, stretch=1)

    def create_kpi_card(self, label_text, default_val, color_code):
        card = QFrame()
        card.setObjectName("kpi_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        lbl_top = QLabel(label_text)
        lbl_top.setObjectName("kpi_label")
        layout.addWidget(lbl_top)

        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("kpi_num")
        lbl_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color_code};")
        lbl_val.setWordWrap(True)
        layout.addWidget(lbl_val)

        card.value_label = lbl_val
        return card

    def load_default_paths(self):
        default_dir = os.path.dirname(os.path.abspath(__file__))
        default_kmz = os.path.join(default_dir, "MB CHUNG 2 DU AN CA CUM (1).kmz")
        default_kml = os.path.join(default_dir, "Việt Nam (phường xã) - 34.kml")

        if os.path.exists(default_kmz):
            self.txt_study.setText(default_kmz)
        if os.path.exists(default_kml):
            self.txt_boundary.setText(default_kml)
        self.log("Đã tải đường dẫn file mặc định vào giao diện.")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {message}")

    def browse_study_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Ranh Nghiên Cứu", "",
            "Tập tin KMZ/KML (*.kmz *.kml);;Tất cả tập tin (*.*)"
        )
        if path:
            self.txt_study.setText(path)

    def browse_boundary_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Ranh Xã Phường / Tỉnh Thành", "",
            "Tập tin KML/KMZ (*.kml *.kmz);;Tất cả tập tin (*.*)"
        )
        if path:
            self.txt_boundary.setText(path)

    def start_analysis(self):
        study_path = self.txt_study.text().strip()
        boundary_path = self.txt_boundary.text().strip()

        if not study_path or not os.path.exists(study_path):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn file ranh nghiên cứu (KMZ/KML) hợp lệ.")
            return

        if not boundary_path or not os.path.exists(boundary_path):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn file ranh xã phường (KML/KMZ) hợp lệ.")
            return

        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.btn_gmaps.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Đang khởi động phân tích không gian...")
        self.log(f"Bắt đầu phân tích: File 1='{os.path.basename(study_path)}' | File 2='{os.path.basename(boundary_path)}'")

        self.worker = AnalysisWorker(study_path, boundary_path)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self.on_analysis_finished)
        self.worker.error_signal.connect(self.on_analysis_error)
        self.worker.start()

    def on_progress(self, msg, pct):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)
        self.log(msg)

    def on_analysis_finished(self, results):
        self.btn_run.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_gmaps.setEnabled(True)
        self.progress_bar.setValue(100)
        self.analysis_results = results
        
        matched_communes = results['matched_communes']
        study_features = results['study_features']
        bounds = results['bounds']
        center = results.get('center_info', {})

        # Update KPIs
        self.card_kpi1.value_label.setText(str(len(matched_communes)))
        provinces = list(set([c['ten_tinh'] for c in matched_communes if c.get('ten_tinh')]))
        self.card_kpi2.value_label.setText(", ".join(provinces) if provinces else "N/A")
        self.card_kpi3.value_label.setText(str(len(study_features)))
        
        center_text = f"Vĩ độ: {center.get('centroid_lat', 0):.6f}\nKinh độ: {center.get('centroid_lon', 0):.6f}\n({center.get('center_commune', '')})"
        self.card_kpi_center.value_label.setText(center_text)
        self.card_kpi4.value_label.setText(f"Lon: {bounds[0]:.3f}..{bounds[2]:.3f}\nLat: {bounds[1]:.3f}..{bounds[3]:.3f}")

        # Populate Tab 1: Communes Table
        self.populate_communes_table(matched_communes)

        # Populate Tab 2: Features Table
        self.populate_features_table(results['feature_breakdown'])

        # Render Tab 3: Map
        self.render_map(results)

        self.lbl_status.setText(f"✅ Phân tích hoàn tất! Đã tìm thấy {len(matched_communes)} xã/phường giao cắt.")
        self.log(f"Hoàn thành phân tích! Tâm dự án: {center.get('centroid_full_str', '')}")
        self.log(f"Khớp {len(matched_communes)} xã/phường thuộc {len(provinces)} tỉnh/thành.")
        
        QMessageBox.information(
            self, "Thành công",
            f"Đã phân tích xong!\n- Tọa độ tâm ranh nghiên cứu: {center.get('centroid_dd_str', '')}\n  ({center.get('centroid_dms_str', '')})\n- Thuộc địa bàn: {center.get('center_commune', '')}\n- Số xã/phường khớp: {len(matched_communes)}\n- Tổng đối tượng dự án: {len(study_features)}\n\nBạn có thể xem kết quả trực quan trên bản đồ hoặc bấm 'Xuất Báo Cáo Excel'."
        )

    def on_analysis_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"❌ Lỗi: {err_msg}")
        self.log(f"LỖI: {err_msg}")
        QMessageBox.critical(self, "Lỗi phân tích", f"Đã xảy ra lỗi trong quá trình xử lý:\n{err_msg}")

    def populate_communes_table(self, communes):
        headers = [
            "STT", "Tên Xã / Phường", "Loại", "Mã Xã", "Tỉnh / Thành", "Mã Tỉnh",
            "Tọa Độ Tâm Xã", "Số Đối Tượng Giao", "Diện Tích (km²)", "Dân Số", "Mật Độ (ng/km²)", "Sáp Nhập", "Trụ Sở"
        ]
        self.table_communes.setRowCount(len(communes))
        self.table_communes.setColumnCount(len(headers))
        self.table_communes.setHorizontalHeaderLabels(headers)

        for row, c in enumerate(communes):
            items = [
                str(row + 1),
                c.get('ten_xa', ''),
                c.get('loai', ''),
                c.get('ma_xa', ''),
                c.get('ten_tinh', ''),
                c.get('ma_tinh', ''),
                c.get('toa_do_tam_xa', ''),
                str(c.get('so_doi_tuong_giao', 0)),
                str(c.get('dtich_km2', '')),
                str(c.get('dan_so', '')),
                str(c.get('matdo_km2', '')),
                c.get('sap_nhap', ''),
                c.get('tru_so', '')
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(val)
                if col in (0, 3, 5, 6, 7, 8, 9, 10):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table_communes.setItem(row, col, item)

        self.table_communes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_communes.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_communes.horizontalHeader().setSectionResizeMode(11, QHeaderView.Stretch)

    def populate_features_table(self, features):
        headers = ["STT", "Tên Đối Tượng", "Loại Hình Học", "Xã / Phường Trực Thuộc", "Tỉnh / Thành", "Tọa Độ Tâm (Lon, Lat)", "Tọa Độ Tâm (DMS)", "Mô Tả"]
        self.table_features.setRowCount(len(features))
        self.table_features.setColumnCount(len(headers))
        self.table_features.setHorizontalHeaderLabels(headers)

        for row, f in enumerate(features):
            items = [
                str(f['STT']),
                str(f['Tên đối tượng']),
                str(f['Loại hình học']),
                str(f['Xã / Phường']),
                str(f['Tỉnh / Thành']),
                str(f['Tọa độ tâm (Kinh độ, Vĩ độ)']),
                str(f.get('Tọa độ tâm (Độ Phút Giây)', '')),
                str(f['Mô tả'])
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(val)
                if col in (0, 2, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table_features.setItem(row, col, item)

        self.table_features.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_features.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def filter_commune_table(self, text):
        query = text.lower().strip()
        for row in range(self.table_communes.rowCount()):
            match = False
            for col in range(self.table_communes.columnCount()):
                item = self.table_communes.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table_communes.setRowHidden(row, not match)

    def filter_feature_table(self, text):
        query = text.lower().strip()
        for row in range(self.table_features.rowCount()):
            match = False
            for col in range(self.table_features.columnCount()):
                item = self.table_features.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table_features.setRowHidden(row, not match)

    def render_map(self, results):
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        matched_communes = results['matched_communes']
        study_features = results['study_features']
        bounds = results['bounds']
        center = results.get('center_info', {})

        colors = ['#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3', '#fdb462', '#b3de69', '#fccde5']

        def plot_polygon(geom, fc, ec, label=None):
            if geom.geom_type == 'Polygon':
                x, y = geom.exterior.xy
                ax.fill(x, y, alpha=0.35, fc=fc, ec=ec, linewidth=1.5, label=label)
            elif geom.geom_type == 'MultiPolygon':
                first = True
                for p in geom.geoms:
                    x, y = p.exterior.xy
                    ax.fill(x, y, alpha=0.35, fc=fc, ec=ec, linewidth=1.5, label=label if first else None)
                    first = False
            elif geom.geom_type == 'GeometryCollection':
                for g in geom.geoms:
                    plot_polygon(g, fc, ec, label)

        # Plot communes
        for i, c in enumerate(matched_communes):
            col = colors[i % len(colors)]
            plot_polygon(c['geometry'], fc=col, ec='#1E3A8A', label=f"{c['ten_xa']} ({c['ten_tinh']})")
            
            # Commune centroid label
            cent = c['geometry'].centroid
            ax.text(
                cent.x, cent.y, c['ten_xa'],
                fontsize=10, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#CBD5E1", alpha=0.85)
            )

        # Plot study features
        for sf in study_features:
            geom = sf['geometry']
            if geom.geom_type == 'Point':
                ax.plot(geom.x, geom.y, 'o', color='#DC2626', markersize=5)
            elif geom.geom_type == 'LineString':
                x, y = geom.xy
                ax.plot(x, y, color='#DC2626', linewidth=1.5, alpha=0.85)
            elif geom.geom_type == 'Polygon':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='#DC2626', linewidth=1.5)
            elif geom.geom_type == 'GeometryCollection':
                for sub in geom.geoms:
                    if sub.geom_type == 'Point':
                        ax.plot(sub.x, sub.y, 'o', color='#DC2626', markersize=5)
                    elif sub.geom_type == 'LineString':
                        x, y = sub.xy
                        ax.plot(x, y, color='#DC2626', linewidth=1.5)

        # Plot Center Point Marker ⭐
        if 'centroid_lon' in center and 'centroid_lat' in center:
            c_lon = center['centroid_lon']
            c_lat = center['centroid_lat']
            ax.plot(c_lon, c_lat, marker='*', markersize=16, color='#FFD700', markeredgecolor='#B45309', markeredgewidth=2, label='Tọa Độ Tâm Dự Án (Centroid)', zorder=10)
            ax.annotate(
                f"⭐ TÂM DỰ ÁN\n({c_lon:.5f}, {c_lat:.5f})",
                xy=(c_lon, c_lat),
                xytext=(15, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.4", fc="#FEF3C7", ec="#D97706", linewidth=1.5),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2", color="#D97706", lw=1.5),
                fontsize=9,
                fontweight='bold',
                color="#92400E",
                zorder=11
            )

        # Bounds with margin
        minx, miny, maxx, maxy = bounds
        dx = max((maxx - minx) * 0.15, 0.02)
        dy = max((maxy - miny) * 0.15, 0.02)
        ax.set_xlim(minx - dx, maxx + dx)
        ax.set_ylim(miny - dy, maxy + dy)

        ax.set_title("Bản Đồ Không Gian Giao Cắt Ranh Nghiên Cứu và Địa Giới Xã Phường", fontsize=13, fontweight='bold', pad=12)
        ax.set_xlabel("Kinh độ (Longitude)")
        ax.set_ylabel("Vĩ độ (Latitude)")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='best', framealpha=0.9, fontsize=9)

        self.fig.tight_layout()
        self.canvas.draw()

    def open_google_maps(self):
        if self.analysis_results and 'center_info' in self.analysis_results:
            url = self.analysis_results['center_info'].get('google_maps_url')
            if url:
                webbrowser.open(url)

    def export_excel(self):
        if not self.analysis_results:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có kết quả phân tích để xuất.")
            return

        default_name = f"Ket_qua_khop_ranh_xa_phuong_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.join(default_dir, default_name)

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu Báo Cáo Excel", default_path,
            "Tập tin Excel (*.xlsx);;Tất cả tập tin (*.*)"
        )

        if not out_path:
            return

        try:
            study_name = os.path.basename(self.txt_study.text())
            boundary_name = os.path.basename(self.txt_boundary.text())
            export_results_to_excel(self.analysis_results, out_path, study_name, boundary_name)
            self.log(f"Đã xuất file Excel thành công: {out_path}")

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Xuất Excel Thành Công")
            msg_box.setText(f"File Excel đã được xuất thành công tại:\n{out_path}\n\nĐã bao gồm tọa độ tâm ranh nghiên cứu và liên kết Google Maps.\n\nBạn có muốn mở file ngay bây giờ không?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            ret = msg_box.exec_()

            if ret == QMessageBox.Yes:
                if sys.platform == 'win32':
                    os.startfile(out_path)
                elif sys.platform == 'darwin':
                    subprocess.call(('open', out_path))
                else:
                    subprocess.call(('xdg-open', out_path))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất Excel", f"Không thể xuất file Excel:\n{str(e)}")

    def open_current_directory(self):
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        if sys.platform == 'win32':
            os.startfile(curr_dir)
        elif sys.platform == 'darwin':
            subprocess.call(('open', curr_dir))
        else:
            subprocess.call(('xdg-open', curr_dir))


# --- CLI MODE ---
def run_cli(args):
    print("=" * 65)
    print(" CÔNG CỤ XÁC ĐỊNH RANH XÃ PHƯỜNG KHỚP VỚI KHU VỰC NGHIÊN CỨU")
    print("=" * 65)
    print(f"File 1 (Ranh nghiên cứu): {args.study}")
    print(f"File 2 (Ranh xã phường): {args.boundary}")
    print(f"File xuất Excel: {args.output}")
    print("-" * 65)

    def progress_callback(msg, pct):
        print(f"[{pct:3.0f}%] {msg}")

    t0 = datetime.now()
    results = analyze_intersection(args.study, args.boundary, progress_callback)
    
    study_name = os.path.basename(args.study)
    boundary_name = os.path.basename(args.boundary)
    export_results_to_excel(results, args.output, study_name, boundary_name)
    t1 = datetime.now()

    center = results.get('center_info', {})
    print("-" * 65)
    print(f"✅ THÀNH CÔNG! Thời gian xử lý: {(t1 - t0).total_seconds():.2f} giây.")
    print(f"📍 TỌA ĐỘ TÂM RANH NGHIÊN CỨU (CENTROID):")
    print(f"   • Thập phân (DD):  {center.get('centroid_dd_str', '')}")
    print(f"   • Độ Phút Giây:    {center.get('centroid_dms_str', '')}")
    print(f"   • Thuộc địa bàn:   {center.get('center_commune', '')}")
    print(f"   • Google Maps:     {center.get('google_maps_url', '')}")
    print("-" * 65)
    print(f"Số xã/phường giao cắt: {len(results['matched_communes'])}")
    for c in results['matched_communes']:
        print(f" - {c['ten_xa']} ({c['ten_tinh']}) | Mã xã: {c['ma_xa']} | Tâm xã: {c['toa_do_tam_xa']} | Số đối tượng giao: {c['so_doi_tuong_giao']}")
    print(f"File Excel kết quả: {os.path.abspath(args.output)}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Công cụ xác định ranh xã phường giao cắt với khu vực nghiên cứu.")
    parser.add_argument("--cli", action="store_true", help="Chạy chế độ dòng lệnh (không mở giao diện)")
    parser.add_argument("--study", default=r"D:\Documents\Ideasdrone\tool\MB CHUNG 2 DU AN CA CUM (1).kmz", help="Đường dẫn file KMZ/KML ranh nghiên cứu")
    parser.add_argument("--boundary", default=r"D:\Documents\Ideasdrone\tool\Việt Nam (phường xã) - 34.kml", help="Đường dẫn file KML/KMZ ranh xã phường")
    parser.add_argument("--output", default=r"D:\Documents\Ideasdrone\tool\Ket_qua_khop_ranh_xa_phuong.xlsx", help="Đường dẫn file Excel đầu ra")

    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
