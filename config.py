import os

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def setting(name, default=""):
    """Read a local environment value or a hosted Streamlit secret."""
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        # st.secrets raises when no secrets file/configuration is present.
        return default
