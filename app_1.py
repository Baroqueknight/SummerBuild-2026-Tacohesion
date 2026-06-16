import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
import math
import time
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Municipal Eco-OS & Fleet Telematics", layout="wide")

# =====================================================================
# CORE SIMULATION DATA & CONSTANTS
# =====================================================================
CITY_DEPOT = (10.7626, 106.6602)

CO2_FACTORS = {
    "Recyclable_Recycled": 0.05,
    "Recyclable_Incinerated": 0.85,
    "Landfill_Incinerated": 0.95,
    "Organic_Composted": 0.02,
    "Organic_Upcycled": 0.005
}

# Initialize State Engines
if "bins" not in st.session_state:
    st.session_state.bins = {
        "BIN-01 (Tourist Center)": {"lat": 10.7640, "lon": 106.6620, "type": "Recyclable", "capacity_kg": 200, "fill": 85.0, "hist_pattern": [40, 55, 70, 92, 45, 60, 88]},
        "BIN-02 (Residential A)": {"lat": 10.7610, "lon": 106.6580, "type": "Organic", "capacity_kg": 150, "fill": 40.0, "hist_pattern": [20, 30, 42, 50, 60, 75, 40]},
        "BIN-03 (Market District)": {"lat": 10.7680, "lon": 106.6650, "type": "Landfill", "capacity_kg": 300, "fill": 90.0, "hist_pattern": [80, 85, 90, 95, 88, 92, 99]},
        "BIN-04 (Tech Park)": {"lat": 10.7590, "lon": 106.6610, "type": "Recyclable", "capacity_kg": 200, "fill": 32.0, "hist_pattern": [10, 15, 22, 35, 40, 20, 15]}
    }

if "citizens_db" not in st.session_state:
    st.session_state.citizens_db = {
        "UID-8821": {"name": "Alex Morgan", "credits": 340, "scans": 14},
        "UID-4512": {"name": "Jamie Nguyen", "credits": 890, "scans": 32},
        "UID-3091": {"name": "Elena Rostova", "credits": 120, "scans": 5}
    }

if "trucks_db" not in st.session_state:
    st.session_state.trucks_db = {
        "Truck-A (51C-555.22)": {"driver": "Tran Van H", "status": "Active", "fuel_efficiency": "28L/100km", "compressor_psi": 1850, "obd_codes": []},
        "Truck-B (51C-123.45)": {"driver": "Nguyen Van A", "status": "Maintenance Alert", "fuel_efficiency": "34L/100km", "compressor_psi": 1320, "obd_codes": ["P0234", "B1241"]},
        "Truck-C (51D-987.65)": {"driver": "Tran Thi B", "status": "Active", "fuel_efficiency": "27L/100km", "compressor_psi": 1910, "obd_codes": []}
    }

if "b2b_directory" not in st.session_state:
    st.session_state.b2b_directory = [
        {"partner": "GreenFeed Agricultural Corp", "type": "Animal Feed Redirection", "accepted_material": "Bakery Surplus & Clean Grains", "status": "Active Sourcing"},
        {"partner": "BioPlast Synthetics Lab", "type": "Industrial Upcycling", "accepted_material": "Heavy Starch & Waste Spent Oils", "status": "Capacity Available"}
    ]

if "historical_waste_logs" not in st.session_state:
    st.session_state.historical_waste_logs = [
        {"type": "Recyclable", "disposal": "Recycled", "weight_kg": 450.0, "co2_tonnes": 0.0225},
        {"type": "Landfill", "disposal": "Incinerated", "weight_kg": 1200.0, "co2_tonnes": 1.14},
        {"type": "Organic", "disposal": "Composted", "weight_kg": 600.0, "co2_tonnes": 0.012}
    ]

if "food_donated_kg" not in st.session_state:
    st.session_state.food_donated_kg = 145.0

# =====================================================================
# MAP LAYOUT RENDERER
# =====================================================================
def render_live_map(truck_gps=None, route_line=None):
    bin_data_list = []
    for b_id, details in st.session_state.bins.items():
        bin_data_list.append({
            "name": b_id, "lat": details["lat"], "lon": details["lon"], "fill": details["fill"], "type": details["type"],
            "weight": f"{(details['fill']/100)*details['capacity_kg']:.1f}/{details['capacity_kg']} kg",
            "color": [230, 50, 50, 200] if details["fill"] >= 75 else [50, 180, 50, 200]
        })
    df_bins = pd.DataFrame(bin_data_list)
    df_depot = pd.DataFrame([{"lat": CITY_DEPOT[0], "lon": CITY_DEPOT[1], "name": "Main Operations Base"}])
    
    layers = [
        pdk.Layer("HexagonLayer", data=df_depot, get_position="[lon, lat]", radius=150, elevation_scale=4, extruded=True, get_fill_color=[0, 100, 255, 200]),
        pdk.Layer("ScatterplotLayer", data=df_bins, get_position="[lon, lat]", get_color="color", get_radius=90, pickable=True, auto_highlight=True)
    ]
    
    if route_line:
        layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([{"path": route_line, "color": [255, 165, 0, 200]}]), get_path="path", get_color="color", width_min_pixels=4))
    if truck_gps:
        layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame([truck_gps]), get_position="[lon, lat]", get_color=[255, 140, 0, 255], get_radius=130))

    tooltip_template = {
        "html": """<div style='font-family: Arial; padding: 6px; background-color: #1a1a1a; color: white; border-radius: 4px;'>
                   <b style='color: #00fa9a;'>{name}</b><br/>Type: {type}<br/>Fill Level: {fill}%<br/>Load Weight: {weight}</div>""",
        "style": {"backgroundColor": "transparent", "zIndex": "10000"}
    }
    
    map_placeholder.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=pdk.ViewState(latitude=CITY_DEPOT[0], longitude=CITY_DEPOT[1], zoom=13.2, pitch=35),
        layers=layers, tooltip=tooltip_template
    ))

# =====================================================================
# NAVIGATION SIDEBAR PANEL
# =====================================================================
col1, col2 = st.columns([1.1, 0.9], gap="large")
st.sidebar.title("🏙️ Municipal Eco-OS")
st.sidebar.markdown("City Smart Infrastructure Control Matrix")
app_mode = st.sidebar.radio("Select Functional Control Console", [
    "🚛 Live Fleet & ML Predictive Analytics",
    "💳 Smart Gateways & Recycle-to-Earn",
    "🔧 Fleet Maintenance (OBD-II)",
    "🌾 B2B Upcycling & Bio-Directory"
])

# Global Analytics Data Aggregators
df_waste = pd.DataFrame(st.session_state.historical_waste_logs)
total_mass = df_waste["weight_kg"].sum() if not df_waste.empty else 0.0
total_co2 = df_waste["co2_tonnes"].sum() if not df_waste.empty else 0.0

# =====================================================================
# MODULE 1: PREDICTIVE LOGISTICS ENGINE
# =====================================================================
if app_mode == "🚛 Live Fleet & ML Predictive Analytics":
    st.header("🚛 Predictive Fleet Logistics Optimization")
    st.markdown("Uses time-series modeling to dispatch vehicles before container capacities overflow.")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Mass Diverted", f"{total_mass:,.1f} kg")
    m2.metric("Carbon Log (CO₂e)", f"{total_co2:,.4f} MT")
    m3.metric("Food Rescued Assets", f"{st.session_state.food_donated_kg:,.1f} kg")
    st.write("---")
    
    c1, c2 = st.columns([1.1, 0.9])
    
    with col1:
        st.header("🚛 Predictive Fleet Logistics Optimization")
        st.subheader("Machine Learning Time-Series Projections")
        selected_bin = st.selectbox("Select Target Telemetry Sensor Array Node", list(st.session_state.bins.keys()))
        
        # Simulate an ML multi-step forward horizon prediction vector graph
        hist_data = st.session_state.bins[selected_bin]["hist_pattern"]
        future_pred = [hist_data[-1] + int(np.sin(i)*15 + (i*4)) for i in range(1, 5)]
        future_pred = [min(100, max(0, x)) for x in future_pred] # clamping boundaries
        
        chart_df = pd.DataFrame({
            "Historical Steps (Days)": [f"D-{6-i}" for i in range(7)] + [f"T+{i}" for i in range(1, 5)],
            "Fill Capacity %": hist_data + future_pred,
            "Data Source Type": ["Historical Sensor Telemetry"]*7 + ["ML Time-Series Forecast (Prophet)"]*4
        })
        st.line_chart(chart_df, x="Historical Steps (Days)", y="Fill Capacity %")
        
        # Flag predictive warning alerts
        if max(future_pred) > 85:
            st.warning(f"⚠️ **Predictive Overflow Warning:** Node is projected to cross critical limits (`{max(future_pred)}%`) within a short execution window. Dispatch recommended.")
        
        st.subheader("Manual Sensor Telemetry Adjustments")
        for b_id, data in st.session_state.bins.items():
            st.session_state.bins[b_id]["fill"] = st.slider(f"📍 {b_id} Live Fill Level", 0.0, 100.0, float(data["fill"]))
            
        st.subheader("Fleet Unit Crew Deployment")
        selected_truck = st.selectbox("Assign Available Vehicle Asset", list(st.session_state.trucks_db.keys()))
        
        if st.button("Deploy Fleet & Track Live Run", type="primary"):
            bins_needing_pickup = [b_id for b_id, d in st.session_state.bins.items() if d["fill"] >= 75]
            if bins_needing_pickup:
                # Mock Routing Generation Vectors
                route_line = [[CITY_DEPOT[1], CITY_DEPOT[0]]]
                for b_id in bins_needing_pickup:
                    route_line.append([st.session_state.bins[b_id]["lon"], st.session_state.bins[b_id]["lat"]])
                route_line.append([CITY_DEPOT[1], CITY_DEPOT[0]])
                
                status_box = st.empty()
                for i in range(len(route_line) - 1):
                    for step in range(4):
                        alpha = step / 4.0
                        clon = route_line[i][0] + alpha * (route_line[i+1][0] - route_line[i][0])
                        clat = route_line[i][1] + alpha * (route_line[i+1][1] - route_line[i][1])
                        
                        truck_state = {"name": selected_truck, "lat": clat, "lon": clon, "fill": "N/A", "weight": "Active Duty"}
                        render_live_map(truck_gps=truck_state, route_line=route_line)
                        status_box.info(f"🛰️ **Live Dispatch Telemetry:** `{selected_truck}` is traversing route paths...")
                        time.sleep(0.08)
                
                # Flush and empty variables state
                for b_id in bins_needing_pickup:
                    b_info = st.session_state.bins[b_id]
                    mass = (b_info["fill"]/100)*b_info["capacity_kg"]
                    st.session_state.historical_waste_logs.append({
                        "type": b_info["type"], "disposal": "Recycled" if b_info["type"]=="Recyclable" else "Composted",
                        "weight_kg": mass, "co2_tonnes": (mass * CO2_FACTORS["Recyclable_Recycled"])/1000
                    })
                    st.session_state.bins[b_id]["fill"] = 0.0
                status_box.success("🏁 Collection route complete. Material data offloaded to registers.")
                time.sleep(1)
                st.rerun()
            else:
                st.info("All nodes operating within acceptable parameters.")

    with col2:
        map_placeholder = st.empty()
        render_live_map()
        
        st.write("---")
        st.markdown("**Mass Volume Breakdown by Disposal Type (kg)**")
        st.bar_chart(df_waste.groupby(["type", "disposal"]).sum().reset_index(), x="type", y="weight_kg", color="disposal", stack=False)

# =====================================================================
# MODULE 2: SMART GATEWAYS & GAMIFICATION
# =====================================================================
elif app_mode == "💳 Smart Gateways & Recycle-to-Earn":
    st.header("💳 Interactive IoT Access Control Gateways")
    st.markdown("Simulate smart hardware drop-off points featuring structural cross-contamination scanning controls.")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Hardware Simulation: Drop-off Scan Event")
        user_id = st.selectbox("Scan Citizen Authentication ID (NFC/RFID)", list(st.session_state.citizens_db.keys()))
        target_bin = st.selectbox("Select Target Unit Drop-off Interface Gateway", list(st.session_state.bins.keys()))
        dropped_type = st.selectbox("Material Dropped For Processing", ["Recyclable (Clean Plastic/Glass)", "Organic Material", "Contraband Item (Concrete/Lead Car Batteries)"])
        input_weight = st.number_input("Detected Container Load Mass (kg)", min_value=0.5, max_value=50.0, value=2.5)
        
        if st.button("Simulate Drop-off Closure Action"):
            if dropped_type == "Contraband Item (Concrete/Lead Car Batteries)":
                st.error("🚨 **Access Gateway Exception Triggered:** Internal infrared imaging and load sensors detected illegal hazard contaminants. Access door locked. Incident logged to profile.")
            else:
                credit_award = int(input_weight * 10)
                st.session_state.citizens_db[user_id]["credits"] += credit_award
                st.session_state.citizens_db[user_id]["scans"] += 1
                
                # Update physical container volume
                st.session_state.bins[target_bin]["fill"] = min(100.0, st.session_state.bins[target_bin]["fill"] + ((input_weight/st.session_state.bins[target_bin]['capacity_kg'])*100))
                st.success(f"🔓 **Gateway Secure Transaction Complete:** {credit_award} Eco-Credits awarded to user profile account.")
                time.sleep(1.5)
                st.rerun()
                
    with c2:
        st.subheader("Citizen Incentive Ledger Accounts")
        st.dataframe(pd.DataFrame(st.session_state.citizens_db).T, use_container_width=True)
        
        st.subheader("Municipal Token Marketplace Clearing House")
        st.markdown("""
        | Reward Item Ecosystem | Voucher Token Clearing Exchange Rate |
        | :--- | :--- |
        | 🎫 Municipal Subway Day Transit Pass | 150 Eco-Credits |
        | ⚡ Residential Electricity Bill Discount | 500 Eco-Credits |
        | ☕ Green Sourced Local Café Coupon | 100 Eco-Credits |
        """)

# =====================================================================
# MODULE 3: FLEET MAINTENANCE (OBD-II DIAGNOSTICS)
# =====================================================================
elif app_mode == "🔧 Fleet Maintenance (OBD-II)":
    st.header("🔧 Advanced Telematics Diagnostics (OBD-II Dashboard)")
    st.markdown("Tracks engine parameters and real-time engine fault diagnostics to optimize fleet availability.")
    
    for truck_id, telematics in st.session_state.trucks_db.items():
        with st.expander(f"🚛 {truck_id} — Operational Status Panel: {telematics['status']}"):
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("Fuel Consumption Profile", telematics["fuel_efficiency"])
            
            # Highlight diagnostic alerts for mechanical systems (e.g., compressor pressure)
            psi_color = "normal" if telematics["compressor_psi"] > 1500 else "inverse"
            tc2.metric("Hydraulic Compressor Fluid Force", f"{telematics['compressor_psi']} PSI", delta="CRITICAL PRESSURE LOSS" if telematics["compressor_psi"] < 1500 else "Stable", delta_color=psi_color)
            
            tc3.write("**Active Diagnostic Trouble Codes (DTC):**")
            if telematics["obd_codes"]:
                for code in telematics["obd_codes"]:
                    st.error(f"⚠️ **Code {code}:** Hydraulic Seals Degrading — Schedule Shop Inspection")
            else:
                st.success("✅ Zero active standard diagnostic codes reported.")

# =====================================================================
# MODULE 4: INDUSTRIAL B2B UP-CYCLING DIRECTORY
# =====================================================================
elif app_mode == "🌾 B2B Upcycling & Bio-Directory":
    st.header("🌾 B2B Industrial Food Upcycling Ecosystem")
    st.markdown("Intercepts clean, bulk enterprise-grade food waste before it goes to compost, routing it to commercial production lines instead.")
    
    uc1, uc2 = st.columns([1.0, 1.0])
    
    with uc1:
        st.subheader("Log Commercial Biomass Redirection Dispatch")
        with st.form("b2b_form", clear_on_submit=True):
            source_ent = st.text_input("Source Enterprise", "Central Bakery Mill Complex")
            material_desc = st.selectbox("Biomass Material Compound Category", ["Clean Spent Grain Slurry", "High Starch Pastry Surplus", "Spent Frying Oils"])
            volume_kg = st.number_input("Consignment Load Mass Weight (kg)", min_value=10.0, max_value=5000.0, value=250.0)
            target_partner = st.selectbox("Target Enterprise Sourcing Facility Match", [p["partner"] for p in st.session_state.b2b_directory])
            
            if st.form_submit_button("Authorize Commercial Manifest Freight"):
                co2_savings = (volume_kg * CO2_FACTORS["Organic_Upcycled"])/1000
                st.session_state.historical_waste_logs.append({
                    "type": "Organic", "disposal": "Upcycled", "weight_kg": volume_kg, "co2_tonnes": co2_savings
                })
                st.toast(f"Manifest signed. {volume_kg}kg routed directly to {target_partner}.", icon="🌾")
                time.sleep(1)
                st.rerun()
                
    with uc2:
        st.subheader("Registered Industrial Bio-Refinery Partnerships")
        st.dataframe(pd.DataFrame(st.session_state.b2b_directory), use_container_width=True)