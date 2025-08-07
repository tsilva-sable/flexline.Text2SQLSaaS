import streamlit as st
from streamlit_browser_storage import LocalStorage

def check_password():
    """Returns `True` if the user has the correct password or a valid session token."""
    if st.session_state.get("password_correct", False):
        return True

    local_storage = LocalStorage(key="session_storage")

    # Check for a session token in local storage
    session_token = local_storage.get("session_token")
    if session_token and session_token == st.secrets.streamlit_app.api_key:
        st.session_state["password_correct"] = True
        st.rerun()

    with st.form("Credentials"):
        st.title("Welcome")
        st.markdown("Please enter the API key to use this application.")
        user_key = st.text_input("API Key", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if user_key == st.secrets.streamlit_app.api_key:
            st.session_state["password_correct"] = True
            # Store the session token in local storage
            local_storage.set("session_token", user_key)
            st.rerun()  # Rerun to clear the form and display the app
        else:
            st.session_state["password_correct"] = False
            st.error("😕 The provided API key is incorrect.")

    return False
