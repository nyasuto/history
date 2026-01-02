import altair as alt
import pandas as pd
import streamlit as st

from src import config, db, etl

st.set_page_config(page_title="Safari History Analytics", page_icon="🧭", layout="wide")

# Initialize Session State
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False


@st.cache_data(ttl=600)
def load_data(ignore_set=None):
    """Loads and processes data from Safari History DB."""
    try:
        conn = db.get_connection()
        raw_df = db.fetch_history_data(conn)
        conn.close()
        df = etl.process_history_df(raw_df, ignore_set)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info(
            "Ensure the terminal has 'Full Disk Access' in macOS System Settings to read Safari History."
        )
        return pd.DataFrame()


def main():
    st.title("🧭 Safari History Analytics")

    # Load Ignore List
    ignore_set = config.load_ignore_list()

    with st.sidebar:
        st.header("Filters")
        if st.button("Reload Data"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.header("Ignore List")

        # Add Domain
        new_domain = st.text_input("Add Domain to Ignore").strip()
        if st.button("Add"):
            if new_domain:
                config.add_domain(new_domain)
                st.cache_data.clear()
                st.rerun()

        # Remove Domain
        if ignore_set:
            domain_to_remove = st.selectbox("Remove Domain", sorted(list(ignore_set)))
            if st.button("Remove"):
                config.remove_domain(domain_to_remove)
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("No domains in ignore list.")

    # Load Data
    df = load_data(ignore_set)

    if df.empty:
        st.warning("No data found or permission denied.")
        return

    # Sidebar Filter Logic
    min_date = df["date"].min()
    max_date = df["date"].max()

    date_range = st.sidebar.date_input(
        "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )

    # Filter DataFrame
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df

    # --- KPI Section ---
    st.subheader("Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Visits", len(filtered_df))
    col2.metric("Unique Domains", filtered_df["domain"].nunique())
    col3.metric("Days Active", filtered_df["date"].nunique())

    # --- Charts ---
    st.divider()
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Top Domains")
        domain_counts = filtered_df["domain"].value_counts().head(10).reset_index()
        domain_counts.columns = ["domain", "count"]

        chart = (
            alt.Chart(domain_counts)
            .mark_bar()
            .encode(
                x=alt.X("count", title="Visits"),
                y=alt.Y("domain", sort="-x", title="Domain"),
                tooltip=["domain", "count"],
            )
            .properties(height=400)
        )
        st.altair_chart(chart, width="stretch")

    with col_chart2:
        st.subheader("Activity by Hour")
        hourly_counts = filtered_df.groupby("hour").size().reset_index(name="count")

        chart_hour = (
            alt.Chart(hourly_counts)
            .mark_bar()
            .encode(
                x=alt.X("hour", title="Hour (0-23)"),
                y=alt.Y("count", title="Visits"),
                tooltip=["hour", "count"],
            )
            .properties(height=400)
        )
        st.altair_chart(chart_hour, width="stretch")

    # --- Raw Data ---
    st.divider()
    st.subheader("History Log")

    search_term = st.text_input("Search Title or URL", "")
    if search_term:
        search_mask = (
            filtered_df["title"].str.contains(search_term, case=False, na=False)
        ) | (filtered_df["url"].str.contains(search_term, case=False, na=False))
        display_df = filtered_df[search_mask]
    else:
        display_df = filtered_df

    st.dataframe(
        display_df[["dt", "title", "domain", "url"]],
        width="stretch",
        column_config={
            "dt": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
            "url": st.column_config.LinkColumn("URL"),
        },
        height=500,
    )

    # --- Domain Analysis ---
    st.divider()
    st.header("Domain Analysis")

    # Domain Selector (sorted by visit count desc)
    top_domains = filtered_df["domain"].value_counts().index.tolist()
    if top_domains:
        selected_domain = st.selectbox("Select Domain to Analyze", top_domains)

        if selected_domain:
            domain_df = filtered_df[filtered_df["domain"] == selected_domain]

            st.subheader(f"Analytics for {selected_domain}")

            d_col1, d_col2 = st.columns(2)
            d_col1.metric("Visits", len(domain_df))
            d_col2.metric("Unique Pages", domain_df["url"].nunique())

            # Top Pages
            st.markdown("#### Top Pages")
            page_counts = (
                domain_df.groupby(["title", "url"]).size().reset_index(name="count")
            )
            page_counts = page_counts.sort_values("count", ascending=False).head(20)

            st.dataframe(
                page_counts,
                width="stretch",
                column_config={
                    "url": st.column_config.LinkColumn("URL"),
                    "count": st.column_config.NumberColumn("Visits", format="%d"),
                },
                hide_index=True,
            )
    else:
        st.info("No domains available for analysis.")


if __name__ == "__main__":
    main()
