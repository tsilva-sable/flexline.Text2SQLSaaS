import io

import pandas as pd
import streamlit as st

def display_results():
    """Displays the results dataframe and provides export options."""
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
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state.results_df.to_excel(
                writer, index=False, sheet_name="Results"
            )

        st.download_button(
            label="📄 Export to Excel",
            data=buffer,
            file_name="query_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # --- CSV Export Functionality (optional) ---
        csv_data = st.session_state.results_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Export to CSV",
            data=csv_data,
            file_name="query_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
