import sqlite3
import os
import pandas as pd
from datetime import datetime

SAFARI_HISTORY_PATH = os.path.expanduser("~/Library/Safari/History.db")

def get_connection():
    """
    Connects directly to the Safari History database in read-only mode.
    """
    try:
        # Open in read-only mode using URI
        # Note: 'file:' URI requires absolute path
        db_uri = f"file:{SAFARI_HISTORY_PATH}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        return conn
    except sqlite3.OperationalError as e:
        raise RuntimeError(
            f"Permission denied: {e}. "
            "macOS requires 'Full Disk Access' to read Safari History. "
            "Please grant Full Disk Access to your Terminal/IDE in System Settings > Privacy & Security."
        )
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to connect to database: {e}")

def fetch_history_data(conn):
    """
    Fetches raw history data joined with visits.
    """
    query = """
    SELECT
        history_visits.id,
        history_visits.visit_time,
        history_visits.title,
        history_items.url,
        history_items.domain_expansion,
        history_items.visit_count
    FROM
        history_visits
    INNER JOIN
        history_items ON history_visits.history_item = history_items.id
    ORDER BY
        history_visits.visit_time DESC
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()
