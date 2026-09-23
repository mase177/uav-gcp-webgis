# UAV GCP WebGIS

Prototype WebGIS cho đề tài **Applying artificial intelligence to automatically optimize ground control point placement based on accessibility for UAV image surveys**.

Luồng nghiên cứu cốt lõi là:

```text
AOI + mạng đường → Candidate GCP → Genetic Algorithm → đánh giá → routing → WebGIS
```
## Cấu trúc

```text
uav_gcp_webgis/
├── backend/app/
│   ├── api/routes/          # areas, gcps, optimization, routing
│   ├── core/config.py       # đường dẫn và giới hạn an toàn
│   ├── services/
│   │   ├── spatial.py       # candidate, coverage, uniformity, accessibility
│   │   ├── optimizer.py     # GA, random/grid/spatial-only baselines
│   │   └── routing.py       # nearest-neighbour + 2-opt field route
│   ├── schemas.py
│   └── main.py
├── frontend/                # Leaflet UI, không cần npm build
├── data/cambay/CAMBAY.kmz    # lớp cấm/hạn chế bay do người dùng cung cấp
├── tests/                   # kiểm thử candidate và GA
├── requirements.txt
└── run.py
```

## Chạy ứng dụng

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Mở `http://127.0.0.1:8001`. API docs có tại `http://127.0.0.1:8001/docs`.

## PostgreSQL/PostGIS

WebGIS dùng database riêng `uav_gcp_webgis` trên PostgreSQL/PostGIS. Chuỗi kết nối cục bộ được đặt trong `.env`; không đưa mật khẩu vào source code. Cài dependencies mới rồi khởi động lại ứng dụng:

```bash
pip install -r requirements.txt
python run.py
```

Schema `uav` gồm dữ liệu nghiệp vụ UAV: `survey_projects`, `survey_areas`, `road_networks`, `airspace_zones`, `optimization_runs`, `control_points` và `survey_routes`.

Ba lớp chỉ tham chiếu từ SCM cũ đã được chép sang database mới: `field_access_constraints` (3 vùng hạn chế xe), `legacy_logistics_routes` (5 tuyến) và `legacy_route_segments` (13 đoạn). Chúng không được dùng thay thế mạng đường thực tế trong GA.

## Cách thử nghiệm

1. Chọn **Nhập vùng bay / dữ liệu khảo sát** rồi nạp Shapefile ZIP, GeoJSON, KML/KMZ hoặc nhập tọa độ WGS84. Sau mỗi lần nạp, bản đồ tự zoom đến phạm vi dữ liệu. Polygon được nhận là AOI, LineString là mạng đường, điểm có tên `CP` hoặc `Check Point` được nhận là Check Point; các điểm còn lại là GCP.
2. Chọn **Vẽ polygon AOI** để tạo khu vực khảo sát, hoặc **Ghim GCP trực tiếp** để lập phương án thủ công.
3. Chọn loại định vị ảnh (**RTK**, **PPK** hoặc **không RTK/PPK**), độ chính xác yêu cầu, địa hình, độ cao bay, GSD và chồng phủ. Khi đã có AOI và mạng đường, WebGIS đưa ra khuyến nghị số GCP, số Check Point tối thiểu và bước lưới Candidate; người dùng có thể áp dụng hoặc tự điều chỉnh.
4. Sau khi có AOI, bấm **Chạy tối ưu GA**. WebGIS tự nạp nền mạng đường OpenStreetMap để đánh giá tiếp cận và lập chỉ đường; mạng đường không cần hiển thị hoặc tải thủ công. Với AOI rộng, hệ thống tự chia thành các ô truy vấn nhỏ rồi gộp dữ liệu đường; có thể thay bằng KML/GeoJSON đường do người dùng cung cấp khi không có Internet.
5. Chạy GA để nhận cấu hình GCP, fitness và các baseline so sánh. Mọi điểm thuộc AOI đều là ứng viên; khoảng cách đến đường là điểm ưu tiên liên tục, không phải điều kiện loại bỏ điểm. Theo cấu hình định vị, GA tự điều chỉnh trọng số fitness: UAV không RTK ưu tiên coverage/uniformity hơn; RTK ưu tiên thêm khả năng tiếp cận, nhưng vẫn giữ ràng buộc phân bố không gian. Khi GA hoàn tất, WebGIS tự tối ưu thứ tự khảo sát từ GCP 1, hiển thị thứ tự ghé các điểm và tuyến trên đường. Có thể chọn ô tô hoặc xe máy; thời gian xe máy là ước tính tham khảo và cần kiểm tra đường cấm xe máy.
6. Ghim **Check Point (CP)** bằng ghim xanh để kiểm tra độc lập độ chính xác. GCP hiển thị bằng ghim vàng. CP được xuất cùng GCP và có thể được tính vào tuyến khảo sát.
7. Có thể bấm **Lập tuyến khảo sát theo OSM** để tính lại tuyến sau khi thêm/bớt GCP hoặc CP. Nếu OSRM không phản hồi, hệ thống hiển thị rõ đây là tuyến khoảng cách thẳng ước lượng, không phải tuyến thực tế.

Khi chạy qua FastAPI, WebGIS tự nạp `data/cambay/CAMBAY.kmz`: vùng **cấm bay** màu đỏ và vùng **hạn chế bay** màu vàng. Đây là lớp cảnh báo điều kiện vận hành UAV; không được dùng để tự loại các GCP mặt đất khỏi thuật toán GA.

## Ranh giới bay và thông tin hỗ trợ hồ sơ

AOI được dùng làm **ranh giới bay dự kiến**. Sau khi hoàn tất AOI, phần **Ranh giới bay & hồ sơ** trên WebGIS cho phép:

1. Tự động khớp AOI với tệp `data/Ranh_Vietnam/Việt Nam (phường xã) - 34.kml` và trả về/hiển thị riêng các xã, phường giao cắt. Tệp toàn quốc gần 280 MB luôn được xử lý tại máy chủ, không tải về trình duyệt. Chức năng này chuyển quy trình khớp ranh của thư mục `tool/` sang thao tác WebGIS.
2. Kiểm tra AOI giao cắt các vùng cấm/hạn chế trong lớp `CAMBAY.kmz` đã nạp.
3. Xuất `ranh_bay_du_kien.kml` và `phieu_thong_tin_ranh_bay.html`, gồm diện tích, tọa độ tâm, phạm vi tọa độ, địa bàn giao cắt và kết quả sàng lọc lớp CAMBAY.

Các tệp xuất ra chỉ hỗ trợ chuẩn bị thông tin kỹ thuật. Chúng không phải giấy phép bay, không xác nhận điều kiện pháp lý và cần được đối chiếu với nguồn chính thức/cơ quan có thẩm quyền tại thời điểm vận hành.

## Các chỉ số trong fitness

`fitness = w1·coverage + w2·uniformity + w3·edge_interior + w4·accessibility`

- **coverage**: tỷ lệ mẫu trong AOI có GCP gần trong bán kính phủ.
- **uniformity**: độ ổn định của khoảng cách đến GCP lân cận.
- **edge_interior**: cân bằng GCP vùng biên và vùng trong.
- **accessibility**: mức độ thuận lợi để đi từ đường đến GCP, tính giảm dần theo khoảng cách đến mạng đường OSM hoặc mạng đường do người dùng nạp. Chỉ số này ưu tiên điểm dễ tiếp cận nhưng không loại bỏ điểm cần thiết cho độ phủ không gian. Thời gian tiếp cận đầy đủ theo road graph là bước nâng cấp tiếp theo.

Các baseline gồm trung bình random, bố trí lan tỏa không gian và bản spatial-only. Đây là dữ liệu cần so sánh kỹ trong báo cáo môn AI.

## Cấu hình RTK/PPK và GCP

RTK/PPK làm tăng độ tin cậy tọa độ tâm ảnh, vì vậy WebGIS có thể đề xuất ít GCP hơn hoặc bước lưới Candidate thưa hơn so với chuyến bay không RTK/PPK. Đây chỉ là khuyến nghị lập kế hoạch, không phải quy tắc khoảng cách GCP cố định. Địa hình, độ chính xác yêu cầu, GSD và chồng phủ vẫn được đưa vào cấu hình để điều chỉnh khuyến nghị. Mọi phương án phải có Check Point độc lập; chỉ số RMSE từ quá trình xử lý ảnh UAV mới là cơ sở kết luận độ chính xác.

## Hướng mở rộng có kiểm soát

- Nạp OSM theo AOI và thay heuristic tuyến đi bằng shortest path trên road graph.
- Lưu `survey_area`, `optimization_run`, `gcp` và trạng thái khảo sát bằng PostGIS chỉ khi cần cộng tác/persistence.
- Bổ sung dữ liệu UAV/GCP thực địa để kiểm chứng tác động đến độ chính xác photogrammetry.
- Thêm assistant ngôn ngữ tự nhiên sau khi API tối ưu ổn định.
