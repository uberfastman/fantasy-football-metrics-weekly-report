# Fantasy Football Metrics Weekly Report - ESPN Personal Fork

A simplified version of the original Fantasy Football Metrics Weekly Report, streamlined for personal ESPN league use.

## What This Does

Automatically generates a comprehensive PDF report for your ESPN Fantasy Football league with metrics like:
- League standings and playoff probabilities  
- Power rankings, coaching efficiency, and luck metrics
- Bad Boy rankings (player arrests), Beef rankings (player weights), High Roller rankings (fines)
- Weekly top scorers and time series charts
- Individual team breakdowns and statistics

## Quick Setup

1. **Install uv** (modern Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup**:
   ```bash
   git clone https://github.com/AlexSpencer27/fantasy-football-metrics-weekly-report.git
   cd fantasy-football-metrics-weekly-report
   uv sync
   ```

3. **Configure your league**:
   Edit `config.yaml`:
   ```yaml
   league_id: "YOUR_ESPN_LEAGUE_ID"  # Find this in your ESPN league URL
   season: 2025
   current_nfl_week: 2
   ```

4. **Run the report**:
   ```bash
   python main.py
   ```

That's it! Your PDF report will be generated in `output/reports/`.

## Configuration

The `config.yaml` file contains just the essentials:

- `league_id`: Your ESPN league ID (found in the URL)
- `season`: Current NFL season year
- `current_nfl_week`: Current week number
- `refresh_feature_web_data`: Set to `true` to refresh external data (arrests, fines, etc.)
- `espn_cookie_swid` & `espn_cookie_espn_s2`: Only needed for private leagues

All other settings use sensible defaults - all report features enabled, good PDF styling, fast execution.

## Private Leagues

For private ESPN leagues, you'll need to add your session cookies to `config.yaml`. See the [ESPN cookie guide](https://stmorse.github.io/journal/espn-fantasy-3-python.html) for details.

## Changes from Original

This fork simplifies the original app by:
- **ESPN only** - Removed Yahoo, Sleeper, Fleaflicker, CBS support
- **No Docker** - Direct Python execution with uv
- **No CLI arguments** - Simple `python main.py` execution  
- **YAML config** - Replaced complex .env with minimal config.yaml
- **No integrations** - Removed Google Drive, Slack, Discord, GroupMe uploads
- **Hardcoded defaults** - All report features enabled, sensible settings

Perfect for personal league reports without the complexity.

---

*Original project by [Wren J. R. (uberfastman)](https://github.com/uberfastman/fantasy-football-metrics-weekly-report)*