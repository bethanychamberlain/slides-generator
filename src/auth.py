"""Azure Entra ID authentication for Streamlit via MSAL."""

import base64
import json
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


def _check_easy_auth():
    """Check for Azure Easy Auth headers (platform-level SSO)."""
    headers = st.context.headers
    principal_name = headers.get("X-Ms-Client-Principal-Name")
    if not principal_name:
        return None

    # Try to get display name from the base64-encoded claims principal
    display_name = principal_name.split("@")[0]
    principal_b64 = headers.get("X-Ms-Client-Principal")
    if principal_b64:
        try:
            claims = json.loads(base64.b64decode(principal_b64))
            for claim in claims.get("claims", []):
                if claim.get("typ") == "name":
                    display_name = claim["val"]
                    break
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    return {"name": display_name, "email": principal_name}


def require_login():
    """Require login. Returns dict with name, email — or calls st.stop().

    Checks: session cache → Easy Auth → MSAL → dev fallback.
    """
    # Already authenticated this session
    if st.session_state.get("user"):
        return st.session_state["user"]

    # Platform-level SSO (Azure Easy Auth)
    easy_auth_user = _check_easy_auth()
    if easy_auth_user:
        st.session_state["user"] = easy_auth_user
        return easy_auth_user

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
    """Dev mode: name + optional API key entry."""
    if st.session_state.get("user"):
        return st.session_state["user"]

    st.markdown("### Development Mode")
    st.caption("No Azure Entra ID configured. Enter your name to continue.")
    name = st.text_input("Your name", key="dev_name")

    # Show key fields only for providers missing an env var
    api_keys = {}
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    has_mistral = bool(os.environ.get("MISTRAL_API_KEY", ""))

    if has_anthropic and has_mistral:
        st.caption("Using API keys from environment variables.")
    else:
        if not has_anthropic:
            api_keys["anthropic"] = st.text_input(
                "Anthropic API Key (optional)",
                type="password", placeholder="sk-ant-...", key="dev_key_anthropic",
            )
        if not has_mistral:
            api_keys["mistral"] = st.text_input(
                "Mistral API Key (optional)",
                type="password", placeholder="Paste Mistral key...", key="dev_key_mistral",
            )
        if has_anthropic or has_mistral:
            env_providers = [p for p, v in [("Anthropic", has_anthropic), ("Mistral", has_mistral)] if v]
            st.caption(f"Using {', '.join(env_providers)} key from environment.")

    if st.button("Continue") and name.strip():
        # Need at least one key (from env or manual entry)
        manual_keys = {k: v.strip() for k, v in api_keys.items() if v.strip()}
        if not has_anthropic and not has_mistral and not manual_keys:
            st.error("Enter at least one API key, or set ANTHROPIC_API_KEY / MISTRAL_API_KEY in your environment.")
            st.stop()
        user = {
            "name": name.strip(),
            "email": f"{name.strip().lower()}@dev.local",
            "api_keys": manual_keys or None,
        }
        st.session_state["user"] = user
        st.rerun()
    st.stop()


def logout():
    """Clear session state and rerun."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
