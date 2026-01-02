# hist - Safari History Analytics

Analyze and visualize your Safari browsing history with a beautiful dashboard.
Built with Python and Streamlit.

## Features

- 📊 **Rich Dashboard**: View browsing trends, top domains, and activity heatmaps.
- 🔍 **Search & Filter**: Easily find past visits with keyword search and domain filters.
- 📈 **Analytics**: Deep dive into your browsing habits with domain-based and time-based statistics.
- 🚀 **Local**: Runs entirely on your machine. Your history data never leaves your computer.

## Requirements

- Python 3.10+
- macOS (to access Safari data)

## Installation & Usage

1. **Clone the repository**
   ```bash
   git clone https://github.com/yast/history.git
   cd history
   ```

2. **Setup Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Dashboard**
   ```bash
   streamlit run app.py
   ```

## Structure

- `app.py`: Main application entry point.
- `src/`: Core logic (Database access, Data processing).

## Data Privacy

This tool reads `~/Library/Safari/History.db` in **read-only** mode. No data is sent to external servers.
