import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Biochemistry Freezer Log", layout="wide")
st.title("Biochemistry Freezer Management")

# --- 2. DATA CONNECTION ---
# This pulls everything from your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_logs():
    expected_cols = [
        "Timestamp", "User", "Email", "Phone", "Guide_Name", 
        "Freezer_Type", "Unit_Name", "Rack_Name", "Box_ID", "Count", "Photo_Path"
    ]
    try:
        # ttl=0 ensures we don't see old cached data
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=expected_cols)
        
        # Clean up column names to avoid KeyErrors
        data.columns = data.columns.str.strip()
        
        # If 'User' column is missing because the sheet is new/blank
        if 'User' not in data.columns:
            return pd.DataFrame(columns=expected_cols)
            
        return data
    except Exception:
        return pd.DataFrame(columns=expected_cols)

# --- 3. LOAD USER LIST (From GitHub) ---
def load_users():
    try:
        return pd.read_excel("users.xlsx", dtype={'last_date': str})
    except Exception:
        st.error("Error: 'users.xlsx' not found in your GitHub repository.")
        return pd.DataFrame(columns=["userid", "password", "last_date"])

user_df = load_users()
USER_REGISTRY = dict(zip(user_df['userid'].astype(str), user_df['password'].astype(str)))

# --- 4. SIDEBAR AUTHENTICATION ---
st.sidebar.header("Lab Login")
user_name = st.sidebar.selectbox("Select Your Name", list(USER_REGISTRY.keys()))
passcode = st.sidebar.text_input("Enter Passcode", type="password")

# --- 5. MAIN APPLICATION LOGIC ---
if passcode == USER_REGISTRY.get(user_name):
    st.sidebar.success(f"Logged in: {user_name}")
    
    # Expiry Countdown
    user_info = user_df[user_df['userid'].astype(str) == user_name].iloc[0]
    if 'last_date' in user_info and pd.notnull(user_info['last_date']):
        try:
            expiry_date = datetime.strptime(str(user_info['last_date']).strip(), "%d-%m-%Y")
            days_left = (expiry_date - datetime.now()).days
            st.sidebar.metric("Days Remaining", f"{days_left} Days")
        except: pass

    tab1, tab2 = st.tabs(["📥 Log New Entry", "📋 View Records"])

    with tab1:
        st.subheader("Freezer Entry Form")
        with st.form("main_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_type = col1.selectbox("Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_name = col2.selectbox("Unit Name", 
                        ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["Old", "New"])
            
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            g_name = st.text_input("Guide Name")
            r_name = st.text_input("Rack No/Name")
            b_id = st.text_input("Box ID (Required)")
            count = st.number_input("Sample Count", min_value=0, step=1)
            
            submit = st.form_submit_button("Save to Cloud")

        if submit:
            if not b_id:
                st.error("You must enter a Box ID.")
            else:
                try:
                    # Load current data
                    current_df = load_live_logs()
                    
                    # Create new row
                    new_entry = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "User": user_name, "Email": email, "Phone": phone,
                        "Guide_Name": g_name, "Freezer_Type": f_type,
                        "Unit_Name": u_name, "Rack_Name": r_name,
                        "Box_ID": b_id, "Count": count, "Photo_Path": "Pending"
                    }])
                    
                    # Combine and update
                    updated_df = pd.concat([current_df, new_entry], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success("Data successfully synced to Google Sheets!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Save Failed: {e}")

    with tab2:
        st.subheader("Lab Sample Inventory")
        all_data = load_live_logs()
        if user_name.lower() == "admin":
            st.dataframe(all_data, use_container_width=True)
        else:
            # Show only the user's records
            my_data = all_data[all_data['User'] == user_name]
            st.dataframe(my_data, use_container_width=True)

else:
    st.info("Please verify your passcode in the sidebar to enter data.")