/**
 * FloodGuard Priority Queue Interactive Controller (Stitch Frontend Integration)
 * Supports real-time API communication and bidirectional state updates.
 */

let INCIDENTS_DATA = [
  {
    id: "#INC-8821",
    cam_id: "CAM-1042",
    location: "Mutha River Underpass Culvert #4 (Shivajinagar)",
    description: "Heavy industrial debris and plastic tarp creating 74% cross-sectional drainage blockage. Severe overflow hazard.",
    severity: 5,
    risk_score: 94,
    garbage_area: "74.2%",
    water_level: "1.92m (+0.8m/hr)",
    time_ago: "4 mins ago",
    timestamp: "00:14:22 [LIVE CAPTURE]",
    type: "camera",
    run_threat: "CRITICAL",
    zone: "Shivajinagar",
    status: "open",
    sop: "Deploy Hydraulic De-silting Jetting Vehicle (Unit PMC-4) and 4-man rapid clearing crew. Clear culvert trash rack from eastern bank.",
    filmstrip: [
      { label: "Normal flow (22%)", time: "00:12:05", src: "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80" },
      { label: "Debris collision", time: "00:13:40", src: "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=400&q=80" },
      { label: "Severe choke point", time: "00:14:22 [LIVE]", src: "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80", active: true },
      { label: "Backwater surge", time: "00:15:10", src: "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?auto=format&fit=crop&w=400&q=80" }
    ],
    assigned_crew: "PMC-04"
  },
  {
    id: "#INC-8819",
    cam_id: "CAM-0982",
    location: "Hadapsar Flyover Drainage Outfall (Drain-089)",
    description: "Telemetry trigger: Ultrasonic water rise rate exceeded safe threshold. Backwater surge detected at primary manifold.",
    severity: 4,
    risk_score: 82,
    garbage_area: "N/A (Ultrasonic Sensor)",
    water_level: "2.4m / 2.8m Max",
    time_ago: "12 mins ago",
    timestamp: "SURGE LEVEL ALERT",
    type: "sensor",
    run_threat: "ELEVATED",
    zone: "Hadapsar",
    status: "open",
    sop: "Engage de-watering auxiliary pumps at Siphon station #2.",
    filmstrip: [],
    assigned_crew: null
  },
  {
    id: "#INC-8815",
    cam_id: "CAM-0312",
    location: "Swargate Junction Stormwater Drain",
    description: "Illegal dumping in progress: Concrete rubble and masonry bags choking 55% culvert inlet during high precipitation.",
    severity: 4,
    risk_score: 78,
    garbage_area: "54.8%",
    water_level: "1.40m (+0.3m/hr)",
    time_ago: "19 mins ago",
    timestamp: "00:08:14 [LIVE CAPTURE]",
    type: "camera",
    run_threat: "HIGH",
    zone: "Swargate",
    status: "violations",
    sop: "Notify Ward Officer and dispatch interceptor QRT squad.",
    filmstrip: [
      { label: "Truck arrival", time: "00:05:10", src: "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=400&q=80" },
      { label: "Dumping active", time: "00:08:14", src: "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80", active: true }
    ],
    assigned_crew: null
  },
  {
    id: "#INC-8812",
    cam_id: "CAM-0419",
    location: "Sinhagad Road Vitthalwadi Box Drain",
    description: "High volume plastic debris and thermocol packing blocking screen grate. Water level rising fast.",
    severity: 5,
    risk_score: 91,
    garbage_area: "68.5%",
    water_level: "2.10m (+0.9m/hr)",
    time_ago: "25 mins ago",
    timestamp: "00:18:30 [LIVE CAPTURE]",
    type: "camera",
    run_threat: "CRITICAL",
    zone: "Sinhagad",
    status: "open",
    sop: "Mobilize Sinhagad Ward Unit #2 with mechanical grab crane.",
    filmstrip: [
      { label: "Screen intake", time: "00:15:00", src: "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f7?auto=format&fit=crop&w=400&q=80", active: true }
    ],
    assigned_crew: null
  }
];

let selectedIncidentId = "#INC-8821";
let currentFilter = "open";
let currentZone = "all";
let currentSearch = "";
let sortDesc = true;

async function initData() {
  if (window.ApiClient) {
    const liveIncidents = await ApiClient.getIncidents();
    if (liveIncidents && liveIncidents.length > 0) {
      INCIDENTS_DATA = liveIncidents;
      selectedIncidentId = INCIDENTS_DATA[0].id;
    }
  }
  updateStats();
  renderIncidentList();
  renderDetailPanel();
}

function updateStats() {
  const openCount = INCIDENTS_DATA.filter(i => i.status === "open").length;
  const violationsCount = INCIDENTS_DATA.filter(i => i.status === "violations").length;
  const crewsCount = INCIDENTS_DATA.filter(i => i.status === "crews" || i.assigned_crew).length;
  const criticalCount = INCIDENTS_DATA.filter(i => i.severity === 5 && i.status === "open").length;

  const elOpen = document.getElementById("kpi-open-count");
  if (elOpen) elOpen.textContent = openCount;

  const elCrit = document.getElementById("kpi-critical-sub");
  if (elCrit) elCrit.textContent = `${criticalCount} Critical`;

  const elViol = document.getElementById("kpi-violations-count");
  if (elViol) elViol.textContent = violationsCount;

  const elCrews = document.getElementById("kpi-crews-count");
  if (elCrews) elCrews.textContent = crewsCount;

  const navOpen = document.getElementById("nav-open-count");
  if (navOpen) navOpen.textContent = openCount;

  const tabOpen = document.getElementById("tab-open-badge");
  if (tabOpen) tabOpen.textContent = openCount;

  const tabViol = document.getElementById("tab-violations-badge");
  if (tabViol) tabViol.textContent = violationsCount;

  const tabCrews = document.getElementById("tab-crews-badge");
  if (tabCrews) tabCrews.textContent = crewsCount;
}

function getFilteredIncidents() {
  let list = INCIDENTS_DATA.filter(inc => {
    if (currentFilter === "open" && inc.status !== "open") return false;
    if (currentFilter === "violations" && inc.status !== "violations") return false;
    if (currentFilter === "crews" && (!inc.assigned_crew && inc.status !== "crews")) return false;
    if (currentFilter === "resolved" && inc.status !== "resolved") return false;

    if (currentZone !== "all" && !inc.location.toLowerCase().includes(currentZone.toLowerCase()) && !inc.zone?.toLowerCase().includes(currentZone.toLowerCase())) {
      return false;
    }

    if (currentSearch) {
      const q = currentSearch.toLowerCase();
      const match = inc.id.toLowerCase().includes(q)
        || inc.cam_id.toLowerCase().includes(q)
        || inc.location.toLowerCase().includes(q)
        || inc.description.toLowerCase().includes(q);
      if (!match) return false;
    }

    return true;
  });

  list.sort((a, b) => sortDesc ? (b.risk_score - a.risk_score) : (a.risk_score - b.risk_score));
  return list;
}

function renderIncidentList() {
  const container = document.getElementById("incident-list-container");
  if (!container) return;

  const filtered = getFilteredIncidents();
  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <div class="text-3xl mb-2">🎉</div>
        <h4 class="font-bold text-slate-800 text-sm">All Clear in this Category</h4>
        <p class="text-xs text-slate-500 mt-1">No incidents matching the active filter.</p>
      </div>
    `;
    return;
  }

  // Ensure selected incident is in filtered list or pick first
  if (!filtered.find(i => i.id === selectedIncidentId)) {
    selectedIncidentId = filtered[0].id;
    renderDetailPanel();
  }

  container.innerHTML = filtered.map(inc => {
    const isSelected = inc.id === selectedIncidentId;
    const isSev5 = inc.severity === 5;
    const thumbSrc = (inc.filmstrip && inc.filmstrip.length > 0)
      ? (inc.filmstrip.find(f => f.active)?.src || inc.filmstrip[0].src)
      : "";

    return `
      <div class="cursor-pointer transition duration-150 rounded-xl border p-4 bg-white ${isSelected ? 'border-[#0e7c86] ring-2 ring-[#0e7c86]/20 shadow-md' : 'border-[#e1e6ee] hover:border-slate-300 shadow-sm'}" onclick="selectIncident('${inc.id}')">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center space-x-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${isSev5 ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-amber-100 text-amber-800 border border-amber-200'}">
              Sev ${inc.severity}/5 ${isSev5 ? 'CRITICAL' : 'WARNING'}
            </span>
            <span class="font-mono text-xs text-slate-500">${inc.cam_id}</span>
            <span class="font-mono text-xs font-semibold text-slate-700">${inc.id}</span>
          </div>
          <span class="text-xs text-slate-400 font-mono">${inc.time_ago}</span>
        </div>

        <div class="flex space-x-4">
          <div class="w-36 h-24 rounded-lg overflow-hidden bg-slate-900 relative flex-shrink-0 border border-slate-200">
            ${inc.type === 'camera' && thumbSrc ? `
              <img src="${thumbSrc}" class="w-full h-full object-cover opacity-85" />
              <div class="absolute inset-0 border border-red-500 m-1 pointer-events-none"></div>
              <span class="absolute bottom-1 right-1 bg-black/80 text-[9px] font-mono text-white px-1 rounded">${inc.timestamp}</span>
            ` : `
              <div class="w-full h-full flex flex-col items-center justify-center bg-slate-100 text-slate-400 p-2 text-center">
                <span class="font-mono text-xs font-bold text-slate-600">ULTRASONIC</span>
                <span class="text-[10px] text-slate-400">Telemetry Outfall</span>
              </div>
            `}
          </div>

          <div class="flex-1 flex flex-col justify-between">
            <div>
              <h3 class="text-sm font-bold text-slate-900 leading-snug">${inc.location}</h3>
              <p class="text-xs text-slate-500 line-clamp-2 mt-1">${inc.description}</p>
            </div>
            <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
              <span class="text-xs font-bold font-mono text-[#0e7c86]">${inc.garbage_area || 'Telemetry'}</span>
              <div class="flex items-center space-x-1">
                <span class="text-xs font-mono font-black ${isSev5 ? 'text-red-600' : 'text-amber-600'}">${inc.risk_score}</span>
                <span class="text-[10px] uppercase font-mono text-slate-400">RISK</span>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end space-x-2 mt-3 pt-2 border-t border-slate-100">
          <button class="px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded border border-slate-200 transition" onclick="event.stopPropagation(); resolveIncident('${inc.id}')">
            Resolve
          </button>
          <button class="px-3 py-1 text-xs font-semibold text-white bg-[#0e7c86] hover:bg-[#09535a] rounded transition" onclick="event.stopPropagation(); dispatchCrew('${inc.id}')">
            ${inc.assigned_crew ? `Crew ${inc.assigned_crew} Assigned` : 'Dispatch Crew'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function selectIncident(incidentId) {
  selectedIncidentId = incidentId;
  renderIncidentList();
  renderDetailPanel();
}

function renderDetailPanel() {
  const container = document.getElementById("detail-panel-container");
  const inc = INCIDENTS_DATA.find(i => i.id === selectedIncidentId);
  if (!container || !inc) return;

  const isSev5 = inc.severity === 5;
  const activeFrameSrc = (inc.filmstrip && inc.filmstrip.length > 0)
    ? (inc.filmstrip.find(f => f.active)?.src || inc.filmstrip[0].src)
    : "";

  container.innerHTML = `
    <div class="flex items-center justify-between pb-3 border-b border-slate-200">
      <div>
        <div class="flex items-center space-x-2 font-mono text-xs">
          <span class="font-bold text-slate-800">${inc.id}</span>
          <span class="text-slate-400">•</span>
          <span class="text-slate-600">${inc.cam_id}</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isSev5 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">
            ${isSev5 ? 'CRITICAL BLOCKAGE DETECTED' : 'ELEVATED SURGE ALERT'}
          </span>
        </div>
        <h2 class="text-lg font-extrabold text-slate-900 mt-0.5">${inc.location}</h2>
      </div>
      <div class="flex items-center space-x-2">
        <button class="px-2.5 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 rounded text-slate-700 transition" onclick="alert('Streamlit live CCTV replay accessible at http://localhost:8501')">
          LIVE REPLAY ↗
        </button>
      </div>
    </div>

    <!-- Main CCTV Video / Feed Inspector with Bounding Box -->
    <div class="mt-4 bg-slate-950 rounded-xl overflow-hidden relative border border-slate-800">
      <div class="h-72 w-full relative">
        ${activeFrameSrc ? `
          <img id="main-inspector-frame" src="${activeFrameSrc}" class="w-full h-full object-cover" />
          <div class="absolute inset-x-12 inset-y-8 border-2 border-red-500 pointer-events-none rounded bg-red-500/10 flex items-start justify-between p-2">
            <span class="bg-red-600 text-white font-mono text-[10px] px-1.5 py-0.5 rounded font-bold">
              [BOX: 420x280 | PLASTIC & SILT | AREA: ${inc.garbage_area || '50%'} | RISK: ${inc.risk_score}%]
            </span>
            <span class="bg-black/70 text-red-400 font-mono text-[10px] px-1 rounded">SURCHARGE SPIKE</span>
          </div>
        ` : `
          <div class="w-full h-full flex flex-col items-center justify-center text-slate-400">
            <span class="text-3xl mb-1">📡</span>
            <span class="font-mono text-sm">ULTRASONIC TELEMETRY SENSOR</span>
            <span class="text-xs text-slate-500">Live depth: ${inc.water_level}</span>
          </div>
        `}
      </div>
      <div class="p-3 bg-slate-900 text-white flex items-center justify-between text-xs font-mono border-t border-slate-800">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
          <span>AI ENGINE: YOLOE SEGMENTATION & GEMINI VISION</span>
        </div>
        <div class="text-slate-400">BLOCKAGE PROBABILITY: <span class="text-emerald-400 font-bold">96.4%</span></div>
      </div>
    </div>

    <!-- Sequential Key Frame Timeline -->
    ${inc.filmstrip && inc.filmstrip.length > 0 ? `
      <div class="mt-4">
        <div class="flex justify-between items-center text-xs font-mono text-slate-500 mb-2">
          <span class="font-bold uppercase tracking-wider">Sequential Key Frame Timeline</span>
          <span class="text-teal-600 font-medium">Click frame to inspect</span>
        </div>
        <div class="grid grid-cols-4 gap-2">
          ${inc.filmstrip.map((frame, idx) => `
            <div class="cursor-pointer border-2 ${frame.active ? 'border-[#0e7c86]' : 'border-slate-200 hover:border-slate-400'} rounded-lg overflow-hidden bg-slate-900 transition" onclick="switchFrame('${frame.src}')">
              <img src="${frame.src}" class="h-16 w-full object-cover" />
              <div class="p-1 bg-white text-[10px] font-mono text-slate-600 truncate">${frame.time}</div>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <!-- AI Volumetric & Hydrological Diagnosis -->
    <div class="mt-4 bg-[#f8fafc] border border-slate-200 rounded-xl p-4">
      <div class="flex items-center space-x-2 text-xs font-bold text-slate-700 mb-1">
        <span class="text-teal-600">✦</span>
        <span>AI Diagnostic Report</span>
      </div>
      <p class="text-xs text-slate-600 leading-relaxed">
        ${inc.description}
      </p>
      <div class="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-200 text-center font-mono">
        <div class="bg-white p-2 rounded border border-slate-100">
          <span class="text-[10px] text-slate-400 block">RISK SCORE</span>
          <span class="text-sm font-bold text-red-600">${inc.risk_score}/100</span>
        </div>
        <div class="bg-white p-2 rounded border border-slate-100">
          <span class="text-[10px] text-slate-400 block">GARBAGE AREA</span>
          <span class="text-sm font-bold text-slate-800">${inc.garbage_area || 'N/A'}</span>
        </div>
        <div class="bg-white p-2 rounded border border-slate-100">
          <span class="text-[10px] text-slate-400 block">WATER LEVEL</span>
          <span class="text-sm font-bold text-slate-800">${inc.water_level || '1.4m'}</span>
        </div>
        <div class="bg-white p-2 rounded border border-slate-100">
          <span class="text-[10px] text-slate-400 block">RUNOFF THREAT</span>
          <span class="text-sm font-bold text-red-600">${inc.run_threat || 'HIGH'}</span>
        </div>
      </div>
    </div>

    <!-- SOP Recommendation -->
    <div class="mt-4 bg-teal-50/60 border border-teal-200 rounded-xl p-3 text-xs">
      <span class="font-bold text-[#09535a] block mb-0.5">Standard Operating Procedure (SOP-PMC-07):</span>
      <span class="text-slate-700">${inc.sop || 'Deploy rapid clearance unit to clear inlet.'}</span>
    </div>

    <!-- Emergency Dispatch Crew Actions -->
    <div class="mt-4 flex items-center justify-between gap-3 pt-2">
      <button class="w-1/3 py-2.5 rounded-lg border border-slate-300 font-semibold text-xs text-slate-700 hover:bg-slate-100 transition" onclick="resolveIncident('${inc.id}')">
        Mark Resolved
      </button>
      <button class="w-2/3 py-2.5 rounded-lg bg-[#0e7c86] hover:bg-[#09535a] text-white font-bold text-xs shadow-md transition flex items-center justify-center space-x-2" onclick="dispatchCrew('${inc.id}')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        <span>${inc.assigned_crew ? `Re-dispatch Crew (${inc.assigned_crew})` : 'Dispatch Crew Unit PMC-04 Now'}</span>
      </button>
    </div>
  `;
}

function switchFrame(frameSrc) {
  const mainFrame = document.getElementById("main-inspector-frame");
  if (mainFrame) mainFrame.src = frameSrc;
}

async function resolveIncident(id) {
  const inc = INCIDENTS_DATA.find(i => i.id === id);
  if (inc) inc.status = "resolved";

  if (window.ApiClient) {
    await ApiClient.resolveIncident(id);
  }

  updateStats();
  renderIncidentList();
  renderDetailPanel();
  alert(`Incident ${id} marked as RESOLVED.`);
}

async function dispatchCrew(id) {
  const inc = INCIDENTS_DATA.find(i => i.id === id);
  if (inc) {
    inc.status = "crews";
    inc.assigned_crew = "PMC-04";
  }

  if (window.ApiClient) {
    await ApiClient.dispatchCrew(id, "PMC-04");
  }

  updateStats();
  renderIncidentList();
  renderDetailPanel();
  alert(`Emergency Response Crew Unit PMC-04 successfully dispatched to ${id}. Incident status updated to 'In Field'.`);
}

// Event Listeners setup
document.addEventListener("DOMContentLoaded", () => {
  // Tabs
  document.querySelectorAll(".queue-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".queue-tab-btn").forEach(b => {
        b.classList.remove("active", "bg-[#0e7c86]", "text-white");
        b.classList.add("bg-slate-100", "text-slate-600");
      });
      btn.classList.add("active", "bg-[#0e7c86]", "text-white");
      btn.classList.remove("bg-slate-100", "text-slate-600");
      currentFilter = btn.getAttribute("data-filter");
      renderIncidentList();
    });
  });

  // Zone filter
  const zoneSelect = document.getElementById("filter-zone");
  if (zoneSelect) {
    zoneSelect.addEventListener("change", (e) => {
      currentZone = e.target.value;
      renderIncidentList();
    });
  }

  // Search input
  const searchInput = document.getElementById("incident-search");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      currentSearch = e.target.value;
      renderIncidentList();
    });
  }

  // Sort Risk toggle
  const sortBtn = document.getElementById("btn-sort-risk");
  if (sortBtn) {
    sortBtn.addEventListener("click", () => {
      sortDesc = !sortDesc;
      const ind = document.getElementById("sort-indicator");
      if (ind) ind.textContent = sortDesc ? "↓" : "↑";
      renderIncidentList();
    });
  }

  // Export Log button
  const exportBtn = document.getElementById("btn-export-log");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(INCIDENTS_DATA, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `PMC_Drainage_Incidents_${new Date().toISOString().slice(0,10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    });
  }

  initData();
});
