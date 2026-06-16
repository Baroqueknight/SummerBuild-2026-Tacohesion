import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
import math
import time
import json
import random
from datetime import datetime, timedelta
from collections import defaultdict

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Municipal Eco-OS | Smart City Platform",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌿"
)

# =====================================================================
# GLOBAL CSS THEMING
# =====================================================================
st.markdown("""
<style>
    /* Dark cyberpunk-civic theme */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .stMetric { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 12px; }
    .stMetric label { color: #8b949e !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
    .stMetric [data-testid="stMetricValue"] { color: #39d353 !important; font-size: 1.6rem !important; font-weight: 700; }
    div[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
    .eco-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
    .alert-critical { border-left: 4px solid #f85149; background: #1a0d0d; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0; }
    .alert-high { border-left: 4px solid #d29922; background: #1a1400; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0; }
    .alert-medium { border-left: 4px solid #388bfd; background: #0d1526; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0; }
    .badge-green { background: #0d3321; color: #39d353; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-red { background: #3d0d0d; color: #f85149; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-yellow { background: #2d2000; color: #d29922; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .section-title { color: #8b949e; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px; }
    h1, h2, h3 { color: #e6edf3 !important; }
    .stButton > button { background: #238636; color: white; border: none; border-radius: 6px; font-weight: 600; }
    .stButton > button:hover { background: #2ea043; }
    .stDataFrame { border: 1px solid #21262d; border-radius: 8px; }
    hr { border-color: #21262d; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CONSTANTS
# =====================================================================
CITY_DEPOT = (10.7626, 106.6602)
CARBON_CREDIT_VALUATION = 45.00

CO2_FACTORS = {
    "Recyclable_Recycled": 0.05,
    "Recyclable_Incinerated": 0.85,
    "Landfill_Incinerated": 0.95,
    "Organic_Composted": 0.02,
    "Organic_Upcycled": 0.005,
    "Hazardous_Treated": 0.45,
    "Electronic_Recycled": 0.12
}

WASTE_TYPES = ["Recyclable", "Organic", "Landfill", "Hazardous", "Electronic"]

# =====================================================================
# SESSION STATE INITIALIZATION
# =====================================================================
def init_state():
    defaults = {
        "bins": {
            "BIN-01 (Tourist Center)": {"lat": 10.7640, "lon": 106.6620, "type": "Recyclable", "capacity_kg": 200, "fill": 85.0, "hist_pattern": [40,55,70,92,45,60,88], "last_collected": "2026-06-14 09:00", "sensor_health": "OK", "temperature_c": 28.4},
            "BIN-02 (Residential A)":  {"lat": 10.7610, "lon": 106.6580, "type": "Organic",    "capacity_kg": 150, "fill": 40.0, "hist_pattern": [20,30,42,50,60,75,40], "last_collected": "2026-06-15 07:30", "sensor_health": "OK", "temperature_c": 31.1},
            "BIN-03 (Market District)":{"lat": 10.7680, "lon": 106.6650, "type": "Landfill",   "capacity_kg": 300, "fill": 90.0, "hist_pattern": [80,85,90,95,88,92,99], "last_collected": "2026-06-13 14:00", "sensor_health": "Degraded", "temperature_c": 35.7},
            "BIN-04 (Tech Park)":      {"lat": 10.7590, "lon": 106.6610, "type": "Recyclable", "capacity_kg": 200, "fill": 32.0, "hist_pattern": [10,15,22,35,40,20,15], "last_collected": "2026-06-15 11:00", "sensor_health": "OK", "temperature_c": 27.2},
            "BIN-05 (Hospital Zone)":  {"lat": 10.7655, "lon": 106.6570, "type": "Hazardous",  "capacity_kg": 100, "fill": 65.0, "hist_pattern": [30,40,50,55,60,62,65], "last_collected": "2026-06-14 16:00", "sensor_health": "OK", "temperature_c": 24.0},
            "BIN-06 (University)":     {"lat": 10.7600, "lon": 106.6640, "type": "Electronic", "capacity_kg": 120, "fill": 22.0, "hist_pattern": [5,8,12,15,18,20,22],  "last_collected": "2026-06-15 08:00", "sensor_health": "OK", "temperature_c": 26.5},
        },
        "citizens_db": {
            "UID-8821": {"name": "Alex Morgan",   "credits": 340,  "scans": 14, "tier": "Silver", "co2_saved_kg": 28.5,  "join_date": "2025-11-03"},
            "UID-4512": {"name": "Jamie Nguyen",  "credits": 890,  "scans": 32, "tier": "Gold",   "co2_saved_kg": 71.2,  "join_date": "2025-09-15"},
            "UID-3091": {"name": "Elena Rostova", "credits": 120,  "scans": 5,  "tier": "Bronze", "co2_saved_kg": 9.8,   "join_date": "2026-01-22"},
            "UID-7745": {"name": "Duc Pham",      "credits": 1540, "scans": 58, "tier": "Platinum","co2_saved_kg": 130.1,"join_date": "2025-07-01"},
        },
        "trucks_db": {
            "Truck-A (51C-555.22)": {"driver": "Tran Van H",   "status": "Active",             "fuel_l100km": 28, "compressor_psi": 1850, "obd_codes": [],              "km_total": 42100, "last_service_km": 40000, "fuel_log": [28,27,29,28,30,27,28]},
            "Truck-B (51C-123.45)": {"driver": "Nguyen Van A", "status": "Maintenance Alert",  "fuel_l100km": 34, "compressor_psi": 1320, "obd_codes": ["P0234","B1241"],"km_total": 61800, "last_service_km": 58000, "fuel_log": [29,31,33,34,35,34,34]},
            "Truck-C (51D-987.65)": {"driver": "Tran Thi B",   "status": "Active",             "fuel_l100km": 27, "compressor_psi": 1910, "obd_codes": [],              "km_total": 29500, "last_service_km": 28000, "fuel_log": [27,26,27,28,27,26,27]},
            "Truck-D (51D-444.88)": {"driver": "Le Van C",     "status": "Off Duty",           "fuel_l100km": 31, "compressor_psi": 1780, "obd_codes": [],              "km_total": 18200, "last_service_km": 16000, "fuel_log": [31,30,31,32,31,30,31]},
        },
        "b2b_directory": [
            {"partner": "GreenFeed Agricultural Corp", "type": "Animal Feed Redirection",   "accepted_material": "Bakery Surplus & Clean Grains",    "status": "Active Sourcing",   "contact": "greenlink@gfa.vn",    "capacity_kg_day": 500},
            {"partner": "BioPlast Synthetics Lab",     "type": "Industrial Upcycling",      "accepted_material": "Heavy Starch & Waste Spent Oils",  "status": "Capacity Available","contact": "ops@bioplast.io",     "capacity_kg_day": 800},
            {"partner": "EcoMethane Energy Pte",       "type": "Biogas Conversion",         "accepted_material": "Organic Slurry & Food Waste",      "status": "Active Sourcing",   "contact": "supply@ecomethane.sg","capacity_kg_day": 1200},
        ],
        "historical_waste_logs": [
            {"date": "2026-06-09", "type": "Recyclable", "disposal": "Recycled",    "weight_kg": 450.0,  "co2_tonnes": 0.0225, "truck": "Truck-A"},
            {"date": "2026-06-10", "type": "Landfill",   "disposal": "Incinerated", "weight_kg": 1200.0, "co2_tonnes": 1.14,   "truck": "Truck-B"},
            {"date": "2026-06-11", "type": "Organic",    "disposal": "Composted",   "weight_kg": 600.0,  "co2_tonnes": 0.012,  "truck": "Truck-A"},
            {"date": "2026-06-12", "type": "Recyclable", "disposal": "Recycled",    "weight_kg": 380.0,  "co2_tonnes": 0.019,  "truck": "Truck-C"},
            {"date": "2026-06-13", "type": "Organic",    "disposal": "Upcycled",    "weight_kg": 290.0,  "co2_tonnes": 0.00145,"truck": "Truck-A"},
            {"date": "2026-06-14", "type": "Landfill",   "disposal": "Incinerated", "weight_kg": 980.0,  "co2_tonnes": 0.931,  "truck": "Truck-C"},
            {"date": "2026-06-15", "type": "Electronic", "disposal": "Recycled",    "weight_kg": 75.0,   "co2_tonnes": 0.00375,"truck": "Truck-A"},
        ],
        "anomalies_log": [
            {"timestamp": "2026-06-15 08:34", "node": "BIN-03 (Market District)",  "issue": "Spike > 40% in 5 Mins",          "severity": "High",     "resolved": False},
            {"timestamp": "2026-06-15 14:12", "node": "BIN-01 (Tourist Center)",   "issue": "Sensor Dropout (Null Voltage)",   "severity": "Medium",   "resolved": False},
            {"timestamp": "2026-06-14 23:01", "node": "BIN-05 (Hospital Zone)",    "issue": "Thermal Ceiling Breach (>40°C)",  "severity": "Critical", "resolved": True},
        ],
        "maintenance_schedule": [
            {"truck": "Truck-A (51C-555.22)", "task": "Oil & Filter Change",     "due_km": 44000, "due_date": "2026-07-10", "priority": "Scheduled"},
            {"truck": "Truck-B (51C-123.45)", "task": "Compressor Seal Repair",  "due_km": 61800, "due_date": "2026-06-17", "priority": "Urgent"},
            {"truck": "Truck-B (51C-123.45)", "task": "OBD P0234 Diagnosis",      "due_km": 61800, "due_date": "2026-06-17", "priority": "Urgent"},
            {"truck": "Truck-C (51D-987.65)", "task": "Tyre Rotation",           "due_km": 32000, "due_date": "2026-07-25", "priority": "Scheduled"},
        ],
        "food_donated_kg": 145.0,
        "carbon_credits_sold": 0.0,
        "notification_count": 3,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================
def solve_tsp_nearest_neighbor(depot, target_bin_ids):
    unvisited = list(target_bin_ids)
    current_loc = depot
    optimized_route = []
    while unvisited:
        next_closest = min(unvisited, key=lambda b_id: math.sqrt(
            (current_loc[0] - st.session_state.bins[b_id]["lat"])**2 +
            (current_loc[1] - st.session_state.bins[b_id]["lon"])**2
        ))
        optimized_route.append(next_closest)
        current_loc = (st.session_state.bins[next_closest]["lat"], st.session_state.bins[next_closest]["lon"])
        unvisited.remove(next_closest)
    return optimized_route

def get_fill_color(fill_pct):
    if fill_pct >= 90: return [248, 81, 73, 220]
    if fill_pct >= 75: return [210, 153, 34, 220]
    if fill_pct >= 50: return [255, 165, 0, 200]
    return [57, 211, 83, 200]

def get_df():
    return pd.DataFrame(st.session_state.historical_waste_logs)

def compute_kpis():
    df = get_df()
    if df.empty:
        return 0.0, 0.0, 0.0
    total_mass   = df["weight_kg"].sum()
    total_co2    = df["co2_tonnes"].sum()
    credit_value = (total_co2 - st.session_state.carbon_credits_sold) * CARBON_CREDIT_VALUATION
    return total_mass, total_co2, credit_value

def render_live_map(target_element, truck_gps=None, route_line=None):
    bin_data_list = []
    for b_id, d in st.session_state.bins.items():
        bin_data_list.append({
            "name": b_id, "lat": d["lat"], "lon": d["lon"],
            "fill": d["fill"], "type": d["type"],
            "weight": f"{(d['fill']/100)*d['capacity_kg']:.1f}/{d['capacity_kg']} kg",
            "color": get_fill_color(d["fill"])
        })
    df_bins   = pd.DataFrame(bin_data_list)
    df_depot  = pd.DataFrame([{"lat": CITY_DEPOT[0], "lon": CITY_DEPOT[1], "name": "Main Depot"}])

    layers = [
        pdk.Layer("HexagonLayer",    data=df_depot,  get_position="[lon, lat]", radius=150, elevation_scale=4, extruded=True, get_fill_color=[0,100,255,200]),
        pdk.Layer("ScatterplotLayer",data=df_bins,   get_position="[lon, lat]", get_color="color", get_radius=90, pickable=True, auto_highlight=True),
    ]
    if route_line:
        layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([{"path": route_line, "color": [255,165,0,200]}]),
            get_path="path", get_color="color", width_min_pixels=4))
    if truck_gps:
        layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame([truck_gps]),
            get_position="[lon, lat]", get_color=[255,140,0,255], get_radius=130))

    tooltip = {"html": """<div style='font-family:monospace;padding:8px;background:#161b22;color:#e6edf3;border:1px solid #21262d;border-radius:6px'>
               <b style='color:#39d353'>{name}</b><br/>Type: {type}<br/>Fill: {fill}%<br/>Load: {weight}</div>""",
               "style": {"backgroundColor":"transparent"}}

    target_element.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10",
        initial_view_state=pdk.ViewState(latitude=CITY_DEPOT[0], longitude=CITY_DEPOT[1], zoom=13.2, pitch=40),
        layers=layers, tooltip=tooltip
    ))

# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown("## 🌿 Eco-OS Platform")
    st.markdown("<span style='color:#8b949e;font-size:0.75rem'>HCMC Municipal Smart Infrastructure</span>", unsafe_allow_html=True)
    st.divider()

    # Live clock
    st.markdown(f"<div style='color:#39d353;font-size:0.8rem;font-family:monospace'>🟢 LIVE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
    st.divider()

    # Quick KPI strip
    total_mass, total_co2, credit_val = compute_kpis()
    bins_critical = sum(1 for d in st.session_state.bins.values() if d["fill"] >= 75)
    st.metric("Bins Critical", f"{bins_critical} / {len(st.session_state.bins)}")
    st.metric("CO₂e Offset", f"{total_co2:.3f} MT")
    st.divider()

    app_mode = st.radio("Navigation", [
        "🏠 Dashboard Overview",
        "🚛 Fleet & Predictive Logistics",
        "💳 Smart Gateways & Gamification",
        "🔧 Fleet Maintenance & OBD-II",
        "🌾 B2B Upcycling Network",
        "📉 Carbon Credits Desk",
        "📊 Waste Analytics & Reports",
        "⚠️ Anomaly Detection Engine",
        "🗓️ Maintenance Scheduler",
    ])

# =====================================================================
# MODULE 0 — DASHBOARD OVERVIEW
# =====================================================================
if app_mode == "🏠 Dashboard Overview":
    st.title("🌿 Municipal Eco-OS Control Centre")
    st.caption("Real-time smart waste infrastructure telemetry — Ho Chi Minh City")
    st.divider()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Waste Diverted", f"{total_mass:,.0f} kg", delta="+380 kg today")
    k2.metric("CO₂e Offset", f"{total_co2:.3f} MT", delta="+0.019 MT today")
    k3.metric("Carbon Credit Value", f"${credit_val:,.2f}", delta="+$0.86")
    k4.metric("Active Bins", f"{sum(1 for d in st.session_state.bins.values() if d['fill'] < 75)} OK / {len(st.session_state.bins)}")
    k5.metric("Citizen Participants", str(len(st.session_state.citizens_db)), delta="+1 this week")

    st.divider()
    col_map, col_status = st.columns([1.5, 1], gap="large")

    with col_map:
        st.markdown("#### 🗺️ Live Infrastructure Map")
        map_ph = st.empty()
        render_live_map(map_ph)

    with col_status:
        st.markdown("#### 📡 Bin Sensor Status")
        for b_id, d in st.session_state.bins.items():
            fill = d["fill"]
            badge = f"<span class='badge-red'>CRITICAL</span>" if fill >= 90 else \
                    f"<span class='badge-yellow'>HIGH</span>" if fill >= 75 else \
                    f"<span class='badge-green'>OK</span>"
            st.markdown(f"""<div class='eco-card'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                    <span style='font-size:0.85rem;font-weight:600'>{b_id.split('(')[1].rstrip(')')}</span>
                    {badge}
                </div>
                <div style='margin-top:6px;background:#21262d;border-radius:4px;height:6px'>
                    <div style='background:{"#f85149" if fill>=90 else "#d29922" if fill>=75 else "#39d353"};
                    width:{fill}%;height:6px;border-radius:4px'></div>
                </div>
                <div style='color:#8b949e;font-size:0.72rem;margin-top:4px'>{fill:.0f}% full · {d["type"]} · {d["temperature_c"]}°C</div>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🚨 Recent Anomalies")
    for a in st.session_state.anomalies_log[:3]:
        cls = "alert-critical" if a["severity"] == "Critical" else "alert-high" if a["severity"] == "High" else "alert-medium"
        status_icon = "✅" if a["resolved"] else "🔴"
        st.markdown(f"""<div class='{cls}'>
            {status_icon} <b>{a['node']}</b> — {a['issue']}
            <span style='color:#8b949e;font-size:0.75rem;float:right'>{a['timestamp']}</span>
        </div>""", unsafe_allow_html=True)

# =====================================================================
# MODULE 1 — FLEET & PREDICTIVE LOGISTICS
# =====================================================================
elif app_mode == "🚛 Fleet & Predictive Logistics":
    st.header("🚛 Predictive Fleet Logistics Optimization")
    st.caption("Time-series ML projections + TSP nearest-neighbour route solver")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Mass Diverted", f"{total_mass:,.1f} kg")
    m2.metric("Carbon Offset", f"{total_co2:.4f} MT CO₂e")
    m3.metric("Carbon Credit Ledger", f"${credit_val:,.2f} USD")
    st.divider()

    col1, col2 = st.columns([1.1, 0.9], gap="large")

    with col1:
        st.subheader("ML Fill Projection")
        selected_bin = st.selectbox("Select Sensor Node", list(st.session_state.bins.keys()))
        hist = st.session_state.bins[selected_bin]["hist_pattern"]

        future = [hist[-1] + int((i * 4.5) + np.sin(i * 1.2) * 5) for i in range(1, 5)]
        future = [min(100, max(0, x)) for x in future]

        chart_df = pd.DataFrame({
            "Day": [f"D-{6-i}" for i in range(7)] + [f"T+{i}" for i in range(1, 5)],
            "Fill %": hist + future,
            "Series": ["Historical"]*7 + ["Forecast"]*4
        })
        st.line_chart(chart_df, x="Day", y="Fill %")

        if max(future) > 85:
            st.warning(f"⚠️ Overflow predicted — peak at {max(future)}% within 4 steps.")

        st.subheader("Live Fill Adjustments")
        for b_id in st.session_state.bins:
            st.session_state.bins[b_id]["fill"] = st.slider(
                f"📍 {b_id}", 0.0, 100.0, float(st.session_state.bins[b_id]["fill"]), key=f"sl_{b_id}")

        st.subheader("Dispatch Assignment")
        active_trucks = [t for t, d in st.session_state.trucks_db.items() if d["status"] == "Active"]
        selected_truck = st.selectbox("Assign Vehicle", active_trucks if active_trucks else list(st.session_state.trucks_db.keys()))

        bins_needing_pickup = [b for b, d in st.session_state.bins.items() if d["fill"] >= 75]
        col_a, col_b = st.columns(2)
        deploy_btn  = col_a.button("🚀 Dispatch TSP Route", type="primary")
        collect_all = col_b.button("🗑️ Collect All Bins")

    with col2:
        map_ph = st.empty()
        render_live_map(map_ph)
        st.divider()
        st.subheader("📋 Work Ticket Manifest")
        if bins_needing_pickup:
            st.info(f"**Driver:** {st.session_state.trucks_db.get(selected_truck, {}).get('driver','—')} | **Vehicle:** {selected_truck}")
            for b in bins_needing_pickup:
                d = st.session_state.bins[b]
                load = (d["fill"]/100) * d["capacity_kg"]
                st.markdown(f"- `{b}` — **{d['fill']:.0f}%** full · {load:.1f} kg · {d['type']}")
            st.caption("⚠️ High-vis gear required in Market District zones.")
        else:
            st.success("✅ All bins within safe thresholds. No pickups required.")

    if collect_all:
        for b_id in st.session_state.bins:
            d = st.session_state.bins[b_id]
            mass = (d["fill"]/100) * d["capacity_kg"]
            if mass > 0:
                disposal = "Recycled" if d["type"] == "Recyclable" else "Composted" if d["type"] == "Organic" else "Incinerated"
                factor_key = f"{d['type']}_{'Recycled' if d['type']=='Recyclable' else 'Composted' if d['type']=='Organic' else 'Incinerated'}"
                factor = CO2_FACTORS.get(factor_key, 0.05)
                st.session_state.historical_waste_logs.append({
                    "date": datetime.now().strftime("%Y-%m-%d"), "type": d["type"],
                    "disposal": disposal, "weight_kg": mass,
                    "co2_tonnes": (mass * factor)/1000, "truck": selected_truck
                })
                st.session_state.bins[b_id]["fill"] = 0.0
                st.session_state.bins[b_id]["last_collected"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.success("All bins cleared and logged.")
        st.rerun()

    if deploy_btn and bins_needing_pickup:
        optimized = solve_tsp_nearest_neighbor(CITY_DEPOT, bins_needing_pickup)
        route_line = [[CITY_DEPOT[1], CITY_DEPOT[0]]]
        for b_id in optimized:
            route_line.append([st.session_state.bins[b_id]["lon"], st.session_state.bins[b_id]["lat"]])
        route_line.append([CITY_DEPOT[1], CITY_DEPOT[0]])

        status_box = st.empty()
        progress    = st.progress(0)
        total_steps = (len(route_line) - 1) * 4

        for i in range(len(route_line) - 1):
            for step in range(4):
                alpha = step / 4.0
                clon  = route_line[i][0] + alpha * (route_line[i+1][0] - route_line[i][0])
                clat  = route_line[i][1] + alpha * (route_line[i+1][1] - route_line[i][1])
                truck_state = {"name": selected_truck, "lat": clat, "lon": clon, "fill": "—", "weight": "En route"}
                render_live_map(map_ph, truck_gps=truck_state, route_line=route_line)
                status_box.info(f"🛰️ Tracking `{selected_truck}` — Segment {i+1}/{len(route_line)-1}")
                progress.progress((i * 4 + step + 1) / total_steps)
                time.sleep(0.07)

        for b_id in optimized:
            d    = st.session_state.bins[b_id]
            mass = (d["fill"]/100) * d["capacity_kg"]
            st.session_state.historical_waste_logs.append({
                "date": datetime.now().strftime("%Y-%m-%d"), "type": d["type"],
                "disposal": "Recycled" if d["type"]=="Recyclable" else "Composted",
                "weight_kg": mass, "co2_tonnes": (mass * CO2_FACTORS["Recyclable_Recycled"])/1000,
                "truck": selected_truck
            })
            st.session_state.bins[b_id]["fill"] = 0.0
            st.session_state.bins[b_id]["last_collected"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        status_box.success("🏁 Route complete — all bins cleared and waste logs updated.")
        progress.progress(1.0)
        time.sleep(1)
        st.rerun()

# =====================================================================
# MODULE 2 — SMART GATEWAYS & GAMIFICATION
# =====================================================================
elif app_mode == "💳 Smart Gateways & Gamification":
    st.header("💳 Smart Drop-off Gateways & Recycle-to-Earn")
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("🔑 Citizen Drop-off Simulation")
        user_id      = st.selectbox("Citizen NFC/RFID ID", list(st.session_state.citizens_db.keys()),
            format_func=lambda x: f"{x} — {st.session_state.citizens_db[x]['name']}")
        target_bin   = st.selectbox("Target Gateway Bin", list(st.session_state.bins.keys()))
        dropped_type = st.selectbox("Material Type", ["Recyclable (Clean Plastic/Glass)", "Organic Material", "Electronic Waste", "Contraband (Batteries/Concrete)"])
        input_weight = st.number_input("Weight (kg)", min_value=0.5, max_value=50.0, value=2.5)

        if st.button("✅ Process Drop-off", type="primary"):
            if "Contraband" in dropped_type:
                st.error("🚨 GATEWAY LOCKED — Infrared scan detected illegal contaminants. Incident logged.")
                st.session_state.anomalies_log.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "node": target_bin, "issue": f"Contraband attempt by {user_id}",
                    "severity": "High", "resolved": False
                })
            else:
                multiplier = 15 if "Electronic" in dropped_type else 10
                credit_award = int(input_weight * multiplier)
                co2_kg = input_weight * 0.05
                st.session_state.citizens_db[user_id]["credits"] += credit_award
                st.session_state.citizens_db[user_id]["scans"]   += 1
                st.session_state.citizens_db[user_id]["co2_saved_kg"] += co2_kg

                # Tier upgrade check
                c = st.session_state.citizens_db[user_id]
                if c["credits"] >= 1500 and c["tier"] != "Platinum": st.session_state.citizens_db[user_id]["tier"] = "Platinum"
                elif c["credits"] >= 700 and c["tier"] not in ["Gold","Platinum"]: st.session_state.citizens_db[user_id]["tier"] = "Gold"
                elif c["credits"] >= 200 and c["tier"] == "Bronze": st.session_state.citizens_db[user_id]["tier"] = "Silver"

                fill_delta = (input_weight / st.session_state.bins[target_bin]["capacity_kg"]) * 100
                st.session_state.bins[target_bin]["fill"] = min(100.0, st.session_state.bins[target_bin]["fill"] + fill_delta)

                st.success(f"✅ Processed! **+{credit_award} Eco-Credits** awarded to {st.session_state.citizens_db[user_id]['name']}")
                st.info(f"🌱 Estimated CO₂ offset: **{co2_kg:.2f} kg**")

    with col2:
        st.subheader("🏆 Citizen Leaderboard")
        lb_data = sorted(st.session_state.citizens_db.items(), key=lambda x: x[1]["credits"], reverse=True)
        tier_icons = {"Platinum": "💎", "Gold": "🥇", "Silver": "🥈", "Bronze": "🥉"}
        for rank, (uid, data) in enumerate(lb_data, 1):
            st.markdown(f"""<div class='eco-card'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                    <span><b>#{rank}</b> &nbsp; {tier_icons.get(data['tier'],'🔵')} {data['name']}</span>
                    <span style='color:#39d353;font-weight:700'>{data['credits']:,} credits</span>
                </div>
                <div style='color:#8b949e;font-size:0.75rem;margin-top:4px'>{uid} · {data['scans']} scans · {data['co2_saved_kg']:.1f} kg CO₂ offset · {data['tier']}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("🎁 Redeem Eco-Credits")
        redeem_user   = st.selectbox("Citizen", list(st.session_state.citizens_db.keys()),
            format_func=lambda x: f"{st.session_state.citizens_db[x]['name']} ({st.session_state.citizens_db[x]['credits']} credits)", key="redeem_sel")
        reward_option = st.selectbox("Reward", ["Bus Pass (50 credits)", "Market Voucher 20k VND (100 credits)", "Tree Planting Certificate (200 credits)", "Carbon Offset Badge (500 credits)"])
        cost          = int(reward_option.split("(")[1].split(" ")[0])
        if st.button(f"Redeem for {cost} credits"):
            if st.session_state.citizens_db[redeem_user]["credits"] >= cost:
                st.session_state.citizens_db[redeem_user]["credits"] -= cost
                st.success(f"✅ {reward_option.split('(')[0].strip()} redeemed!")
                st.rerun()
            else:
                st.error("Insufficient credits.")

# =====================================================================
# MODULE 3 — FLEET MAINTENANCE & OBD-II
# =====================================================================
elif app_mode == "🔧 Fleet Maintenance & OBD-II":
    st.header("🔧 Fleet Telematics & OBD-II Diagnostics")

    for truck_id, t in st.session_state.trucks_db.items():
        km_since_service = t["km_total"] - t["last_service_km"]
        health_pct = max(0, 100 - int((km_since_service / 6000) * 100))
        status_color = "#f85149" if t["status"] == "Maintenance Alert" else "#39d353" if t["status"] == "Active" else "#8b949e"

        with st.expander(f"🚛 {truck_id} — {t['driver']} · {t['status']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fuel Rate",          f"{t['fuel_l100km']} L/100km",  delta=f"{'⬆ High' if t['fuel_l100km']>30 else '✓ Normal'}")
            c2.metric("Compressor PSI",     f"{t['compressor_psi']} PSI",   delta="CRITICAL" if t["compressor_psi"] < 1500 else "OK", delta_color="inverse" if t["compressor_psi"] < 1500 else "normal")
            c3.metric("Odometer",           f"{t['km_total']:,} km")
            c4.metric("Engine Health Est.", f"{health_pct}%",               delta="Service Due" if km_since_service > 4000 else "OK", delta_color="inverse" if km_since_service > 4000 else "normal")

            st.markdown("**7-Day Fuel Consumption Trend**")
            fuel_df = pd.DataFrame({"Day": [f"D-{6-i}" for i in range(7)], "L/100km": t["fuel_log"]})
            st.line_chart(fuel_df, x="Day", y="L/100km", height=150)

            if t["obd_codes"]:
                st.markdown("**⚠️ Active Diagnostic Trouble Codes**")
                dtc_descriptions = {"P0234": "Turbocharger Overboost Condition", "B1241": "Hydraulic Seal Degradation Detected"}
                for code in t["obd_codes"]:
                    st.markdown(f"<div class='alert-critical'><b>{code}</b> — {dtc_descriptions.get(code, 'Unknown fault')}</div>", unsafe_allow_html=True)
                if st.button(f"Clear DTCs for {truck_id}", key=f"clear_{truck_id}"):
                    st.session_state.trucks_db[truck_id]["obd_codes"] = []
                    st.session_state.trucks_db[truck_id]["status"] = "Active"
                    st.success("DTCs cleared. Status reset to Active.")
                    st.rerun()
            else:
                st.success("✅ No active diagnostic codes.")

# =====================================================================
# MODULE 4 — B2B UPCYCLING NETWORK
# =====================================================================
elif app_mode == "🌾 B2B Upcycling Network":
    st.header("🌾 Industrial B2B Upcycling Ecosystem")
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("Log Biomass Redirection Dispatch")
        with st.form("b2b_form", clear_on_submit=True):
            source_ent    = st.text_input("Source Enterprise", "Central Bakery Mill Complex")
            material_desc = st.selectbox("Material Type", ["Clean Spent Grain Slurry", "High Starch Pastry Surplus", "Spent Frying Oils", "Food Packaging Waste"])
            volume_kg     = st.number_input("Consignment Mass (kg)", min_value=10.0, max_value=5000.0, value=250.0)
            target_partner= st.selectbox("Target Partner", [p["partner"] for p in st.session_state.b2b_directory])
            notes         = st.text_area("Dispatch Notes", placeholder="Temperature requirements, handling instructions...")
            if st.form_submit_button("📦 Authorise Manifest", type="primary"):
                factor = CO2_FACTORS["Organic_Upcycled"]
                st.session_state.historical_waste_logs.append({
                    "date": datetime.now().strftime("%Y-%m-%d"), "type": "Organic", "disposal": "Upcycled",
                    "weight_kg": volume_kg, "co2_tonnes": (volume_kg * factor)/1000, "truck": "B2B Direct"
                })
                st.toast(f"✅ {volume_kg:.0f}kg manifest authorised → {target_partner}", icon="🌾")
                time.sleep(1)
                st.rerun()

    with col2:
        st.subheader("🌾 Registered Biorefinery Partners")
        for p in st.session_state.b2b_directory:
            st.markdown(f"""<div class='eco-card'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                    <span><b>{p['partner']}</b></span>
                    <span class='badge-green'>{p['status']}</span>
                </div>
                <div style='color:#8b949e;font-size:0.75rem;margin-top:6px'>
                    <b>Type:</b> {p['type']}<br/>
                    <b>Accepted:</b> {p['accepted_material']}<br/>
                    <b>Capacity:</b> {p['capacity_kg_day']} kg/day · <b>Contact:</b> {p['contact']}
                </div>
            </div>""", unsafe_allow_html=True)

# =====================================================================
# MODULE 5 — CARBON CREDITS DESK
# =====================================================================
elif app_mode == "📉 Carbon Credits Desk":
    st.header("📉 Carbon Offsets & Compliance Ledger")
    st.caption("Tokenized diversion verification framework tracking international offsets trade values.")

    total_mass, total_co2, credit_val = compute_kpis()

    c1, c2, c3 = st.columns(3)
    c1.metric("Accrued Carbon Baseline Saved", f"{total_co2:.4f} MT CO₂e")
    c2.metric("Market Clearing Value (USD/MT)", f"${CARBON_CREDIT_VALUATION:,.2f}")
    c3.metric("Available Settlement Equity", f"${credit_val:,.2f}")

    st.divider()
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("💼 Liquidity Clearing House")
        st.markdown("Trade verified municipal offsets to corporate compliance entities.")
        
        max_sellable = max(0.0, total_co2 - st.session_state.carbon_credits_sold)
        trade_amt = st.number_input("Volume to Liquidate (MT)", min_value=0.0, max_value=float(max_sellable), value=min(0.1, max_sellable), step=0.01)
        
        if st.button("Execute Institutional Settlement Block", type="primary"):
            if trade_amt > 0:
                st.session_state.carbon_credits_sold += trade_amt
                payout = trade_amt * CARBON_CREDIT_VALUATION
                st.success(f"💸 Settlement Certified! Wrapped contract of **{trade_amt:.4f} MT** liquidated for **${payout:,.2f} USD**.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("No valid carbon balance available for clearing.")

    with col2:
        st.subheader("📑 Global Compliance Audit Profile")
        st.markdown(f"""
        <div class='eco-card'>
            <b>Total Lifetime Offsets Generated:</b> {total_co2:.4f} MT<br/>
            <b>Total Assets Liquidated to Date:</b> {st.session_state.carbon_credits_sold:.4f} MT<br/>
            <b>Outstanding Vault Holdings:</b> {max_sellable:.4f} MT<br/>
            <hr style='margin:10px 0; border-color:#21262d;'>
            <span style='color:#8b949e; font-size:0.75rem;'>Verified via Gold Standard Framework Methodology Framework V2.6.</span>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# MODULE 6 — WASTE ANALYTICS & REPORTS
# =====================================================================
elif app_mode == "📊 Waste Analytics & Reports":
    st.header("📊 Deep Data Analytics & Stream Logs")
    
    df = get_df()
    if df.empty:
        st.info("No historical ledger logs compiled yet.")
    else:
        t1, t2 = st.tabs(["🗃️ Historical Ledger Data", "📈 Volumetric Aggregations"])
        
        with t1:
            st.subheader("Raw Telemetry Audit Stream")
            st.dataframe(df, use_container_width=True)
            
        with t2:
            st.subheader("Diversion Footprint by Stream Type")
            type_summary = df.groupby("type")["weight_kg"].sum().reset_index()
            st.bar_chart(type_summary, x="type", y="weight_kg")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Disposal Routing Architecture**")
                disp_summary = df.groupby("disposal")["weight_kg"].sum()
                st.dataframe(disp_summary)
            with c2:
                st.markdown("**Vehicle Log Apportionment**")
                truck_summary = df.groupby("truck")["weight_kg"].count().rename("Pickups Actioned")
                st.dataframe(truck_summary)

# =====================================================================
# MODULE 7 — ANOMALY DETECTION ENGINE
# =====================================================================
elif app_mode == "⚠️ Anomaly Detection Engine":
    st.header("⚠️ Infrastructure Anomaly & Threat Detection Matrix")
    st.caption("Active monitoring of distributed arrays for structural tampering and sensor hardware faults.")

    st.subheader("Active Infrastructure Exception Log")
    
    for idx, a in enumerate(st.session_state.anomalies_log):
        cls = "alert-critical" if a["severity"] == "Critical" else "alert-high" if a["severity"] == "High" else "alert-medium"
        badge = "<span class='badge-green'>RESOLVED</span>" if a["resolved"] else "<span class='badge-red'>UNRESOLVED</span>"
        
        st.markdown(f"""
        <div class='{cls}'>
            <div style='display:flex; justify-content:space-between;'>
                <b>{a['node']}</b>
                {badge}
            </div>
            <div style='margin-top:4px; font-size:0.85rem;'>{a['issue']}</div>
            <div style='color:#8b949e; font-size:0.75rem; margin-top:4px;'>Logged at: {a['timestamp']} · Priority: {a['severity']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if not a["resolved"]:
            if st.button(f"Mark Fixed — Close Incident #{idx}", key=f"res_{idx}"):
                st.session_state.anomalies_log[idx]["resolved"] = True
                st.success("Ticket updated successfully.")
                time.sleep(0.5)
                st.rerun()

    st.divider()
    st.subheader("🧪 Hardware Simulation Panel")
    st.markdown("Inject artificial edge cases into the stream telemetry array.")
    
    sim_node = st.selectbox("Target Node Array", list(st.session_state.bins.keys()))
    sim_issue = st.selectbox("Fault Vector Matrix", [
        "Sudden Structural Weight Surge (>75kg/min)",
        "Ultrasonic Sensor Dropout (Zero Voltage Exception)",
        "Chamber Thermal Runaway Event (>55°C)",
        "Chamber Lid Tamper Switch Disconnection Fault"
    ])
    sim_severity = st.selectbox("Risk Level Classification", ["Medium", "High", "Critical"])
    
    if st.button("Inject Simulated Threat Signature"):
        st.session_state.anomalies_log.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "node": sim_node,
            "issue": sim_issue,
            "severity": sim_severity,
            "resolved": False
        })
        st.error(f"🚨 Security Alert: Injected threat footprint onto node: {sim_node}")
        time.sleep(1)
        st.rerun()

# =====================================================================
# MODULE 8 — MAINTENANCE SCHEDULER
# =====================================================================
elif app_mode == "🗓️ Maintenance Scheduler":
    st.header("🗓️ Fleet Asset Maintenance Scheduler")
    st.caption("Predictive asset servicing thresholds and lifecycle coordination logs.")

    col1, col2 = st.columns([1.2, 0.8], gap="large")

    with col1:
        st.subheader("📋 Scheduled Work Orders")
        sched_df = pd.DataFrame(st.session_state.maintenance_schedule)
        st.dataframe(sched_df, use_container_width=True)

    with col2:
        st.subheader("➕ Create Preventive Maintenance Block")
        with st.form("sched_form", clear_on_submit=True):
            m_truck = st.selectbox("Target Fleet Asset", list(st.session_state.trucks_db.keys()))
            m_task = st.text_input("Task Assignment Name", placeholder="e.g. Hydraulic Cylinder Flush")
            m_km = st.number_input("Target Odometer Mileage (km)", min_value=0, value=int(st.session_state.trucks_db[m_truck]["km_total"] + 2000))
            m_date = st.date_input("Scheduled Target Date", value=datetime.now() + timedelta(days=14))
            m_prio = st.selectbox("Priority Core Classification", ["Routine", "Scheduled", "Urgent"])
            
            if st.form_submit_button("📅 Log Service Window", type="primary"):
                if m_task:
                    st.session_state.maintenance_schedule.append({
                        "truck": m_truck, "task": m_task, "due_km": m_km, "due_date": str(m_date), "priority": m_prio
                    })
                    st.toast(f"Preventive task registered for {m_truck}", icon="⚙️")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Task profile name field cannot be empty.")