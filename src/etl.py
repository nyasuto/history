from datetime import datetime, timedelta
from urllib.parse import urlparse

# Safari uses Cocoa Core Data timestamp (seconds since 2001-01-01 00:00:00 UTC)
COCOA_EPOCH = datetime(2001, 1, 1, 0, 0, 0)


def convert_cocoa_timestamp(timestamp_float):
    """Converts Cocoa Core Data timestamp to Python datetime."""
    return COCOA_EPOCH + timedelta(seconds=timestamp_float)


def extract_domain(url):
    """Extracts the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def process_history_df(df):
    """
    Transforms the raw DataFrame:
    1. Converts timestamps.
    2. Fills missing domains or extracts them from URL.
    3. Adds time-based features (Hour, Date, etc.)
    """
    if df.empty:
        return df

    # 1. Convert timestamp
    # history_visits.visit_time is float
    df["dt"] = df["visit_time"].apply(convert_cocoa_timestamp)

    # Adjust to local time (simplistic approach, ideally use timezone libraries)
    # Streamlit displays datetime in local timezone by default if timezone aware,
    # but let's keep it simple native datetime for now.

    # 2. Domain handling
    # domain_expansion might be None
    df["domain"] = df["domain_expansion"].fillna("")

    # If domain is empty, try to extract from URL
    mask_empty_domain = df["domain"] == ""
    df.loc[mask_empty_domain, "domain"] = df.loc[mask_empty_domain, "url"].apply(
        extract_domain
    )

    # Remove 'www.' for cleaner aggregation
    df["domain"] = df["domain"].str.replace(r"^www\.", "", regex=True)

    # 3. Add features
    df["date"] = df["dt"].dt.date
    df["hour"] = df["dt"].dt.hour
    df["day_of_week"] = df["dt"].dt.day_name()

    return df
