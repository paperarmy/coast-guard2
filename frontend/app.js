/* ===================== 설정 ===================== */
const API = window.location.hostname === "localhost"
  ? "http://localhost:8000/api"
  : "/api";

/* ===================== 전역 상태 ===================== */
let state = {
  grids: [],
  filteredGrids: [],
  environment: null,
  assets: [],
  sortKey: "rank",
  sortAsc: true,
  map: null,
  assetMap: null,
  gridLayers: {},
  tsChart: null,
  currentView: "dashboard",
};

/* ===================== 유틸 ===================== */
const $ = id => document.getElementById(id);
const lvlClass = l => ({위험:"danger",경계:"warning",주의:"caution",정상:"safe"}[l] || "safe");
const assetIcon = t => ({drone:"🚁",tod:"👁️",cctv:"📷",patrol:"🚢"}[t] || "📌");

function formatKorTime() {
  return new Date().toLocaleString("ko-KR", { hour12: false, year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit" });
}

/* ===================== 초기화 ===================== */
window.onload = async () => {
  startClock();
  initMap();
  initAssetMap();
  await loadAll();
  setInterval(loadEnvironment, 60000); // 1분마다 환경 갱신
};

function startClock() {
  $("clock").textContent = formatKorTime();
  setInterval(() => { $("clock").textContent = formatKorTime(); }, 1000);
}

async function loadAll() {
  await Promise.all([loadEnvironment(), loadGrids(), loadAssets()]);
  renderForecast();
}

/* ===================== API 호출 ===================== */
async function fetchAPI(path) {
  try {
    const r = await fetch(API + path);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    $("connection-status").style.background = "#16a34a";
    return await r.json();
  } catch (e) {
    $("connection-status").style.background = "#dc2626";
    console.error("API 오류:", path, e.message);
    return null;
  }
}

async function loadEnvironment() {
  const data = await fetchAPI("/environment/current");
  if (!data) return;
  state.environment = data;
  renderEnvironmentPanel(data);

  const alert = await fetchAPI("/alert/today");
  if (alert) renderAlertBanner(alert);
}

async function loadGrids() {
  const data = await fetchAPI("/grids?limit=210");
  if (!data) return;
  state.grids = data.grids;
  state.filteredGrids = [...state.grids];
  renderMapGrids();
  renderPriorityList();
  renderStatsGrid();
  renderGridTable();
  populateTsSelect();
}

async function loadAssets() {
  const data = await fetchAPI("/assets");
  if (!data) return;
  state.assets = data.assets;
  renderAssetMap();
  renderAssetList();
}

/* ===================== 환경 패널 ===================== */
function renderEnvironmentPanel(env) {
  const period = env.time.is_night ? "야간" : "주간";
  const el = $("env-period");
  el.textContent = period;
  el.className = "badge " + (env.time.is_night ? "night" : "day");
  $("env-tide").textContent = `${env.tide.height_m}m (${env.tide.tide_phase})${env.tide.is_high_tide ? " 🌊" : ""}`;
  $("env-vis").textContent = `${env.weather.visibility_km}km${env.weather.is_fog ? " 🌫️" : ""}`;
  $("env-wind").textContent = `${env.weather.wind_speed_ms} (${env.weather.wind_direction})`;

  const chips = env.triple_risk.components;
  $("triple-chips").innerHTML = [
    { key: "night", label: "야간" },
    { key: "high_tide", label: "만조" },
    { key: "fog", label: "안개" },
  ].map(c => `
    <div class="triple-chip ${chips[c.key] ? "on" : "off"}">
      <span>${chips[c.key] ? "✔" : "✘"}</span>
      <span>${c.label}</span>
    </div>
  `).join("");
}

/* ===================== 경보 배너 ===================== */
function renderAlertBanner(alert) {
  const lvl = alert.alert_level;
  const cls = { 위험: "alert-danger", 경계: "alert-warning", 주의: "alert-caution", 정상: "alert-normal" };
  const icon = { 위험: "🚨", 경계: "⚠️", 주의: "🔔", 정상: "●" };
  const banner = $("alert-banner");
  banner.className = "alert-banner " + (cls[lvl] || "alert-normal");
  $("alert-icon").textContent = icon[lvl] || "●";
  $("alert-text").textContent = alert.message;
}

/* ===================== 지도 (대시보드) ===================== */
function initMap() {
  state.map = L.map("map", { zoomControl: true }).setView([35.6, 126.6], 9);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap", maxZoom: 17
  }).addTo(state.map);
}

function renderMapGrids() {
  if (!state.map) return;
  Object.values(state.gridLayers).forEach(l => state.map.removeLayer(l));
  state.gridLayers = {};

  state.grids.forEach(g => {
    const color = g.cvi_color;
    const radius = 4 + g.cvi * 6;
    const marker = L.circleMarker([g.lat, g.lon], {
      radius, color, fillColor: color, fillOpacity: 0.75, weight: 1.5
    });

    marker.bindPopup(`
      <div class="popup-title">${g.grid_id} | ${g.region}</div>
      <div class="popup-row">CVI: <span style="color:${g.cvi_color}">${g.cvi} (${g.cvi_level})</span></div>
      <div class="popup-row">LISA: <span>${g.lisa}</span></div>
      <div class="popup-row">유형: <span>${g.grid_type}</span></div>
      <div class="popup-row">권고: <span>${g.recommended_actions[0]}</span></div>
      <button class="popup-detail-btn" onclick="openDetail('${g.grid_id}')">상세 보기 →</button>
    `, { maxWidth: 220 });

    marker.addTo(state.map);
    state.gridLayers[g.grid_id] = marker;
  });
}

/* ===================== 오늘의 경계 중점 ===================== */
function renderPriorityList() {
  const top5 = state.grids.slice(0, 5);
  $("priority-list").innerHTML = top5.map((g, i) => `
    <div class="priority-item ${lvlClass(g.cvi_level)}" onclick="openDetail('${g.grid_id}')">
      <div class="priority-rank">${i + 1}</div>
      <div class="priority-info">
        <div class="priority-grid-id">${g.grid_id}</div>
        <div class="priority-region">${g.region}</div>
        <div class="priority-actions">${g.recommended_actions.slice(0, 2).join(" / ")}</div>
      </div>
      <div class="priority-cvi">
        <div class="cvi-value" style="color:${g.cvi_color}">${g.cvi}</div>
        <div class="cvi-level" style="color:${g.cvi_color}">${g.cvi_level}</div>
      </div>
    </div>
  `).join("");
}

/* ===================== 통계 요약 ===================== */
function renderStatsGrid() {
  const grids = state.grids;
  const danger  = grids.filter(g => g.cvi_level === "위험").length;
  const warning = grids.filter(g => g.cvi_level === "경계").length;
  const hh      = grids.filter(g => g.lisa === "HH").length;
  const avgCvi  = (grids.reduce((a,g) => a+g.cvi, 0) / grids.length).toFixed(3);

  $("stats-grid").innerHTML = `
    <div class="stat-box"><div class="stat-value stat-danger">${danger}</div><div class="stat-label">위험 격자</div></div>
    <div class="stat-box"><div class="stat-value stat-warn">${warning}</div><div class="stat-label">경계 격자</div></div>
    <div class="stat-box"><div class="stat-value stat-accent">${hh}</div><div class="stat-label">HH 핫스팟</div></div>
    <div class="stat-box"><div class="stat-value">${avgCvi}</div><div class="stat-label">평균 CVI</div></div>
  `;
}

/* ===================== 7일 예측 ===================== */
async function renderForecast() {
  const data = await fetchAPI("/alert/forecast");
  if (!data) return;
  $("forecast-bar").innerHTML = data.forecast.map(d => `
    <div class="forecast-day level-${d.level}" title="${d.fog_prob_pct}% 안개 / ${d.triple_risk_count}회 3중취약">
      <div class="forecast-date">${d.day_label}</div>
      <div class="forecast-level level-${d.level}">${d.level}</div>
      <div class="forecast-fog">안개${d.fog_prob_pct}%</div>
    </div>
  `).join("");
}

/* ===================== 격자 테이블 ===================== */
function renderGridTable() {
  const tbody = $("grid-tbody");
  tbody.innerHTML = state.filteredGrids.map(g => `
    <tr onclick="openDetail('${g.grid_id}')">
      <td>${g.rank}</td>
      <td>${g.grid_id}</td>
      <td>${g.region}</td>
      <td style="color:${g.cvi_color};font-weight:700">${g.cvi}</td>
      <td><span class="badge-level level-${g.cvi_level}-badge">${g.cvi_level}</span></td>
      <td><span class="badge-lisa lisa-${g.lisa}">${g.lisa}</span></td>
      <td style="font-size:11px">${g.grid_type}</td>
      <td>${g.assets.cctv_count > 0 ? `<span class="bool-yes">${g.assets.cctv_count}대</span>` : '<span class="bool-no">없음</span>'}</td>
      <td>${g.assets.drone ? '<span class="bool-yes">✔</span>' : '<span class="bool-no">-</span>'}</td>
      <td>${g.assets.tod ? '<span class="bool-yes">✔</span>' : '<span class="bool-no">-</span>'}</td>
      <td style="font-size:10px;color:#94a3b8">${g.recommended_actions[0]}</td>
    </tr>
  `).join("");
}

function filterGrids() {
  const region = $("filter-region").value;
  const lisa   = $("filter-lisa").value;
  const level  = $("filter-level").value;
  state.filteredGrids = state.grids.filter(g =>
    (!region || g.region === region) &&
    (!lisa   || g.lisa === lisa) &&
    (!level  || g.cvi_level === level)
  );
  renderGridTable();
}

function sortTable(key) {
  if (state.sortKey === key) state.sortAsc = !state.sortAsc;
  else { state.sortKey = key; state.sortAsc = true; }
  state.filteredGrids.sort((a, b) => {
    const av = a[key], bv = b[key];
    return state.sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });
  renderGridTable();
}

function exportCSV() {
  const headers = ["순위","격자ID","지역","CVI","등급","LISA","유형","CCTV","드론","TOD"];
  const rows = state.filteredGrids.map(g => [
    g.rank, g.grid_id, g.region, g.cvi, g.cvi_level, g.lisa, g.grid_type,
    g.assets.cctv_count, g.assets.drone ? "O" : "X", g.assets.tod ? "O" : "X"
  ]);
  const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `CVI_격자분석_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

/* ===================== 자산 지도 ===================== */
function initAssetMap() {
  state.assetMap = L.map("asset-map").setView([35.6, 126.6], 9);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap", maxZoom: 17
  }).addTo(state.assetMap);
}

function renderAssetMap() {
  if (!state.assetMap) return;
  const colors = { drone: "#38bdf8", tod: "#fb923c", cctv: "#a78bfa", patrol: "#4ade80" };
  state.assets.forEach(a => {
    const color = colors[a.type] || "#94a3b8";
    L.circleMarker([a.lat, a.lon], {
      radius: a.type === "patrol" ? 10 : 7,
      color, fillColor: color, fillOpacity: a.active ? 0.8 : 0.3, weight: 2
    }).bindPopup(`
      <b>${assetIcon(a.type)} ${a.label}</b><br>
      유형: ${a.type.toUpperCase()}<br>
      상태: ${a.active ? "운용 중" : "비운용"}<br>
      커버리지: ${a.range_km}km
    `).addTo(state.assetMap);
  });
}

function renderAssetList() {
  $("asset-list").innerHTML = state.assets.map(a => `
    <div class="asset-item">
      <div class="asset-icon">${assetIcon(a.type)}</div>
      <div class="asset-info">
        <div class="asset-name">${a.label}</div>
        <div class="asset-sub">${a.region} | 커버 ${a.range_km}km</div>
      </div>
      <div class="asset-status ${a.active ? "status-on" : "status-off"}">
        ${a.active ? "운용" : "비운용"}
      </div>
    </div>
  `).join("");
}

/* ===================== 시계열 ===================== */
function populateTsSelect() {
  const sel = $("ts-grid-select");
  state.grids.slice(0, 30).forEach(g => {
    const opt = document.createElement("option");
    opt.value = g.grid_id;
    opt.textContent = `${g.grid_id} (${g.region}, CVI ${g.cvi})`;
    sel.appendChild(opt);
  });
}

async function loadTimeseries() {
  const gridId = $("ts-grid-select").value;
  if (!gridId) return;
  const data = await fetchAPI(`/grids/${gridId}/timeseries?days=90`);
  if (!data) return;

  const labels = data.series.map(d => d.date);
  const values = data.series.map(d => d.anomaly_index);
  const tripleRisk = data.series.map(d => d.is_triple_risk ? d.anomaly_index : null);

  if (state.tsChart) state.tsChart.destroy();
  const ctx = $("ts-chart").getContext("2d");
  state.tsChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "야간 이상 지수",
          data: values,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56,189,248,.1)",
          borderWidth: 1.5,
          pointRadius: 0,
          fill: true,
          tension: 0.3,
        },
        {
          label: "3중 취약일",
          data: tripleRisk,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,.6)",
          borderWidth: 0,
          pointRadius: 5,
          pointStyle: "triangle",
          showLine: false,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#e2e8f0", font: { size: 12 } } },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        x: {
          ticks: { color: "#94a3b8", maxTicksLimit: 12, font: { size: 10 } },
          grid: { color: "rgba(71,85,105,.4)" }
        },
        y: {
          ticks: { color: "#94a3b8", font: { size: 10 } },
          grid: { color: "rgba(71,85,105,.4)" },
          min: 0
        }
      }
    }
  });

  $("ts-info").textContent = `격자 ${gridId} | ${data.region} | 최근 90일 야간 이상 지수 추이 (STL 잔차)`;
}

/* ===================== 격자 상세 ===================== */
async function openDetail(gridId) {
  const grid = state.grids.find(g => g.grid_id === gridId);
  if (!grid) return;

  $("detail-title").textContent = `${grid.grid_id} | ${grid.region}`;
  $("detail-body").innerHTML = `
    <div class="detail-section">
      <div class="detail-section-title">CVI 종합</div>
      <div class="detail-row"><span>CVI 점수</span><span style="color:${grid.cvi_color};font-weight:700;font-size:16px">${grid.cvi}</span></div>
      <div class="detail-row"><span>등급</span><span style="color:${grid.cvi_color}">${grid.cvi_level}</span></div>
      <div class="detail-row"><span>전체 순위</span><span>${grid.rank}위 / 210 (상위 ${grid.rank_pct}%)</span></div>
      <div class="detail-row"><span>LISA 유형</span><span><span class="badge-lisa lisa-${grid.lisa}">${grid.lisa}</span></span></div>
      <div class="detail-row"><span>격자 유형</span><span style="font-size:11px">${grid.grid_type}</span></div>
    </div>

    <div class="detail-section">
      <div class="detail-section-title">SHAP 기여도</div>
      ${Object.entries(grid.shap).map(([k, v]) => {
        const labels = { night_anomaly:"야간이상지수", old_building:"노후건물비율", vessel_density:"야간선박밀도", cctv_gap:"감시취약도(CCTV)", coast_proximity:"해안근접도" };
        const pct = Math.max(0, Math.min(100, v * 100));
        return `
          <div class="shap-bar-wrap">
            <div class="shap-label"><span>${labels[k] || k}</span><span>${(v*100).toFixed(1)}%</span></div>
            <div style="background:rgba(71,85,105,.4);border-radius:3px;height:6px">
              <div class="shap-bar" style="width:${pct}%;background:${pct>50?'#ef4444':pct>30?'#fb923c':'#38bdf8'}"></div>
            </div>
          </div>
        `;
      }).join("")}
    </div>

    <div class="detail-section">
      <div class="detail-section-title">현재 감시 자산</div>
      <div class="detail-row"><span>CCTV</span><span>${grid.assets.cctv_count > 0 ? `${grid.assets.cctv_count}대` : '없음 ⚠️'}</span></div>
      <div class="detail-row"><span>드론 거점</span><span>${grid.assets.drone ? '✔ 지정' : '미지정'}</span></div>
      <div class="detail-row"><span>TOD</span><span>${grid.assets.tod ? '✔ 배치' : '미배치'}</span></div>
    </div>

    <div class="detail-section">
      <div class="detail-section-title">권고 조치</div>
      ${grid.recommended_actions.map(a => `<span class="action-tag">${a}</span>`).join("")}
    </div>

    <div class="detail-section">
      <div class="detail-section-title">위치</div>
      <div class="detail-row"><span>위도</span><span>${grid.lat}</span></div>
      <div class="detail-row"><span>경도</span><span>${grid.lon}</span></div>
    </div>
  `;

  $("grid-detail-panel").classList.remove("hidden");

  // 지도 해당 격자로 이동
  if (state.map && state.gridLayers[gridId]) {
    state.map.setView([grid.lat, grid.lon], 11);
    state.gridLayers[gridId].openPopup();
  }
}

function closeDetail() {
  $("grid-detail-panel").classList.add("hidden");
}

/* ===================== 위험 캘린더 ===================== */
const calState = {
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  allDays: {},       // "YYYY-MM-DD" → day data
  forecastDays: {},
  trendChart: null,
};

async function initCalendar() {
  // 실측 전체 범위 로드
  const end = new Date(); end.setDate(end.getDate() - 1);
  const endStr = end.toISOString().slice(0, 10);
  const hist = await fetchAPI("/calendar/range?start=2023-03-01&end=" + endStr);
  if (hist) hist.days.forEach(d => { calState.allDays[d.date] = d; });

  // 미래 30일 예측 로드
  const fore = await fetchAPI("/calendar/forecast?days=30");
  if (fore) fore.forecast.forEach(d => {
    calState.allDays[d.date] = d;
    calState.forecastDays[d.date] = true;
  });

  renderCalMonth();
  renderCalTrend();
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function calNav(dir) {
  calState.month += dir;
  if (calState.month > 12) { calState.month = 1;  calState.year++; }
  if (calState.month < 1)  { calState.month = 12; calState.year--; }
  renderCalMonth();
}

function calGoToday() {
  const now = new Date();
  calState.year  = now.getFullYear();
  calState.month = now.getMonth() + 1;
  renderCalMonth();
}

function renderCalMonth() {
  const { year, month } = calState;
  $("cal-month-label").textContent = `${year}년 ${month}월`;

  const firstDay  = new Date(year, month - 1, 1).getDay();
  const lastDate  = new Date(year, month, 0).getDate();
  const todayDate = new Date().getDate();
  const todayM    = new Date().getMonth() + 1;
  const todayY    = new Date().getFullYear();

  let html = "";
  // 빈 셀
  for (let i = 0; i < firstDay; i++) html += `<div class="cal-cell empty"></div>`;

  for (let d = 1; d <= lastDate; d++) {
    const dateStr = `${year}-${String(month).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    const day     = calState.allDays[dateStr];
    const isForecast = !!calState.forecastDays[dateStr];
    const isToday    = d === todayDate && month === todayM && year === todayY;

    let riskClass = "risk-0";
    let tripleDot = "";
    if (day) {
      const score = day.risk_score || 0;
      const idx   = Math.min(10, Math.floor(score * 10));
      riskClass   = `risk-${idx}`;
      if ((day.triple_risk_hours || day.predicted_triple_hours || 0) > 0) {
        tripleDot = `<span class="cal-triple-dot" title="3중취약"></span>`;
      }
    }

    const classes = [
      "cal-cell", riskClass,
      isForecast ? "forecast" : "",
      isToday    ? "today"    : "",
    ].filter(Boolean).join(" ");

    html += `<div class="${classes}" data-date="${dateStr}" onclick="selectCalDay('${dateStr}')"
              title="${dateStr} | 위험점수: ${day ? day.risk_score : '?'}">${d}${tripleDot}</div>`;
  }

  $("cal-grid").innerHTML = html;
}

async function selectCalDay(dateStr) {
  // 선택 표시
  document.querySelectorAll(".cal-cell.selected").forEach(el => el.classList.remove("selected"));
  const cell = document.querySelector(`.cal-cell[data-date="${dateStr}"]`);
  if (cell) cell.classList.add("selected");

  $("cal-detail-title").textContent = dateStr;
  $("cal-detail-body").innerHTML = `<div class="cal-placeholder">불러오는 중...</div>`;

  const data = await fetchAPI(`/calendar/day/${dateStr}`);
  if (!data) return;

  const src      = data.source;
  const badge    = $("cal-source-badge");
  badge.textContent = src;
  badge.className   = `cal-src-badge src-${src}`;

  const sum = data.summary;
  const lvlColor = { 위험:"#ef4444", 경계:"#f97316", 주의:"#fbbf24", 정상:"#22c55e" };
  const color = lvlColor[sum.risk_level] || "#94a3b8";

  // 시간별 막대 그래프
  const hours = data.hours || [];
  const barHtml = hours.map(h => {
    const score = h.risk_score || 0;
    const pct   = Math.round(score * 100);
    const bg    = h.triple_risk ? "#ef4444" : h.dual_risk ? "#f97316" :
                  h.is_high_tide ? "#38bdf8" : h.is_fog ? "#a78bfa" :
                  h.is_night ? "#334155" : "#1e293b";
    const label = [
      h.is_night ? "야간" : "", h.is_high_tide ? "만조" : "", h.is_fog ? "안개" : ""
    ].filter(Boolean).join("+") || "-";
    const tide  = h.tide_cm != null ? `${h.tide_cm}cm` : "예측";
    const vis   = h.vis_m   != null ? `${h.vis_m}m` : `확률${h.is_fog_prob != null ? Math.round(h.is_fog_prob*100)+"%" : "?"}`;
    return `<div class="cal-hour-bar" style="height:${Math.max(4,pct)}%;background:${bg}">
      <div class="cal-hour-tooltip">${h.hour}시 | ${label}<br>조위:${tide} 시정:${vis}</div>
    </div>`;
  }).join("");

  const hourLabels = ["0","","","","","6","","","","","12","","","","","18","","","","","","","","23"];

  $("cal-detail-body").innerHTML = `
    <div class="cal-day-stats">
      <div class="cal-stat-box">
        <div class="cal-stat-val" style="color:${color}">${sum.risk_level}</div>
        <div class="cal-stat-lbl">위험 등급</div>
      </div>
      <div class="cal-stat-box">
        <div class="cal-stat-val" style="color:${color}">${(sum.risk_score*100).toFixed(1)}%</div>
        <div class="cal-stat-lbl">위험 점수</div>
      </div>
      <div class="cal-stat-box">
        <div class="cal-stat-val" style="color:#ef4444">${sum.triple_risk_hours || 0}h</div>
        <div class="cal-stat-lbl">3중취약 시간</div>
      </div>
      <div class="cal-stat-box">
        <div class="cal-stat-val">${hours.filter(h=>h.is_high_tide).length}h</div>
        <div class="cal-stat-lbl">만조 시간</div>
      </div>
    </div>
    <div class="cal-conditions">
      <div class="cal-cond-title">시간별 위험 분포 (빨강=3중 / 주황=2중 / 파랑=만조 / 보라=안개)</div>
      <div class="cal-hour-chart-wrap">
        <div class="cal-hour-bars">${barHtml}</div>
        <div class="cal-hour-labels">${hourLabels.map(l=>`<span>${l}</span>`).join("")}</div>
      </div>
    </div>
    <div class="cal-conditions">
      <div class="cal-cond-title">조건별 시간 합계</div>
      <div class="cal-cond-row"><span>만조(≥500cm)</span><span>${hours.filter(h=>h.is_high_tide).length}시간</span></div>
      <div class="cal-cond-row"><span>안개(시정<1km)</span><span>${hours.filter(h=>h.is_fog).length}시간</span></div>
      <div class="cal-cond-row"><span>야간(20~06시)</span><span>${hours.filter(h=>h.is_night).length}시간</span></div>
      <div class="cal-cond-row" style="color:#ef4444;font-weight:600"><span>3중 취약</span><span>${hours.filter(h=>h.triple_risk).length}시간</span></div>
    </div>
    ${src === "예측" && data.summary.confidence_pct != null ? `
    <div class="cal-conf-bar"><div class="cal-conf-fill" style="width:${data.summary.confidence_pct||60}%"></div></div>
    <div class="cal-conf-label">예측 신뢰도: ${data.summary.confidence_pct||60}% (계절 패턴 + 조석 수식 기반)</div>
    ` : ""}
  `;
}

async function renderCalTrend() {
  // 최근 90일 실측 + 30일 예측
  const endDate   = new Date(); endDate.setDate(endDate.getDate() + 30);
  const startDate = new Date(); startDate.setDate(startDate.getDate() - 90);
  const fmt = d => d.toISOString().slice(0,10);

  const days    = [];
  const labels  = [];
  const actual  = [];
  const predict = [];
  const triple  = [];

  let cur = new Date(startDate);
  while (cur <= endDate) {
    const ds  = fmt(cur);
    const day = calState.allDays[ds];
    labels.push(ds.slice(5));
    actual.push(!calState.forecastDays[ds] && day ? day.risk_score : null);
    predict.push(calState.forecastDays[ds] && day ? day.risk_score : null);
    triple.push(day ? (day.triple_risk_hours || day.predicted_triple_hours || 0) > 0 ? 1 : 0 : 0);
    cur.setDate(cur.getDate() + 1);
  }

  if (calState.trendChart) calState.trendChart.destroy();
  const ctx = $("cal-trend-chart").getContext("2d");
  calState.trendChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "실측 위험점수",
          data: actual,
          backgroundColor: actual.map((v,i) => triple[i] ? "rgba(239,68,68,.8)" : "rgba(56,189,248,.6)"),
          borderWidth: 0, barPercentage: 0.9,
        },
        {
          label: "예측 위험점수",
          data: predict,
          backgroundColor: "rgba(249,115,22,.5)",
          borderColor: "rgba(249,115,22,.8)",
          borderWidth: 1, borderDash: [4,2], barPercentage: 0.9,
        },
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#e2e8f0", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.raw;
              return v != null ? `위험점수: ${(v*100).toFixed(1)}%` : "데이터 없음";
            }
          }
        }
      },
      scales: {
        x: { ticks: { color:"#94a3b8", maxTicksLimit:15, font:{size:9} }, grid:{color:"rgba(71,85,105,.3)"} },
        y: { min:0, max:1, ticks:{ color:"#94a3b8", font:{size:10},
              callback: v => `${(v*100).toFixed(0)}%` }, grid:{color:"rgba(71,85,105,.3)"} }
      }
    }
  });
}

/* ===================== 뷰 전환 ===================== */
function switchView(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  $(`view-${view}`).classList.add("active");
  document.querySelector(`[data-view="${view}"]`).classList.add("active");
  state.currentView = view;

  // 지도 크기 재조정
  if (view === "dashboard" && state.map) setTimeout(() => state.map.invalidateSize(), 100);
  if (view === "assets"    && state.assetMap) setTimeout(() => state.assetMap.invalidateSize(), 100);
  if (view === "calendar"  && !calState._loaded) { calState._loaded = true; initCalendar(); }
}

/* ===================== 인쇄 ===================== */
function printPriority() {
  window.print();
}
