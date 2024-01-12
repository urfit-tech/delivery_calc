import streamlit as st

from pages import login_page, main_page

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Page routing
if st.session_state["authenticated"]:
    main_page()  # Display main page after successful login
else:
    login_page()  # Display login page if not authenticated
