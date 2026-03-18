import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Biochemistry Freezer Log", layout="wide")
st.title("Freezer storage manager")

# --- DATA CONNECTIONS ---

# Initialize the secure connection
# This automatically uses the credentials and URL from your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_logs():
    try:
        # SECURE READ: No URL needed here, it pulls from Secrets
        return conn.read()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame(columns=[
            "Timestamp", "User", "Email", "Phone", "Guide_Name", 
            "Freezer_Type", "Unit_Name", "Rack_Name", "Box_ID", "Count", "Photo_Path"
        ])

def load_users():
    try:
        # Pulls user list from your GitHub Excel file
        return pd.read_excel("users.xlsx", dtype={'last_date': str})
    except Exception:
        st.error("Authentication file (users.xlsx) not found on GitHub.")
        return pd.DataFrame(columns=["userid", "password", "last_date"])

# Load data at startup
user_df = load_users()
USER_REGISTRY = dict(zip(user_df['userid'].astype(str), user_df['password'].astype(str)))

# --- SIDEBAR LOGIN ---
st.sidebar.header("Authentication")
user_name = st.sidebar.selectbox("Select User", list(USER_REGISTRY.keys()))
passcode = st.sidebar.text_input("Enter Passcode", type="password")

if passcode == USER_REGISTRY.get(user_name):
    st.sidebar.success(f"Verified: {user_name}")
    
    # --- STORAGE PERIOD COUNTDOWN ---
    user_info = user_df[user_df['userid'].astype(str) == user_name].iloc[0]
    if 'last_date' in user_info and pd.notnull(user_info['last_date']):
        last_date_str = str(user_info['last_date']).strip()
        expiry_date = None
        for fmt in ["%d-%m-%Y", "%d/%m/%Y"]:
            try:
                expiry_date = datetime.strptime(last_date_str, fmt)
                break
            except ValueError: continue

        if expiry_date:
            days_left = (expiry_date - datetime.now()).days
            st.sidebar.metric(label="Days Remaining", value=f"{days_left} Days")
            if days_left <= 0:
                st.sidebar.error("⚠️ Storage Expired!")

    # --- MAIN TABS ---
    tab1, tab2 = st.tabs(["📥 Log New Entry", "📋 My Records"])

    with tab1:
        st.subheader("Add New Sample Data")
        
        col1, col2 = st.columns(2)
        freezer_type = col1.selectbox("Select Freezer", ["-80 Freezer", "-20 Freezer"])
        unit_options = ["(-80)PhCBI", "(-80)Panasonic"] if freezer_type == "-80 Freezer" else ["(-20)Old", "(-20)New"]
        unit_name = col2.selectbox("Select Unit", unit_options)
        
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            user_email = c1.text_input("Email Address")
            user_phone = c2.text_input("Phone Number")
            
            g_col, r_col = st.columns(2)
            guide_name = g_col.text_input("Guide Name")
            rack_name = r_col.text_input("Rack Name/No")
            
            b_col, c_col = st.columns(2)
            box_id = b_col.text_input("Box ID")
            count = c_col.number_input("Count (Boxes/Vials)", min_value=0)
            
            submit = st.form_submit_button("Save to Cloud")

        if submit:
            if not user_email or not user_phone or not box_id:
                st.error("Please fill in Email, Phone, and Box ID.")
            else:
                # 1. Fetch current data securely
                current_df = load_live_logs()
                
                # 2. Create the new row
                new_entry = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "User": user_name,
                    "Email": user_email,
                    "Phone": user_phone,
                    "Guide_Name": guide_name,
                    "Freezer_Type": freezer_type,
                    "Unit_Name": unit_name,
                    "Rack_Name": rack_name,
                    "Box_ID": box_id,
                    "Count": count,
                    "Photo_Path": "Pending"
                }])
                
                # 3. Combine and Push to Cloud
                updated_df = pd.concat([current_df, new_entry], ignore_index=True)
                
                # SECURE UPDATE: Uses credentials from Secrets to write
                conn.update(data=updated_df) 
                
                st.success("Log saved permanently to Google Sheets!")
                st.rerun()

    with tab2:
        # Fresh pull from Google Sheets to show history
        all_logs = load_live_logs()
        if user_name.lower() == "admin":
            st.subheader("Master Lab Log")
            st.dataframe(all_logs, use_container_width=True)
        else:
            st.subheader(f"Log History for {user_name}")
            user_records = all_logs[all_logs['User'].astype(str) == user_name]
            st.dataframe(user_records, use_container_width=True)

else:
    st.info("Please select your name and enter your passcode in the sidebar.")