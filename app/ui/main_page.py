import pandas as pd
import streamlit as st

from app.flexline.client import FlexlineError
from app.flexline.utils import generate_count_query

def main_page(text2sql_client, flexline_client):
    """Renders the main application page for generating and executing SQL queries."""
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

    if st.session_state.ai_response:
        st.divider()
        st.header("Step 2: Review and Execute Query")

        response_data = st.session_state.ai_response
        sql_query = response_data.get("sql_query")
        explanation = response_data.get("explanation")

        st.info(f"**Explanation:** {explanation}")
        st.code(sql_query, language="sql")
        st.success(
            "✅ The generated query is flagged as **read-only** and is safe to run."
        )

        if st.button("Run Query and Get Results", type="primary"):
            MAX_RECORDS = 10000

            with st.spinner("Checking query size... ⚙️"):
                try:
                    final_count_query = generate_count_query(sql_query)
                    count_results = flexline_client.run(final_count_query)

                    record_count = 0
                    if (
                        count_results
                        and isinstance(count_results, list)
                        and count_results[0]
                    ):
                        record_count = count_results[0].get("total_rows", 0)

                    if record_count > MAX_RECORDS:
                        st.warning(
                            f"This query will return approximately {record_count:,} records, which is too large to display directly. Please make your question more specific to narrow down the results."
                        )
                        st.session_state.results_df = None
                    else:
                        st.info(
                            f"Query will return {record_count:,} records. Fetching data..."
                        )
                        with st.spinner("Executing query... ⚙️"):
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
