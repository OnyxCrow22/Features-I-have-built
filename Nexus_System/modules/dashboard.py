import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import time

st.set_page_config(page_title="Airspace Tracker", page_icon="✈️", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nexus.db")
WATCHLIST_PATH = os.path.join(BASE_DIR, "aircraft_watchlist.json")

def get_database_connection():
    return sqlite3.connect(DB_PATH)

def load_aircraft():
    if not os.path.exists(DB_PATH):
        st.warning("Database not found. Please run the aircraft tracker first.")
        return pd.DataFrame()  # Return an empty DataFrame if the database doesn't exist

    connect = get_database_connection()
    query = """SELECT callsign AS "Callsign", registration AS "Registration", aircraft_type AS "Type", 
    distance_miles AS "Distance (Mi)", is_watchlist AS "Watchlist Match", 
    formatted_time AS "Time Detected", icao24 AS "ICAO Hex" FROM aircraft_cache ORDER BY timestamp DESC"""

    df = pd.read_sql_query(query, connect)
    connect.close()

    if not df.empty:
        df["Watchlist Match"] = df["Watchlist Match"].astype(bool)
    return df

def load_watchlist():
    if os.path.exists(WATCHLIST_PATH):
        with open(WATCHLIST_PATH, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass  # Handle the case where the JSON is invalid
    return {"registrations": [], "callsigns": [], "hexes": []}

def save_watchlist(watchlist):
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(watchlist, f, indent=4)

st.title("Airspace Tracker Dashboard")
st.caption("This dashboard displays aircraft detected in your local airspace, highlighting those that match your watchlist.")

df_aircraft = load_aircraft()

col1, col2, col3, col4 = st.columns(4)

total_logged = len(df_aircraft) if not df_aircraft.empty else 0
watchlist_match = df_aircraft["Watchlist Match"].sum() if not df_aircraft.empty else 0
uncommon_match = total_logged - watchlist_match
last_updated = df_aircraft["Time Detected"].max() if not df_aircraft.empty else "N/A"

with col1:
    st.metric(label="Total Aircraft Logged", value=total_logged)

with col2:
    st.metric(label="Watchlist Matches", value=watchlist_match)

with col3:
    st.metric(label="Uncommon Matches", value=uncommon_match)

with col4:
    st.metric(label="Last Updated", value=last_updated)

st.markdown("---")

main_col, sidebar_col = st.columns([3, 1])

with main_col:
    st.subheader("📋 Aircraft Log")

    # Search & Filter Controls
    search_query = st.text_input("🔍 Search by Callsign, Registration, or Hex", "").strip().upper()
    watchlist_only = st.checkbox("Show Watchlist Matches Only")

    # Apply Filters
    filtered_df = df_aircraft.copy()

    if not filtered_df.empty:
        if watchlist_only:
            filtered_df = filtered_df[filtered_df["Watchlist Match"] == True]
            
        if search_query:
            filtered_df = filtered_df[
                filtered_df["Callsign"].str.contains(search_query, na=False) |
                filtered_df["Registration"].str.contains(search_query, na=False) |
                filtered_df["ICAO Hex"].str.contains(search_query.lower(), na=False)
            ]

        # Display Interactive Data Table
        st.dataframe(
            filtered_df,
            column_config={
                "ICAO Hex": st.column_config.LinkColumn(
                    "ADS-B Radar",
                    help="Open aircraft on ADS-B Exchange",
                    validate="^https://.*",
                    display_text=r"https://globe\.adsbexchange\.com/\?icao=(.*)"
                ),
                "Watchlist Match": st.column_config.CheckboxColumn(
                    "Watchlist",
                    help="Is this target on your watchlist?"
                )
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No aircraft logs found in `nexus.db` yet.")

with sidebar_col:
    st.subheader("⚙️ Watchlist Controls")
    
    current_watchlist = load_watchlist()
    
    with st.expander("View / Edit Watchlist JSON", expanded=True):
        updated_json_str = st.text_area(
            "JSON Data",
            value=json.dumps(current_watchlist, indent=2),
            height=250
        )
        
        if st.button("Save Watchlist"):
            try:
                parsed_json = json.loads(updated_json_str)
                save_watchlist(parsed_json)
                st.success("Watchlist saved successfully!")
                time.sleep(1)
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {e}")

    if st.button("🔄 Refresh Data"):
        st.rerun()