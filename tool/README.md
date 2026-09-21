# 🧭 CÔNG CỤ XÁC ĐỊNH RANH XÃ PHƯỜNG KHỚP VỚI KHU VỰC NGHIÊN CỨU (GIS TOOL)

Công cụ phần mềm chuyên dụng để phân tích không gian, tự động xác định ranh giới khu vực nghiên cứu (tập tin KMZ / KML) nằm trên / giao cắt với các xã, phường, thị trấn nào từ tập tin bản đồ ranh giới hành chính toàn quốc (KML / KMZ), đồng thời hiển thị bản đồ trực quan và xuất báo cáo Excel chuyên nghiệp.

---

## 🌟 Tính Năng Chính

1. **Giao diện đồ họa (GUI) trực quan & hiện đại**:
   - Chọn nhanh file KMZ/KML nghiên cứu và file KML/KMZ địa giới hành chính.
   - Thẻ thống kê KPI tức thì (Số xã/phường khớp, tỉnh thành, tổng số đối tượng placemarks, tọa độ phạm vi bounding box).
   - Bảng kết quả tương tác hỗ trợ tìm kiếm/lọc nhanh theo tên xã, mã xã hoặc tỉnh thành.
   - Bảng chi tiết từng đối tượng trong KMZ (Tua bin gió WTG, tuyến dây 500kV, polyline...) xem đối tượng đó nằm tại xã nào.
   - **Bản đồ không gian tích hợp (Interactive Map)**: Tô màu từng xã phường, gắn nhãn tên xã, hiển thị rõ ranh giới nghiên cứu với công cụ Phóng to / Thu nhỏ / Di chuyển / Lưu ảnh.

2. **Thuật toán phân tích không gian tốc độ cao**:
   - Tối ưu hóa xử lý file KML dung lượng lớn (~280 MB với hơn 3.300 xã phường toàn quốc) chỉ trong khoảng 30 giây.
   - Áp dụng kỹ thuật lọc Bounding Box và `shapely.prepared.prep` giúp tăng tốc độ kiểm tra giao cắt không gian gấp hàng chục lần.

3. **Xuất báo cáo Excel (`.xlsx`) đa tầng chuyên nghiệp**:
   - **Sheet 1 (`Xã Phường Giao Cắt`)**: Tổng hợp đầy đủ thông tin: Mã Xã, Tên Xã, Loại (Xã/Phường), Cấp, Mã Tỉnh, Tên Tỉnh, Diện tích (km²), Dân số, Mật độ (người/km²), Thông tin sáp nhập, Trụ sở UBND, Số lượng đối tượng dự án giao cắt.
   - **Sheet 2 (`Chi Tiết Đối Tượng`)**: Liệt kê từng đối tượng trong file nghiên cứu (STT, Tên đối tượng, Loại hình học, Xã/Phường tương ứng, Tọa độ tâm, Mô tả).
   - **Sheet 3 (`Thông Tin Tổng Quan`)**: Báo cáo tổng hợp siêu dữ liệu (Tên file, thời gian phân tích, phạm vi tọa độ kinh/vĩ độ...).
   - Định dạng bảng biểu chuẩn, màu sắc header chuyên nghiệp, hỗ trợ tự động căn lề và độ rộng cột.

---

## 🚀 Hướng Dẫn Sử Dụng

### Chuyển sang máy khác (bản portable)
- Gửi file `release\GIS_Khop_Ranh_Portable.zip`.
- Trên máy nhận, **giải nén toàn bộ** file ZIP, không chạy trực tiếp bên trong ZIP.
- Mở thư mục vừa giải nén và nhấp đúp `Chay_Cong_Cu.bat` (đuôi đúng là `.bat`, không phải `.pat`).
- Máy nhận không cần cài Python hoặc bất kỳ thư viện GIS nào. Chỉ dùng trên Windows 64-bit.

Để tạo lại gói sau khi thay đổi mã nguồn, chạy `build_portable.bat` trên máy lập trình có Python 3.10–3.12.

### Cách 1: Chạy bằng Giao diện (Khuyên dùng)
- Nhấp đúp chuột vào file [`run_tool.bat`](file:///D:/Documents/Ideasdrone/tool/run_tool.bat)
- Hoặc mở terminal và chạy:
  ```bash
  python main.py
  ```
- Nhấp **🚀 Bắt Đầu Phân Tích Không Gian**
- Sau khi hoàn thành, xem kết quả trên các Tab và nhấp **📊 Xuất Báo Cáo Excel (.xlsx)**.

### Cách 2: Chạy trực tiếp từ Dòng lệnh (CLI Automation)
```bash
python main.py --cli --study "MB CHUNG 2 DU AN CA CUM (1).kmz" --boundary "Việt Nam (phường xã) - 34.kml" --output "Ket_qua_khop_ranh_xa_phuong.xlsx"
```

---

## 📁 Cấu Trúc Tập Tin Dự Án

| Tên File / Thư mục | Chức năng |
| :--- | :--- |
| [`main.py`](file:///D:/Documents/Ideasdrone/tool/main.py) | Chương trình chính tích hợp giao diện PyQt5 và chế độ CLI |
| [`gis_engine.py`](file:///D:/Documents/Ideasdrone/tool/gis_engine.py) | Engine phân tích không gian, xử lý KMZ/KML, xuất và định dạng Excel |
| [`run_tool.bat`](file:///D:/Documents/Ideasdrone/tool/run_tool.bat) | File thực thi nhấp đúp để mở phần mềm trên Windows |
| [`Ket_qua_khop_ranh_xa_phuong.xlsx`](file:///D:/Documents/Ideasdrone/tool/Ket_qua_khop_ranh_xa_phuong.xlsx) | File Excel kết quả mẫu vừa được xuất tự động |
| [`preview_map.png`](file:///D:/Documents/Ideasdrone/tool/preview_map.png) | Ảnh bản đồ trực quan mẫu |
