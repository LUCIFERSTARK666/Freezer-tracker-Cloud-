import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Biochemistry Freezer Log", layout="wide")
st.title("Freezer Manager")

# --- DATA CONNECTIONS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_logs():
    # Define the required columns for your research database
    expected_cols = [
        "Timestamp", "User", "Email", "Phone", "Guide_Name", 
        "Freezer_Type", "Unit_Name", "Rack_Name", "Box_ID", "Count", "Photo_Path"
    ]
    try:
        # ttl=0 ensures it doesn't show old cached data
        data = conn.read(ttl=0)
        
        # If the sheet is totally empty or missing headers, create a fresh DataFrame
        if data is None or data.empty or 'User' not in data.columns:
            return pd.DataFrame(columns=expected_cols)
            
        # Remove accidental spaces from headers
        data.columns = data.columns.str.strip()
        return data
    except Exception:
        # If the connection fails entirely, return the empty structure
        return pd.DataFrame(columns=expected_cols)

def load_users():
    try:
        return pd.read_excel("users.xlsx", dtype={'last_date': str})
    except Exception:
        st.error("Authentication file (users.xlsx) not found on GitHub.")
        return pd.DataFrame(columns=["userid", "password", "last_date"])

user_df = load_users()
USER_REGISTRY = dict(zip(user_df['userid'].astype(str), user_df['password'].astype(str)))

# --- SIDEBAR LOGIN ---
st.sidebar.header("Authentication")
user_name = st.sidebar.selectbox("Select User", list(USER_REGISTRY.keys()))
passcode = st.sidebar.text_input("Enter Passcode", type="password")

if passcode == USER_REGISTRY.get(user_name):
    st.sidebar.success(f"Verified: {user_name}")
    
    # Storage Countdown
    user_info = user_df[user_df['userid'].astype(str) == user_name].iloc[0]
    if 'last_date' in user_info and pd.notnull(user_info['last_date']):
        last_date_str = str(user_info['last_date']).strip()
        expiry_date = None
        for fmt in ["%d-%m-%Y", "%d/%m/%Y"]:
            try:
                expiry_date = datetime.strptime(last_date_str, fmt)
                break
            except: continue
        if expiry_date:
            days_left = (expiry_date - datetime.now()).days
            st.sidebar.metric("Days Remaining", f"{days_left} Days")

    tab1, tab2 = st.tabs(["📥 Log New Entry", "📋 My Records"])

    with tab1:
        st.subheader("Add New Sample Data")
        col1, col2 = st.columns(2)
        f_type = col1.selectbox("Select Freezer", ["-80 Freezer", "-20 Freezer"])
        u_opts = ["(-80)PhCBI", "(-80)Panasonic"] if f_type == "-80 Freezer" else ["(-20)Old", "(-20)New"]
        u_name = col2.selectbox("Select Unit", u_opts)
        
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            u_email = c1.text_input("Email")
            u_phone = c2.text_input("Phone Number")
            g_name = st.text_input("Guide Name")
            r_name = st.text_input("Rack Name/No")
            b_id = st.text_input("Box ID")
            count = st.number_input("Count", min_value=0)
            submit = st.form_submit_button("Save to Cloud")

        if submit:
            if not b_id:
                st.error("Box ID is required to save.")
            else:
                # 1. Fetch current data
                current_df = load_live_logs()
                
                # 2. Create the new row
                new_entry = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "User": user_name, "Email": u_email, "Phone": u_phone,
                    "Guide_Name": g_name, "Freezer_Type": f_type,
                    "Unit_Name": u_name, "Rack_Name": r_name,
                    "Box_ID": b_id, "Count": count, "Photo_Path": "Pending"
                }])
                
                # 3. Combine and Push
                updated_df = pd.concat([current_df, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Record safely saved to Google Sheets!")
                st.rerun()

    with tab2:
        all_logs = load_live_logs()
        if all_logs.empty:
            st.info("No records found in the database yet.")
        else:
            if user_name.lower() == "admin":
                st.dataframe(all_logs, use_container_width=True)
            else:
                # Safe filtering: Check if 'User' column exists before filtering
                if 'User' in all_logs.columns:
                    user_records = all_logs[all_logs['User'].astype(str) == user_name]
                    st.dataframe(user_records, use_container_width=True)
                else:
                    st.dataframe(all_logs)

else:
    st.info("Please log in via the sidebar.")