import streamlit as st
import toml

from app.flexline.client import FlexlineClient
from app.text2sql.client import Text2SQLClient
from app.ui.authentication import check_password
from app.ui.main_page import main_page
from app.ui.results import display_results


from app.ui.utils import format_timestamp


def get_project_version():
    try:
        with open("pyproject.toml", "r") as f:
            pyproject_data = toml.load(f)
        return pyproject_data["project"]["version"]
    except (FileNotFoundError, KeyError):
        return "unknown"


st.set_page_config(
    page_title="Client Query App",
    page_icon="🤖",
    layout="wide",
)

if not check_password():
    st.stop()


def init_clients():
    """Initializes and returns both Text2SQL and Flexline clients."""
    try:
        text2sql_client = Text2SQLClient(
            base_url=st.secrets.saas_api.base_url,
            workspace_id=st.secrets.saas_api.workspace_id,
        )
        flexline_client = FlexlineClient(
            aws_access_key_id=st.secrets.flexline_lambda.aws_access_key_id,
            aws_secret_access_key=st.secrets.flexline_lambda.aws_secret_access_key,
            api_key=st.secrets.flexline_lambda.api_key,
            username=st.secrets.flexline_lambda.username,
            password=st.secrets.flexline_lambda.password,
        )
        return text2sql_client, flexline_client
    except (AttributeError, KeyError) as e:
        st.error(
            f"🚨 Critical Error: Secrets are not configured correctly. Missing key: {e}"
        )
        st.stop()


text2sql_client, flexline_client = init_clients()


def authenticate_with_backend(_client):
    """Authenticates the client with the backend API."""
    return _client.authenticate(
        username=st.secrets.saas_api.username, password=st.secrets.saas_api.password
    )


if not authenticate_with_backend(text2sql_client):
    st.error("Backend authentication failed. Please check API credentials and status.")
    st.stop()

APP_VERSION = get_project_version()

if "workspace_details" not in st.session_state or st.session_state.workspace_details is None:
    st.session_state.workspace_details = text2sql_client.get_workspace_details()

# Ensure workspace_details is always a dictionary, even if the API call failed
workspace_details = st.session_state.workspace_details if st.session_state.workspace_details is not None else {}
workspace_name = workspace_details.get("name", "Unknown")
updated_at = format_timestamp(workspace_details.get("updated_at"))

st.title(f"Natural Language to SQL Query (v{APP_VERSION})")
st.markdown(f"**Workspace:** {workspace_name} (`{st.secrets.saas_api.workspace_id}`)")
st.caption(f"Last updated: {updated_at}")

if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "results_df" not in st.session_state:
    st.session_state.results_df = None

main_page(text2sql_client, flexline_client)
display_results()