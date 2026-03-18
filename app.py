import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Biochemistry Freezer Log", layout="wide")
st.title(" Freezer Manager")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_logs():
    expected_cols = [
        "Timestamp", "User", "Email", "Phone", "Guide_Name", 
        "Freezer_Type", "Unit_Name", "Rack_Name", "Box_ID", "Count", "Photo_Path"
    ]
    try:
        # ttl=0 ensures we bypass any cache and get real data
        data = conn.read(ttl=0)
        if data is None or data.empty or 'User' not in data.columns:
            return pd.DataFrame(columns=expected_cols)
        data.columns = data.columns.str.strip()
        return data
    except Exception:
        return pd.DataFrame(columns=expected_cols)

# --- USER AUTH (GitHub File) ---
def load_users():
    try:
        return pd.read_excel("users.xlsx", dtype={'last_date': str})
    except Exception:
        return pd.DataFrame(columns=["userid", "password", "last_date"])

user_df = load_users()
USER_REGISTRY = dict(zip(user_df['userid'].astype(str), user_df['password'].astype(str)))

# --- SIDEBAR ---
user_name = st.sidebar.selectbox("Select User", list(USER_REGISTRY.keys()))
passcode = st.sidebar.text_input("Enter Passcode", type="password")

if passcode == USER_REGISTRY.get(user_name):
    st.sidebar.success(f"Verified: {user_name}")
    
    tab1, tab2 = st.tabs(["📥 New Entry", "📋 Records"])

    with tab1:
        with st.form("entry_form", clear_on_submit=True):
            f_type = st.selectbox("Freezer", ["-80 Freezer", "-20 Freezer"])
            b_id = st.text_input("Box ID")
            count = st.number_input("Count", min_value=0)
            submit = st.form_submit_button("Save to Cloud")

        if submit:
            if not b_id:
                st.error("Box ID required.")
            else:
                try:
                    # 1. Get existing data
                    current_df = load_live_logs()
                    
                    # 2. Add new row
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "User": user_name, "Freezer_Type": f_type,
                        "Box_ID": b_id, "Count": count, "Photo_Path": "Pending"
                    }])
                    
                    updated_df = pd.concat([current_df, new_row], ignore_index=True)
                    
                    # 3. FORCE UPDATE: We tell it explicitly to use the worksheet
                    # If your tab is named "Sheet1", change worksheet="Sheet1"
                    # Otherwise, leaving it blank usually defaults to the first tab
                    conn.update(data=updated_df)
                    
                    st.success("Successfully saved to Google Sheets!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save Failed: {e}")
                    st.info("Try this: Rename the tab in your Google Sheet to 'Sheet1' and try again.")

    with tab2:
        all_logs = load_live_logs()
        st.dataframe(all_logs, use_container_width=True)

else:
    st.info("Log in to continue.")