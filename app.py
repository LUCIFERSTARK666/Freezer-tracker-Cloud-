import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURATION ---
# The app will now pull the URL and the Key from your Streamlit Secrets
st.set_page_config(page_title="Biochemistry Freezer Log", layout="wide")
st.title("Freezer storage manager")

# --- DATA CONNECTIONS ---

# Initialize the secure connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_logs():
    try:
        # SECURE READ: Uses the Service Account from Secrets
        return conn.read()
    except Exception:
        return pd.DataFrame(columns=[
            "Timestamp", "User", "Email", "Phone", "Guide_Name", 
            "Freezer_Type", "Unit_Name", "Rack_Name", "Box_ID", "Count", "Photo_Path"
        ])

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
    
    # Storage Countdown Logic (Remains the same)
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
            email = c1.text_input("Email")
            phone = c2.text_input("Phone Number")
            g_name = st.text_input("Guide Name")
            r_name = st.text_input("Rack Name/No")
            b_id = st.text_input("Box ID")
            count = st.number_input("Count", min_value=0)
            submit = st.form_submit_button("Save to Cloud")

        if submit:
            if not email or not phone or not b_id:
                st.error("Email, Phone, and Box ID are required.")
            else:
                # Prepare the new entry
                new_entry = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "User": user_name, "Email": email, "Phone": phone,
                    "Guide_Name": g_name, "Freezer_Type": f_type,
                    "Unit_Name": u_name, "Rack_Name": r_name,
                    "Box_ID": b_id, "Count": count, "Photo_Path": "Pending"
                }])
                
                # SECURE UPDATE: Appends the data to your Google Sheet
                current_df = load_live_logs()
                updated_df = pd.concat([current_df, new_entry], ignore_index=True)
                
                # Using the connection to push data back to the cloud
                conn.update(data=updated_df)
                
                st.success("Record safely synced to Google Sheets!")
                st.rerun()

    with tab2:
        # Load logs from the secure connection
        all_logs = load_live_logs()
        if user_name.lower() == "admin":
            st.subheader("Master Lab Log")
            st.dataframe(all_logs)
        else:
            st.subheader(f"Log History for {user_name}")
            st.dataframe(all_logs[all_logs['User'] == user_name])
else:
    st.info("Log in via sidebar to proceed.")