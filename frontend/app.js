const map = L.map("map", { zoomControl: false }).setView([16.1, 107.8], 6);
L.control.zoom({ position: "bottomright" }).addTo(map);
const baseMap = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 20,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

function controlPinIcon(type, label) {
  return L.divIcon({
    className: "control-pin-container",
    html: `<div class="control-pin ${type}"><span>${label}</span></div>`,
    iconSize: [30, 36],
    iconAnchor: [15, 35],
  });
}

const gcpPinIcon = controlPinIcon("gcp-pin", "GCP");
const checkPointPinIcon = controlPinIcon("check-point-pin", "CP");

const layers = {
  roads: L.geoJSON(null, { style: { color: "#68758b", weight: 3 } }).addTo(map),
  aoi: L.geoJSON(null, { style: { color: "#1256d9", weight: 2, fillColor: "#6198ff", fillOpacity: 0.12 } }).addTo(map),
  adminBoundaries: L.geoJSON(null, {
    style: { color: "#7c3aed", weight: 1.3, dashArray: "4 4", fillColor: "#a78bfa", fillOpacity: 0.04 },
    onEachFeature: (feature, layer) => layer.bindPopup(`<div class="airspace-popup"><strong>Ranh hành chính</strong>${feature.properties?.name || "Không tên"}</div>`),
  }).addTo(map),
  drawing: L.layerGroup().addTo(map),
  noFlyZones: L.geoJSON(null, {
    style: (feature) => feature.properties?.zone_type === "prohibited"
      ? { color: "#dc2626", weight: 2.5, fillColor: "#ef4444", fillOpacity: 0.22 }
      : { color: "#d97706", weight: 2.5, fillColor: "#f59e0b", fillOpacity: 0.18 },
    onEachFeature: (feature, layer) => {
      const properties = feature.properties || {};
      layer.bindPopup(`<div class="airspace-popup"><strong>${properties.label || "Khu vực bay"}</strong>${properties.name || ""}<br><small>Nguồn: CAMBAY.kmz</small></div>`);
    },
  }).addTo(map),
  candidates: L.geoJSON(null, { pointToLayer: (_, latlng) => L.circleMarker(latlng, { radius: 3, color: "#8792a5", weight: 1, fillOpacity: 0.35 }) }).addTo(map),
  selected: L.geoJSON(null, { pointToLayer: (feature, latlng) => L.marker(latlng, { icon: gcpPinIcon }).bindTooltip(feature.id, { direction: "top" }) }).addTo(map),
  checkPoints: L.geoJSON(null, { pointToLayer: (feature, latlng) => L.marker(latlng, { icon: checkPointPinIcon }).bindTooltip(feature.id, { direction: "top" }) }).addTo(map),
  route: L.geoJSON(null, { style: { color: "#e16b20", weight: 4, dashArray: "7 6" } }).addTo(map),
};

const state = { aoi: null, roads: null, drawing: [], roadDrawing: [], noFlyZones: null, adminBoundaries: null, flightBoundaryAssessment: null, selectedGcps: null, manualGcps: [], checkPoints: [], surveyProfile: null, mode: "aoi" };
const status = document.querySelector("#status");
const metrics = document.querySelector("#metrics");
const byId = (id) => document.querySelector(`#${id}`);

const layerDefinitions = [
  { id: "basemap", label: "Bản đồ nền OpenStreetMap", layer: baseMap, swatch: "base" },
  { id: "aoi", label: "Vùng khảo sát (AOI)", layer: layers.aoi, swatch: "aoi" },
  { id: "adminBoundaries", label: "Ranh hành chính nạp vào", layer: layers.adminBoundaries, swatch: "admin" },
  { id: "roads", label: "Mạng đường / tiếp cận", layer: layers.roads, swatch: "roads" },
  { id: "noFlyZones", label: "Vùng cấm / hạn chế bay", layer: layers.noFlyZones, swatch: "airspace" },
  { id: "candidates", label: "Điểm GCP ứng viên", layer: layers.candidates, swatch: "candidate" },
  { id: "selected", label: "GCP đã chọn / ghim", layer: layers.selected, swatch: "gcp" },
  { id: "checkPoints", label: "Check Point", layer: layers.checkPoints, swatch: "cp" },
  { id: "route", label: "Tuyến khảo sát", layer: layers.route, swatch: "route" },
];

function layerFeatureCount(layer) {
  return layer.getLayers ? layer.getLayers().length : 0;
}

function refreshLayerPanel() {
  layerDefinitions.forEach(({ id, layer }) => {
    const input = byId(`layer-${id}`);
    const count = byId(`layer-count-${id}`);
    if (input) input.checked = map.hasLayer(layer);
    if (count) {
      const featureCount = layerFeatureCount(layer);
      count.textContent = id === "basemap" ? "nền" : featureCount ? String(featureCount) : "trống";
    }
  });
}

const layerPanel = L.control({ position: "topright" });
layerPanel.onAdd = () => {
  const container = L.DomUtil.create("section", "leaflet-control layer-panel");
  container.setAttribute("aria-label", "Lớp dữ liệu và chú thích bản đồ");
  container.innerHTML = `
    <button class="layer-panel-title" type="button" aria-expanded="true">LỚP DỮ LIỆU <span aria-hidden="true">−</span></button>
    <div class="layer-panel-content">
      <p class="layer-panel-note">Bật hoặc tắt lớp đang hiển thị</p>
      ${layerDefinitions.map(({ id, label, swatch }) => `
        <label class="map-layer-row"><input id="layer-${id}" type="checkbox" checked />
          <span class="map-swatch ${swatch}"></span><span class="map-layer-label">${label}</span><small id="layer-count-${id}"></small>
        </label>`).join("")}
      <div class="map-legend-box">
        <strong>Chú thích</strong>
        <span><i class="map-swatch gcp"></i>GCP — ghim vàng</span>
        <span><i class="map-swatch cp"></i>Check Point — ghim xanh</span>
        <span><i class="map-swatch airspace"></i>Đỏ: cấm · Cam: hạn chế</span>
      </div>
    </div>`;
  L.DomEvent.disableClickPropagation(container);
  L.DomEvent.disableScrollPropagation(container);
  return container;
};
layerPanel.addTo(map);

document.querySelector(".layer-panel-title").addEventListener("click", (event) => {
  const button = event.currentTarget;
  const content = button.nextElementSibling;
  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!expanded));
  button.lastElementChild.textContent = expanded ? "+" : "−";
  content.hidden = expanded;
});

layerDefinitions.forEach(({ id, layer }) => {
  byId(`layer-${id}`).addEventListener("change", (event) => {
    if (event.target.checked) layer.addTo(map);
    else map.removeLayer(layer);
    if (id === "noFlyZones") byId("toggle-no-fly").checked = event.target.checked;
  });
});

function setStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

async function loadNoFlyZones() {
  try {
    const response = await fetch("/api/no-fly-zones");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Không thể nạp vùng cấm bay.");
    state.noFlyZones = data.zones;
    layers.noFlyZones.clearLayers().addData(data.zones);
    refreshLayerPanel();
    setStatus(`Đã nạp ${data.zone_count} vùng cấm/hạn chế bay từ CAMBAY.kmz. Lớp này dùng để cảnh báo điều kiện bay UAV.`);
  } catch (error) {
    setStatus(error.message || "Không thể nạp lớp vùng cấm bay.", true);
  }
}

function aoiFeature(points) {
  const closed = [...points, points[0]];
  return { type: "Feature", properties: { name: "User AOI" }, geometry: { type: "Polygon", coordinates: [closed] } };
}

function renderAOI() {
  layers.aoi.clearLayers(); layers.drawing.clearLayers();
  if (state.aoi) {
    layers.aoi.addData(state.aoi);
  } else {
    state.drawing.forEach((coordinate, index) => {
      L.circleMarker([coordinate[1], coordinate[0]], { radius: 5, color: "#1256d9", weight: 2, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(`Đỉnh AOI ${index + 1}`, { direction: "top" }).addTo(layers.drawing);
    });
    if (state.drawing.length > 1) {
      L.polyline(state.drawing.map(([lon, lat]) => [lat, lon]), { color: "#1256d9", weight: 2, dashArray: "6 5" }).addTo(layers.drawing);
    }
  }
  state.roadDrawing.forEach((coordinate, index) => {
    L.circleMarker([coordinate[1], coordinate[0]], { radius: 4, color: "#68758b", weight: 2, fillColor: "#fff", fillOpacity: 1 })
      .bindTooltip(`Đỉnh đường ${index + 1}`, { direction: "top" }).addTo(layers.drawing);
  });
  if (state.roadDrawing.length > 1) {
    L.polyline(state.roadDrawing.map(([lon, lat]) => [lat, lon]), { color: "#68758b", weight: 3, dashArray: "6 5" }).addTo(layers.drawing);
  }
  refreshLayerPanel();
  updateFlightBoundaryControls();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

function geometryRings(geometry) {
  if (geometry?.type === "Polygon") return geometry.coordinates?.slice(0, 1) || [];
  if (geometry?.type === "MultiPolygon") return (geometry.coordinates || []).flatMap((polygon) => polygon.slice(0, 1));
  return [];
}

function ringBounds(ring) {
  const longitudes = ring.map(([longitude]) => longitude);
  const latitudes = ring.map(([, latitude]) => latitude);
  return [Math.min(...longitudes), Math.min(...latitudes), Math.max(...longitudes), Math.max(...latitudes)];
}

function boundsOverlap(first, second) {
  return first[0] <= second[2] && first[2] >= second[0] && first[1] <= second[3] && first[3] >= second[1];
}

function pointOnSegment(point, start, end) {
  const [x, y] = point; const [x1, y1] = start; const [x2, y2] = end;
  const cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1);
  if (Math.abs(cross) > 1e-10) return false;
  return x >= Math.min(x1, x2) - 1e-10 && x <= Math.max(x1, x2) + 1e-10 && y >= Math.min(y1, y2) - 1e-10 && y <= Math.max(y1, y2) + 1e-10;
}

function orientation(first, second, third) {
  return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0]);
}

function segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd) {
  const first = orientation(firstStart, firstEnd, secondStart);
  const second = orientation(firstStart, firstEnd, secondEnd);
  const third = orientation(secondStart, secondEnd, firstStart);
  const fourth = orientation(secondStart, secondEnd, firstEnd);
  if (((first > 0 && second < 0) || (first < 0 && second > 0)) && ((third > 0 && fourth < 0) || (third < 0 && fourth > 0))) return true;
  return (Math.abs(first) < 1e-10 && pointOnSegment(secondStart, firstStart, firstEnd))
    || (Math.abs(second) < 1e-10 && pointOnSegment(secondEnd, firstStart, firstEnd))
    || (Math.abs(third) < 1e-10 && pointOnSegment(firstStart, secondStart, secondEnd))
    || (Math.abs(fourth) < 1e-10 && pointOnSegment(firstEnd, secondStart, secondEnd));
}

function pointInRing(point, ring) {
  let inside = false;
  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
    const currentPoint = ring[index]; const previousPoint = ring[previous];
    if (pointOnSegment(point, currentPoint, previousPoint)) return true;
    const crosses = (currentPoint[1] > point[1]) !== (previousPoint[1] > point[1]);
    if (crosses && point[0] < (previousPoint[0] - currentPoint[0]) * (point[1] - currentPoint[1]) / (previousPoint[1] - currentPoint[1]) + currentPoint[0]) inside = !inside;
  }
  return inside;
}

function ringsIntersect(firstRing, secondRing) {
  if (!boundsOverlap(ringBounds(firstRing), ringBounds(secondRing))) return false;
  for (let index = 0; index < firstRing.length - 1; index += 1) {
    for (let otherIndex = 0; otherIndex < secondRing.length - 1; otherIndex += 1) {
      if (segmentsIntersect(firstRing[index], firstRing[index + 1], secondRing[otherIndex], secondRing[otherIndex + 1])) return true;
    }
  }
  return pointInRing(firstRing[0], secondRing) || pointInRing(secondRing[0], firstRing);
}

function featuresIntersect(firstFeature, secondFeature) {
  const firstRings = geometryRings(firstFeature?.geometry);
  const secondRings = geometryRings(secondFeature?.geometry);
  return firstRings.some((firstRing) => secondRings.some((secondRing) => ringsIntersect(firstRing, secondRing)));
}

function polygonAreaM2(feature) {
  return geometryRings(feature?.geometry).reduce((total, ring) => {
    const averageLatitude = ring.reduce((sum, [, latitude]) => sum + latitude, 0) / ring.length;
    const longitudeFactor = 111_320 * Math.cos(averageLatitude * Math.PI / 180);
    const latitudeFactor = 110_540;
    let twiceArea = 0;
    for (let index = 0; index < ring.length - 1; index += 1) {
      const [longitude, latitude] = ring[index]; const [nextLongitude, nextLatitude] = ring[index + 1];
      twiceArea += (longitude * longitudeFactor) * (nextLatitude * latitudeFactor) - (nextLongitude * longitudeFactor) * (latitude * latitudeFactor);
    }
    return total + Math.abs(twiceArea) / 2;
  }, 0);
}

function formatDms(value, isLatitude) {
  const direction = value < 0 ? (isLatitude ? "S" : "W") : (isLatitude ? "B" : "Đ");
  const absolute = Math.abs(value); const degrees = Math.floor(absolute); const minutesRaw = (absolute - degrees) * 60;
  return `${degrees}°${Math.floor(minutesRaw)}′${((minutesRaw % 1) * 60).toFixed(2)}″ ${direction}`;
}

function resetFlightBoundaryAssessment() {
  state.flightBoundaryAssessment = null;
  byId("flight-boundary-result").hidden = true;
  byId("flight-boundary-result").innerHTML = "";
  byId("export-flight-kml").disabled = true;
  byId("export-flight-brief").disabled = true;
}

function updateFlightBoundaryControls() {
  byId("check-flight-boundary").disabled = !state.aoi;
}

async function loadAdministrativeMatches() {
  if (window.location.protocol === "file:") throw new Error("Hãy chạy WebGIS qua FastAPI để tự khớp ranh hành chính.");
  const response = await fetch("/api/flight-boundaries/administrative-match", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aoi: state.aoi }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Không thể kiểm tra ranh hành chính.");
  state.adminBoundaries = data.matches;
  layers.adminBoundaries.clearLayers().addData(data.matches);
  refreshLayerPanel();
  return { features: data.matches.features || [], source: data.source };
}

async function checkFlightBoundary() {
  if (!state.aoi) return setStatus("Hãy hoàn tất AOI trước khi kiểm tra ranh bay.", true);
  setStatus("Đang khớp AOI với dữ liệu xã/phường toàn quốc...");
  let administrativeMatches = [];
  let administrativeDetail = "";
  try {
    const result = await loadAdministrativeMatches();
    administrativeMatches = result.features;
  } catch (error) {
    state.adminBoundaries = null;
    layers.adminBoundaries.clearLayers();
    refreshLayerPanel();
    administrativeDetail = error.message || "Không thể tự khớp ranh hành chính.";
  }
  const airspaceMatches = (state.noFlyZones?.features || []).filter((feature) => featuresIntersect(state.aoi, feature));
  const bounds = L.geoJSON(state.aoi).getBounds();
  const center = bounds.getCenter();
  const areaM2 = polygonAreaM2(state.aoi);
  const prohibited = airspaceMatches.filter((feature) => feature.properties?.zone_type === "prohibited");
  state.flightBoundaryAssessment = { administrativeMatches, airspaceMatches, prohibited, bounds, center, areaM2 };
  const localityText = administrativeDetail
    ? escapeHtml(administrativeDetail)
    : administrativeMatches.length
      ? administrativeMatches.map((feature) => escapeHtml(feature.properties?.name || "Địa bàn không tên")).join(", ")
      : "Không phát hiện giao cắt với dữ liệu ranh hành chính toàn quốc.";
  if (administrativeDetail) {
    // The status in the exported brief must retain why an administrative match is unavailable.
    state.flightBoundaryAssessment.administrativeDetail = administrativeDetail;
  }
  const airspaceText = !state.noFlyZones
    ? "<li class=\"unavailable\">Chưa nạp được lớp CAMBAY. Hãy chạy WebGIS qua FastAPI rồi kiểm tra lại.</li>"
    : airspaceMatches.length
      ? airspaceMatches.map((feature) => `<li class="${feature.properties?.zone_type === "prohibited" ? "prohibited" : "restricted"}">${escapeHtml(feature.properties?.label || "Khu vực bay")}: ${escapeHtml(feature.properties?.name || "Không tên")}</li>`).join("")
      : "<li class=\"clear\">Không phát hiện giao cắt với lớp CAMBAY đang nạp.</li>";
  byId("flight-boundary-result").hidden = false;
  byId("flight-boundary-result").innerHTML = `
    <strong>${prohibited.length ? "Cần rà soát: AOI giao cắt khu vực cấm bay" : "Tóm tắt ranh giới bay dự kiến"}</strong>
    <dl><dt>Diện tích AOI</dt><dd>${(areaM2 / 10_000).toFixed(2)} ha</dd><dt>Tọa độ tâm</dt><dd>${formatDms(center.lat, true)}; ${formatDms(center.lng, false)}</dd><dt>Địa bàn giao cắt</dt><dd>${localityText}</dd></dl>
    <p class="boundary-result-title">Kiểm tra lớp cấm/hạn chế hiện có</p><ul>${airspaceText}</ul>`;
  byId("export-flight-kml").disabled = false;
  byId("export-flight-brief").disabled = false;
  setStatus(prohibited.length ? "AOI giao cắt vùng cấm bay trong lớp dữ liệu hiện có. Không sử dụng kết quả này để xác nhận điều kiện pháp lý." : administrativeDetail ? `Đã kiểm tra ranh bay, nhưng ${administrativeDetail}` : "Đã kiểm tra ranh bay dự kiến. Có thể xuất KML và phiếu thông tin hỗ trợ hồ sơ.", prohibited.length > 0 || Boolean(administrativeDetail));
}

function downloadText(filename, content, mimeType) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const link = Object.assign(document.createElement("a"), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}

function exportFlightKml() {
  if (!state.aoi) return;
  const polygons = geometryRings(state.aoi.geometry).map((ring, index) => `<Placemark><name>Ranh bay dự kiến ${index + 1}</name><Polygon><outerBoundaryIs><LinearRing><coordinates>${ring.map(([longitude, latitude]) => `${longitude},${latitude},0`).join(" ")}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>`).join("");
  downloadText("ranh_bay_du_kien.kml", `<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Ranh bay dự kiến UAV</name>${polygons}</Document></kml>`, "application/vnd.google-earth.kml+xml");
}

function exportFlightBrief() {
  const result = state.flightBoundaryAssessment;
  if (!result) return;
  const localities = result.administrativeDetail || (result.administrativeMatches.length ? result.administrativeMatches.map((feature) => feature.properties?.name || "Địa bàn không tên").join(", ") : "Không phát hiện giao cắt với dữ liệu ranh hành chính toàn quốc");
  const zones = !state.noFlyZones ? "Chưa nạp được lớp CAMBAY; cần kiểm tra lại khi chạy qua FastAPI" : result.airspaceMatches.length ? result.airspaceMatches.map((feature) => `${feature.properties?.label || "Khu vực bay"}: ${feature.properties?.name || "Không tên"}`).join("; ") : "Không phát hiện giao cắt với lớp CAMBAY đang nạp";
  const html = `<!doctype html><html lang="vi"><meta charset="utf-8"><title>Phiếu thông tin ranh bay UAV</title><style>body{max-width:760px;margin:40px auto;font:14px/1.55 Arial;color:#172033}h1{font-size:22px}dt{font-weight:bold}dd{margin:0 0 12px}.notice{padding:12px;background:#fff5db;border-left:4px solid #d97706}</style><h1>PHIẾU THÔNG TIN RANH GIỚI BAY DỰ KIẾN</h1><dl><dt>Thời điểm tạo</dt><dd>${new Date().toLocaleString("vi-VN")}</dd><dt>Diện tích AOI</dt><dd>${(result.areaM2 / 10_000).toFixed(2)} ha</dd><dt>Tọa độ tâm</dt><dd>${formatDms(result.center.lat, true)}; ${formatDms(result.center.lng, false)}</dd><dt>Phạm vi tọa độ</dt><dd>${result.bounds.getWest().toFixed(6)}, ${result.bounds.getSouth().toFixed(6)} — ${result.bounds.getEast().toFixed(6)}, ${result.bounds.getNorth().toFixed(6)}</dd><dt>Địa bàn hành chính giao cắt</dt><dd>${escapeHtml(localities)}</dd><dt>Kết quả kiểm tra lớp cấm/hạn chế</dt><dd>${escapeHtml(zones)}</dd></dl><p class="notice">Tài liệu này là phiếu thông tin kỹ thuật hỗ trợ chuẩn bị hồ sơ. Không phải giấy phép bay, không thay thế xác nhận của cơ quan có thẩm quyền và phải được đối chiếu với nguồn dữ liệu chính thức tại thời điểm vận hành.</p></html>`;
  downloadText("phieu_thong_tin_ranh_bay.html", html, "text/html;charset=utf-8");
}

function resetResults() {
  layers.candidates.clearLayers(); layers.selected.clearLayers(); layers.checkPoints.clearLayers(); layers.route.clearLayers();
  state.selectedGcps = null; state.manualGcps = []; state.checkPoints = []; metrics.innerHTML = "";
  updateControlActions();
  refreshLayerPanel();
}

function setMode(mode) {
  state.mode = mode;
  byId("mode-aoi").classList.toggle("active", mode === "aoi");
  byId("mode-road").classList.toggle("active", mode === "road");
  byId("mode-gcp").classList.toggle("active", mode === "gcp");
  byId("mode-cp").classList.toggle("active", mode === "cp");
  byId("finish-aoi").textContent = mode === "road" ? "Hoàn tất đường" : "Hoàn tất AOI";
  const message = mode === "aoi" ? "Chế độ vẽ AOI: nhấp để thêm đỉnh polygon."
    : mode === "road" ? "Chế độ vẽ đường: nhấp bản đồ để thêm các đỉnh đường."
      : mode === "gcp" ? "Chế độ ghim GCP: nhấp bản đồ để đặt GCP thủ công."
        : "Chế độ Check Point: nhấp bản đồ để đặt điểm kiểm tra độc lập.";
  setStatus(message);
}

function manualFeatureCollection() {
  return {
    type: "FeatureCollection",
    features: state.manualGcps.map((coordinate, index) => ({
      type: "Feature",
      id: `manual-gcp-${index + 1}`,
      properties: { kind: "manual_gcp", order: index + 1 },
      geometry: { type: "Point", coordinates: coordinate },
    })),
  };
}

function checkPointFeatureCollection() {
  return {
    type: "FeatureCollection",
    features: state.checkPoints.map((coordinate, index) => ({
      type: "Feature",
      id: `check-point-${index + 1}`,
      properties: { kind: "check_point", role: "independent_accuracy_validation", order: index + 1 },
      geometry: { type: "Point", coordinates: coordinate },
    })),
  };
}

function surveyControlCollection() {
  return {
    type: "FeatureCollection",
    features: [...(state.selectedGcps?.features || []), ...checkPointFeatureCollection().features],
  };
}

function updateControlActions() {
  const controls = surveyControlCollection();
  byId("plan-route").disabled = controls.features.length < 2;
  byId("export-result").disabled = controls.features.length === 0;
}

function renderCheckPoints() {
  layers.checkPoints.clearLayers().addData(checkPointFeatureCollection());
  updateControlActions();
  refreshLayerPanel();
}

function renderManualGcps() {
  const collection = manualFeatureCollection();
  layers.selected.clearLayers().addData(collection);
  state.selectedGcps = collection.features.length ? collection : null;
  layers.candidates.clearLayers(); layers.route.clearLayers(); metrics.innerHTML = "";
  renderCheckPoints();
  refreshLayerPanel();
}

function addManualGcp(latlng) {
  state.manualGcps.push([Number(latlng.lng.toFixed(7)), Number(latlng.lat.toFixed(7))]);
  renderManualGcps();
  setStatus(`Đã ghim GCP ${state.manualGcps.length}. Có thể tiếp tục ghim, lập tuyến hoặc xuất GeoJSON.`);
}

function removeLastGcp() {
  if (!state.manualGcps.length) return setStatus("Chưa có GCP ghim tay để xóa.", true);
  state.manualGcps.pop(); renderManualGcps();
  setStatus(`Còn ${state.manualGcps.length} GCP ghim tay.`);
}

function clearManualGcps() {
  if (!state.manualGcps.length) return setStatus("Không có GCP ghim tay để xóa.", true);
  state.manualGcps = []; renderManualGcps();
  setStatus("Đã xóa các GCP ghim tay.");
}

function addCheckPoint(latlng) {
  state.checkPoints.push([Number(latlng.lng.toFixed(7)), Number(latlng.lat.toFixed(7))]);
  layers.route.clearLayers(); renderCheckPoints();
  setStatus(`Đã ghim Check Point ${state.checkPoints.length}. CP hiển thị bằng ghim màu xanh.`);
}

function removeLastCheckPoint() {
  if (!state.checkPoints.length) return setStatus("Chưa có Check Point để xóa.", true);
  state.checkPoints.pop(); renderCheckPoints();
  setStatus(`Còn ${state.checkPoints.length} Check Point.`);
}

function clearCheckPoints() {
  if (!state.checkPoints.length) return setStatus("Không có Check Point để xóa.", true);
  state.checkPoints = []; layers.route.clearLayers(); renderCheckPoints();
  setStatus("Đã xóa các Check Point.");
}

map.on("click", (event) => {
  if (state.mode === "gcp") return addManualGcp(event.latlng);
  if (state.mode === "cp") return addCheckPoint(event.latlng);
  if (state.mode === "road") {
    state.roadDrawing.push([event.latlng.lng, event.latlng.lat]); renderAOI();
    return setStatus(`Đã chọn ${state.roadDrawing.length} đỉnh đường.`);
  }
  if (state.aoi) return setStatus("AOI đã hoàn tất. Bấm Xóa AOI để vẽ lại.", true);
  state.drawing.push([event.latlng.lng, event.latlng.lat]); renderAOI();
  setStatus(`Đã chọn ${state.drawing.length} đỉnh AOI.`);
});

function finishAOI() {
  if (state.mode === "road") return finishRoad();
  if (state.drawing.length < 3) return setStatus("AOI cần tối thiểu 3 đỉnh.", true);
  state.aoi = aoiFeature(state.drawing); resetFlightBoundaryAssessment(); renderAOI(); resetResults();
  refreshSurveyRecommendation();
  setStatus("AOI đã sẵn sàng. Nạp hoặc vẽ mạng đường trước khi tối ưu.");
}

function finishRoad() {
  if (state.roadDrawing.length < 2) return setStatus("Mạng đường cần tối thiểu 2 đỉnh.", true);
  const feature = {
    type: "Feature",
    properties: { name: `Drawn road ${((state.roads?.features || []).length) + 1}` },
    geometry: { type: "LineString", coordinates: state.roadDrawing },
  };
  const existing = state.roads?.features || [];
  state.roads = { type: "FeatureCollection", features: [...existing, feature] };
  state.roadDrawing = [];
  layers.roads.clearLayers().addData(state.roads);
  renderAOI(); resetResults(); refreshSurveyRecommendation(); setMode("aoi");
  setStatus("Đã thêm một tuyến đường vào mạng đường khảo sát.");
}

function clearAOI() {
  state.aoi = null; state.drawing = []; state.roadDrawing = []; state.manualGcps = []; resetFlightBoundaryAssessment(); renderAOI(); resetResults();
  clearSurveyRecommendation();
  setStatus("AOI đã được xóa. Nhấp bản đồ để vẽ lại.");
}

function parseKmlCoordinates(value) {
  return value.trim().split(/\s+/).map((item) => {
    const [longitude, latitude] = item.split(",").map(Number);
    return [longitude, latitude];
  }).filter(([longitude, latitude]) => Number.isFinite(longitude) && Number.isFinite(latitude));
}

function firstKmlElement(root, name) {
  return [...root.getElementsByTagNameNS("*", name)][0];
}

function kmlToGeoJson(kmlText) {
  const documentXml = new DOMParser().parseFromString(kmlText, "application/xml");
  if (documentXml.getElementsByTagName("parsererror").length) throw new Error("Tệp KML không hợp lệ.");
  const features = [];
  for (const placemark of documentXml.getElementsByTagNameNS("*", "Placemark")) {
    const name = firstKmlElement(placemark, "name")?.textContent?.trim() || "Unnamed point";
    const point = firstKmlElement(placemark, "Point");
    const line = firstKmlElement(placemark, "LineString");
    const polygon = firstKmlElement(placemark, "Polygon");
    let geometry = null;
    if (point) {
      const coordinates = parseKmlCoordinates(firstKmlElement(point, "coordinates")?.textContent || "");
      if (coordinates[0]) geometry = { type: "Point", coordinates: coordinates[0] };
    } else if (line) {
      const coordinates = parseKmlCoordinates(firstKmlElement(line, "coordinates")?.textContent || "");
      if (coordinates.length > 1) geometry = { type: "LineString", coordinates };
    } else if (polygon) {
      const boundary = firstKmlElement(polygon, "outerBoundaryIs");
      const coordinates = parseKmlCoordinates(firstKmlElement(boundary || polygon, "coordinates")?.textContent || "");
      if (coordinates.length > 2) {
        if (coordinates[0][0] !== coordinates.at(-1)[0] || coordinates[0][1] !== coordinates.at(-1)[1]) coordinates.push(coordinates[0]);
        geometry = { type: "Polygon", coordinates: [coordinates] };
      }
    }
    if (geometry) features.push({ type: "Feature", properties: { name }, geometry });
  }
  if (!features.length) throw new Error("Không tìm thấy Point, LineString hoặc Polygon trong KML.");
  return { type: "FeatureCollection", features };
}

function asFeatureList(geojson) {
  if (geojson.type === "FeatureCollection") return geojson.features || [];
  if (geojson.type === "Feature") return [geojson];
  return [{ type: "Feature", properties: {}, geometry: geojson }];
}

function importSpatialData(geojson, filename) {
  const features = asFeatureList(geojson).filter((feature) => feature.geometry);
  const polygon = features.find((feature) => ["Polygon", "MultiPolygon"].includes(feature.geometry.type));
  const roads = features.filter((feature) => ["LineString", "MultiLineString"].includes(feature.geometry.type));
  const points = features.filter((feature) => feature.geometry.type === "Point");
  const importedGcps = points.filter((feature) => !/\b(cp|check[ _-]?point)\b/i.test(feature.properties?.name || ""));
  const importedCps = points.filter((feature) => /\b(cp|check[ _-]?point)\b/i.test(feature.properties?.name || ""));

  if (polygon) {
    state.aoi = polygon;
    state.drawing = [];
    resetFlightBoundaryAssessment();
    renderAOI();
  }
  if (roads.length) { state.roads = { type: "FeatureCollection", features: roads }; layers.roads.clearLayers().addData(state.roads); }
  if (points.length) {
    state.manualGcps = importedGcps.map((feature) => feature.geometry.coordinates);
    state.checkPoints = importedCps.map((feature) => feature.geometry.coordinates);
    renderManualGcps();
  }
  layers.candidates.clearLayers(); layers.route.clearLayers(); metrics.innerHTML = "";
  const uploadedBounds = L.geoJSON({ type: "FeatureCollection", features }).getBounds();
  if (uploadedBounds.isValid()) map.fitBounds(uploadedBounds, { padding: [36, 36], maxZoom: 18 });
  refreshLayerPanel();
  refreshSurveyRecommendation();
  const imported = [`${polygon ? 1 : 0} AOI`, `${roads.length} road`, `${importedGcps.length} GCP`, `${importedCps.length} CP`];
  setStatus(`Đã nạp ${filename}: ${imported.join(", ")}. Điểm có tên CP hoặc Check Point được nhận dạng là CP.`);
}

function mergeShapeCollections(value) {
  if (Array.isArray(value)) return { type: "FeatureCollection", features: value.flatMap((item) => asFeatureList(item)) };
  if (value?.type) return value;
  const collections = Object.values(value || {}).filter((item) => item?.type);
  return { type: "FeatureCollection", features: collections.flatMap((item) => asFeatureList(item)) };
}

async function kmzToGeoJson(file) {
  const { default: JSZip } = await import("https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm");
  const archive = await JSZip.loadAsync(await file.arrayBuffer());
  const kmlEntry = Object.values(archive.files).find((entry) => !entry.dir && /\.kml$/i.test(entry.name) && !entry.name.startsWith("__MACOSX/"));
  if (!kmlEntry) throw new Error("Không tìm thấy tệp KML trong KMZ.");
  return kmlToGeoJson(await kmlEntry.async("text"));
}

async function shapefileToGeoJson(file) {
  const { default: shp } = await import("https://unpkg.com/shpjs@6.2.0/dist/shp.esm.js");
  return mergeShapeCollections(await shp(await file.arrayBuffer()));
}

async function loadSpatialFile(event, format) {
  const [file] = event.target.files;
  if (!file) return;
  try {
    byId("selected-file").textContent = `Đang nạp: ${file.name}`;
    setStatus(`Đang đọc ${file.name}...`);
    const data = format === "shape" ? await shapefileToGeoJson(file)
      : file.name.toLowerCase().endsWith(".kmz") ? await kmzToGeoJson(file)
        : file.name.toLowerCase().endsWith(".kml") ? kmlToGeoJson(await file.text())
          : JSON.parse(await file.text());
    importSpatialData(data, file.name);
    byId("selected-file").textContent = `Đã nạp thành công: ${file.name}`;
    closeImportDialog();
  } catch (error) {
    byId("selected-file").textContent = `Không thể nạp: ${file.name}`;
    setStatus(error.message || "Không thể đọc tệp không gian.", true);
  }
  event.target.value = "";
}

async function loadAdministrativeBoundaryFile(event) {
  const [file] = event.target.files;
  if (!file) return;
  try {
    setStatus(`Đang đọc lớp ranh hành chính ${file.name}...`);
    const lowerName = file.name.toLowerCase();
    const data = lowerName.endsWith(".kmz") ? await kmzToGeoJson(file)
      : lowerName.endsWith(".kml") ? kmlToGeoJson(await file.text())
        : lowerName.endsWith(".zip") ? await shapefileToGeoJson(file)
          : JSON.parse(await file.text());
    const features = asFeatureList(data).filter((feature) => ["Polygon", "MultiPolygon"].includes(feature.geometry?.type));
    if (!features.length) throw new Error("Tệp ranh hành chính cần chứa Polygon hoặc MultiPolygon.");
    state.adminBoundaries = { type: "FeatureCollection", features };
    layers.adminBoundaries.clearLayers().addData(state.adminBoundaries);
    refreshLayerPanel();
    if (state.aoi) checkFlightBoundary();
    else setStatus(`Đã nạp ${features.length} ranh hành chính từ ${file.name}. Hoàn tất AOI để kiểm tra giao cắt.`);
  } catch (error) {
    setStatus(error.message || "Không thể đọc lớp ranh hành chính.", true);
  }
  event.target.value = "";
}

function parseCoordinateInput(value) {
  const coordinates = value.trim().split(/[\r\n;]+/).map((line) => line.trim()).filter(Boolean).map((line) => {
    const [longitude, latitude] = line.split(/[\s,]+/).map(Number);
    return [longitude, latitude];
  });
  if (!coordinates.length || coordinates.some(([longitude, latitude]) => !Number.isFinite(longitude) || !Number.isFinite(latitude) || Math.abs(longitude) > 180 || Math.abs(latitude) > 90)) {
    throw new Error("Tọa độ chưa đúng định dạng WGS84: kinh độ, vĩ độ trên mỗi dòng.");
  }
  return coordinates;
}

function importCoordinates(event) {
  event.preventDefault();
  try {
    const coordinates = parseCoordinateInput(byId("coordinate-text").value);
    const kind = byId("coordinate-kind").value;
    if (kind === "aoi" && coordinates.length < 3) throw new Error("Vùng AOI cần ít nhất 3 tọa độ.");
    if (kind === "road" && coordinates.length < 2) throw new Error("Đường cần ít nhất 2 tọa độ.");
    const geometry = kind === "aoi"
      ? { type: "Polygon", coordinates: [[...coordinates, coordinates[0]]] }
      : { type: "LineString", coordinates };
    importSpatialData({ type: "Feature", properties: { name: "Coordinates input" }, geometry }, "tọa độ WGS84");
    closeImportDialog();
  } catch (error) { setStatus(error.message || "Không thể nạp tọa độ.", true); }
}

function openImportDialog() {
  byId("import-modal").hidden = false;
  byId("close-import").focus();
}

function closeImportDialog() {
  byId("import-modal").hidden = true;
  byId("coordinate-form").hidden = true;
}

function payload() {
  return {
    aoi: state.aoi,
    roads: state.roads,
    gcp_count: Number(byId("gcp-count").value),
    candidate_spacing_m: Number(byId("spacing").value),
    access_radius_m: Number(byId("access-radius").value),
    generations: Number(byId("generations").value),
    positioning_method: byId("positioning-method").value,
    required_accuracy_cm: Number(byId("required-accuracy").value),
    terrain_complexity: byId("terrain-complexity").value,
    flight_altitude_m: Number(byId("flight-altitude").value),
    gsd_cm: Number(byId("gsd").value),
    forward_overlap_pct: Number(byId("forward-overlap").value),
    side_overlap_pct: Number(byId("side-overlap").value),
  };
}

function clearSurveyRecommendation() {
  state.surveyProfile = null;
  byId("apply-profile").disabled = true;
  byId("profile-recommendation").textContent = "Chọn cấu hình bay, sau đó nạp AOI và mạng đường để nhận khuyến nghị GCP/CP.";
}

function renderSurveyRecommendation(profile) {
  state.surveyProfile = profile;
  byId("profile-recommendation").innerHTML = `<strong>Khuyến nghị theo ${escapeHtml(profile.positioning_label)} · ${escapeHtml(profile.terrain_label)}</strong>`
    + `${escapeHtml(profile.flight_summary)}<br>AOI: ${profile.area_ha.toFixed(2)} ha · GCP: ${profile.recommended_gcp_count} · CP độc lập: tối thiểu ${profile.recommended_cp_count} · Bước lưới Candidate: ${profile.recommended_candidate_spacing_m} m.<br>${escapeHtml(profile.notice)}`;
  byId("apply-profile").disabled = false;
}

async function refreshSurveyRecommendation() {
  if (!state.aoi || !state.roads) return clearSurveyRecommendation();
  if (window.location.protocol === "file:") {
    byId("profile-recommendation").textContent = "Hãy chạy WebGIS qua FastAPI để nhận khuyến nghị theo cấu hình bay.";
    return;
  }
  try {
    const response = await fetch("/api/optimization/recommendation", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
    const profile = await response.json();
    if (!response.ok) throw new Error(profile.detail || "Không thể tạo khuyến nghị bay.");
    renderSurveyRecommendation(profile);
  } catch (error) {
    byId("profile-recommendation").textContent = error.message || "Không thể tạo khuyến nghị bay.";
    byId("apply-profile").disabled = true;
  }
}

function applySurveyRecommendation() {
  const profile = state.surveyProfile;
  if (!profile) return;
  byId("gcp-count").value = profile.recommended_gcp_count;
  byId("spacing").value = profile.recommended_candidate_spacing_m;
  setStatus(`Đã áp dụng ${profile.recommended_gcp_count} GCP và bước lưới ${profile.recommended_candidate_spacing_m} m. Hãy đặt tối thiểu ${profile.recommended_cp_count} CP xanh độc lập để kiểm chứng.`);
}

function displayMetrics(result) {
  const labels = { fitness: "Fitness tổng", coverage: "Độ phủ", uniformity: "Độ đồng đều", edge_interior: "Biên và trung tâm", accessibility: "Khả năng tiếp cận" };
  metrics.innerHTML = Object.entries(result.metrics).map(([key, value]) => `<dt>${labels[key] || key}</dt><dd>${(value * 100).toFixed(1)}%</dd>`).join("");
}

async function runOptimization() {
  if (!state.aoi || !state.roads) return setStatus("Cần có cả vùng AOI và mạng đường trước khi chạy GA.", true);
  setStatus("Đang sinh candidate GCP và chạy Genetic Algorithm...");
  try {
    const response = await fetch("/api/optimization/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Không thể chạy tối ưu");
    layers.candidates.clearLayers();
    const candidateResponse = await fetch("/api/gcps/candidates", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
    layers.candidates.addData((await candidateResponse.json()).candidates);
    layers.selected.clearLayers().addData(result.selected_gcps); layers.route.clearLayers();
    state.selectedGcps = result.selected_gcps; state.manualGcps = []; displayMetrics(result); renderCheckPoints();
    renderSurveyRecommendation(result.survey_profile);
    refreshLayerPanel();
    setStatus(`Hoàn tất: chọn ${result.gcp_count}/${result.candidate_count} candidate. Fitness GA: ${(result.metrics.fitness * 100).toFixed(1)}%. Khuyến nghị kiểm chứng bằng tối thiểu ${result.survey_profile.recommended_cp_count} CP.`);
  } catch (error) { setStatus(error.message, true); }
}

async function planRoute() {
  const controls = surveyControlCollection();
  if (controls.features.length < 2) return;
  setStatus("Đang tối ưu thứ tự khảo sát GCP...");
  try {
    const response = await fetch("/api/routing/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ gcps: controls.features }) });
    const route = await response.json();
    if (!response.ok) throw new Error(route.detail || "Không thể lập tuyến");
    layers.route.clearLayers().addData(route);
    refreshLayerPanel();
    setStatus(`Tuyến khảo sát đã tạo: ${(route.properties.distance_m / 1000).toFixed(2)} km, ${route.properties.stops} điểm.`);
  } catch (error) { setStatus(error.message, true); }
}

function exportResults() {
  const controls = surveyControlCollection();
  if (!controls.features.length) return;
  const blob = new Blob([JSON.stringify(controls, null, 2)], { type: "application/geo+json" });
  const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "survey_control_points.geojson" });
  link.click(); URL.revokeObjectURL(link.href);
}

byId("mode-aoi").addEventListener("click", () => setMode("aoi"));
byId("mode-road").addEventListener("click", () => setMode("road"));
byId("mode-gcp").addEventListener("click", () => setMode("gcp"));
byId("mode-cp").addEventListener("click", () => setMode("cp"));
byId("finish-aoi").addEventListener("click", finishAOI);
byId("clear-aoi").addEventListener("click", clearAOI);
byId("remove-last-gcp").addEventListener("click", removeLastGcp);
byId("remove-last-cp").addEventListener("click", removeLastCheckPoint);
byId("clear-manual-gcps").addEventListener("click", clearManualGcps);
byId("clear-check-points").addEventListener("click", clearCheckPoints);
byId("check-flight-boundary").addEventListener("click", checkFlightBoundary);
byId("export-flight-kml").addEventListener("click", exportFlightKml);
byId("export-flight-brief").addEventListener("click", exportFlightBrief);
byId("open-import").addEventListener("click", openImportDialog);
byId("close-import").addEventListener("click", closeImportDialog);
byId("show-coordinates").addEventListener("click", () => { byId("coordinate-form").hidden = !byId("coordinate-form").hidden; });
byId("draw-aoi").addEventListener("click", () => { closeImportDialog(); setMode("aoi"); });
byId("draw-road").addEventListener("click", () => { closeImportDialog(); setMode("road"); });
byId("coordinate-form").addEventListener("submit", importCoordinates);
byId("geojson-file").addEventListener("change", (event) => loadSpatialFile(event, "geojson"));
byId("kml-file").addEventListener("change", (event) => loadSpatialFile(event, "kml"));
byId("shape-file").addEventListener("change", (event) => loadSpatialFile(event, "shape"));
byId("import-modal").addEventListener("click", (event) => { if (event.target === byId("import-modal")) closeImportDialog(); });
byId("toggle-no-fly").addEventListener("change", (event) => {
  if (event.target.checked) layers.noFlyZones.addTo(map);
  else layers.noFlyZones.remove();
  refreshLayerPanel();
});
byId("run-ga").addEventListener("click", runOptimization);
byId("apply-profile").addEventListener("click", applySurveyRecommendation);
["positioning-method", "required-accuracy", "terrain-complexity", "flight-altitude", "gsd", "forward-overlap", "side-overlap"].forEach((id) => {
  byId(id).addEventListener("change", refreshSurveyRecommendation);
});
byId("plan-route").addEventListener("click", planRoute);
byId("export-result").addEventListener("click", exportResults);

if (window.location.protocol === "file:") {
  setStatus("Nạp tệp khảo sát hoặc vẽ AOI để bắt đầu. Hãy chạy FastAPI để hiển thị lớp CAMBAY.kmz và dùng GA.");
} else {
  loadNoFlyZones();
}

refreshLayerPanel();
updateFlightBoundaryControls();
clearSurveyRecommendation();
