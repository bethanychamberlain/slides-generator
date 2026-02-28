"""Azure Entra ID authentication for Streamlit via MSAL."""

import os

import msal
import streamlit as st


def _get_auth_config():
    """Read auth configuration from environment variables."""
    client_id = os.environ.get("AZURE_CLIENT_ID", "")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
    tenant_id = os.environ.get("AZURE_TENANT_ID", "")
    redirect_uri = os.environ.get("AZURE_REDIRECT_URI", "http://localhost:8501")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "redirect_uri": redirect_uri,
        "scope": ["User.Read"],
    }


def _get_msal_app(config):
    """Create an MSAL confidential client application."""
    return msal.ConfidentialClientApplication(
        config["client_id"],
        authority=config["authority"],
        client_credential=config["client_secret"],
    )


def require_login():
    """Enforce Microsoft SSO login. Returns user info dict or calls st.stop().

    Returns:
        dict with keys: name, email
    """
    # Already authenticated this session
    if st.session_state.get("user"):
        return st.session_state["user"]

    config = _get_auth_config()

    # If no Entra ID config, fall back to simple mode (local dev)
    if not config["client_id"]:
        return _dev_fallback()

    app = _get_msal_app(config)
    query_params = st.query_params

    # Step 2: Handle redirect back from Microsoft
    if "code" in query_params:
        code = query_params["code"]
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=config["scope"],
            redirect_uri=config["redirect_uri"],
        )
        if "id_token_claims" in result:
            claims = result["id_token_claims"]
            user = {
                "name": claims.get("name", "Unknown"),
                "email": claims.get("preferred_username", claims.get("email", "unknown")),
            }
            st.session_state["user"] = user
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
            st.stop()

    # Step 1: Redirect to Microsoft login
    auth_url = app.get_authorization_request_url(
        scopes=config["scope"],
        redirect_uri=config["redirect_uri"],
    )
    st.markdown("### Welcome to Slide Guide Generator")
    st.markdown("Sign in with your university Microsoft account to get started.")
    st.link_button("Sign in with Microsoft", auth_url, type="primary")
    st.stop()


def _dev_fallback():
    """Name + optional API key entry for local development without Entra ID."""
    if st.session_state.get("user"):
        return st.session_state["user"]

    st.markdown("### Development Mode")
    st.caption("No Azure Entra ID configured. Enter your name to continue.")
    name = st.text_input("Your name", key="dev_name")

    # Allow manual API key entry if no ANTHROPIC_API_KEY in environment
    api_key_from_env = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key_from_env:
        st.caption("Using API key from environment variable.")
        api_key = ""
    else:
        st.caption("No `ANTHROPIC_API_KEY` environment variable found.")
        api_key = st.text_input("Anthropic API Key", type="password",
                                placeholder="sk-ant-...", key="dev_api_key")

    if st.button("Continue") and name.strip():
        if not api_key_from_env and not api_key.strip():
            st.error("Please set ANTHROPIC_API_KEY in your environment or enter a key above.")
            st.stop()
        user = {
            "name": name.strip(),
            "email": f"{name.strip().lower()}@dev.local",
            "api_key": api_key.strip() or None,
        }
        st.session_state["user"] = user
        st.rerun()
    st.stop()


def logout():
    """Clear session and show logged-out state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
