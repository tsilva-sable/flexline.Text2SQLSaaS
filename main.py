import io
import re

import pandas as pd
import streamlit as st

from app.flexline.client import FlexlineClient, FlexlineError
from app.text2sql.client import Text2SQLClient

# --- Page Configuration ---
st.set_page_config(
    page_title="Client Query App",
    page_icon="🤖",
    layout="wide",
)


# --- App Authentication Gate ---
def check_password():
    """Returns `True` if the user has the correct password."""
    with st.form("Credentials"):
        st.title("Welcome")
        st.markdown("Please enter the API key to use this application.")
        user_key = st.text_input("API Key", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if user_key == st.secrets.streamlit_app.api_key:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.session_state["password_correct"] = False
            st.error("😕 The provided API key is incorrect.")


if not st.session_state.get("password_correct", False):
    check_password()
    st.stop()


# --- Initialize Both Clients ---
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


# --- Authenticate with Backend API ---
def authenticate_with_backend(_client):
    """Authenticates the client with the backend API."""
    return _client.authenticate(
        username=st.secrets.saas_api.username, password=st.secrets.saas_api.password
    )


if not authenticate_with_backend(text2sql_client):
    st.error("Backend authentication failed. Please check API credentials and status.")
    st.stop()

# --- Main App UI ---
st.title("Natural Language to SQL Query")
st.markdown(f"**Workspace:** `{st.secrets.saas_api.workspace_id}`")

# --- Initialize Session State ---
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "results_df" not in st.session_state:
    st.session_state.results_df = None

# --- Step 1: Generate SQL (Now in a Form) ---
st.header("Step 1: Generate SQL from a Question")

with st.form(key="sql_generation_form"):
    question = st.text_area(
        "Enter your question:",
        placeholder="e.g., What are the top 5 best-selling products in the last year?",
        height=100,
        key="question_input",
    )
    generate_button = st.form_submit_button(
        label="Generate SQL Query", type="primary", use_container_width=True
    )

if generate_button and question:
    st.session_state.results_df = None  # Clear previous results
    with st.spinner("Asking the AI... 🧠"):
        response = text2sql_client.get_sql(question)
        st.session_state.ai_response = response or None
        if not response:
            st.error(
                "Failed to get a valid response from the AI. The query might not be read-only or the API may be down."
            )

# --- Step 2: Review and Execute ---
if st.session_state.ai_response:
    st.divider()
    st.header("Step 2: Review and Execute Query")

    response_data = st.session_state.ai_response
    sql_query = response_data.get("sql_query")
    explanation = response_data.get("explanation")

    st.info(f"**Explanation:** {explanation}")
    st.code(sql_query, language="sql")
    st.success("✅ The generated query is flagged as **read-only** and is safe to run.")

    if st.button("Run Query and Get Results", type="primary"):
        # Set a threshold for the maximum number of records
        MAX_RECORDS = 20000

        with st.spinner("Checking query size... ⚙️"):
            try:
                # --- Improved Logic for Creating the Count Query ---
                original_query = str(sql_query).strip()
                query_for_count = original_query

                # First, strip any trailing ORDER BY, LIMIT, or OFFSET clauses
                query_for_count = re.sub(
                    r"\s+(ORDER\s+BY|LIMIT|OFFSET)\s+.*$",
                    "",
                    query_for_count,
                    flags=re.IGNORECASE | re.DOTALL,
                ).strip()

                # Now, handle the WITH clause (CTE) case
                if query_for_count.upper().startswith("WITH"):
                    # If it's a CTE, we don't wrap it. Instead, we replace the final SELECT.
                    last_select_pos = query_for_count.upper().rfind("SELECT")

                    # Ensure we are not grabbing a SELECT from a subquery within the CTE
                    from_after_last_select_pos = query_for_count.upper().find(
                        "FROM", last_select_pos
                    )

                    if last_select_pos != -1 and from_after_last_select_pos != -1:
                        # Replace the column list of the final SELECT with COUNT(*)
                        count_select_clause = "SELECT COUNT(*) "
                        query_for_count = (
                            query_for_count[:last_select_pos]
                            + count_select_clause
                            + query_for_count[from_after_last_select_pos:]
                        )
                else:
                    # If it's not a CTE, the safe approach is to wrap it
                    query_for_count = f"SELECT COUNT(*) as record_count FROM ({query_for_count}) as subquery"

                # 1. Execute the count query
                count_results = flexline_client.run(query_for_count)

                record_count = 0
                # Extract the count from the result
                if (
                    count_results
                    and isinstance(count_results, list)
                    and count_results[0]
                ):
                    record_count = list(count_results[0].values())[0]

                # 2. Check if the record count exceeds the threshold
                if record_count > MAX_RECORDS:
                    st.warning(
                        f"This query will return approximately {record_count:,} records, which is too large to display directly. Please make your question more specific to narrow down the results."
                    )
                    st.session_state.results_df = None

                else:
                    # 3. If the count is acceptable, run the original query
                    st.info(
                        f"Query will return {record_count:,} records. Fetching data..."
                    )
                    with st.spinner("Executing query... ⚙️"):
                        # Use the original sql_query here, which still has the ORDER BY
                        results = flexline_client.run(sql_query)
                        st.success("✅ Query executed successfully!")

                        if isinstance(results, list) and results:
                            st.session_state.results_df = pd.DataFrame(results)
                        elif isinstance(results, dict):
                            st.session_state.results_df = pd.DataFrame([results])
                        else:
                            st.warning(
                                "The query executed, but the data was empty or not in a table format."
                            )
                            st.write("Raw output:", results)
                            st.session_state.results_df = None

            except FlexlineError as e:
                st.error(f"Lambda Execution Failed: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

# --- Step 3: Display and Export Results ---
if st.session_state.results_df is not None:
    st.divider()
    st.header("Step 3: Results")

    # Display the formatted DataFrame
    formatted_df = st.session_state.results_df.copy()
    for col in formatted_df.columns:
        if pd.api.types.is_numeric_dtype(formatted_df[col]):
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,}")
    st.dataframe(formatted_df, hide_index=True)

    # --- Excel Export Functionality ---
    # Create an in-memory buffer
    buffer = io.BytesIO()

    # Write the original, unformatted dataframe to the buffer as an Excel file
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        st.session_state.results_df.to_excel(writer, index=False, sheet_name="Results")

    st.download_button(
        label="📄 Export to Excel",
        data=buffer,
        file_name="query_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # You could even offer both options
    # --- CSV Export Functionality (optional) ---
    csv_data = st.session_state.results_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Export to CSV",
        data=csv_data,
        file_name="query_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
