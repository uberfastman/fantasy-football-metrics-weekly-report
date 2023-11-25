
from typing import List, Dict

# nfl team abbreviations
nfl_team_abbreviations: List[str] = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAR", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
]

# small reference dict to convert between commonly used alternate team abbreviations
nfl_team_abbreviation_conversions: Dict[str, str] = {
    "JAC": "JAX",
    "LA": "LAR",
    "WSH": "WAS"
}

# prohibited player statuses to check team coaching efficiency eligibility if dq_ce = True
prohibited_statuses = {
    "O": "Out",
    "Out": "Out",
    "NA": "Inactive: Coach's Decision or Not on Roster",
    "INACTIVE": "Inactive: Coach's Decision or Not on Roster",
    "IR-R": "Injured Reserve - Designated for Return",
    "IR": "Injured Reserve",
    "COVID-19": "Reserve: COVID-19",
    "SUSP": "Suspended",
    "Reserve-Sus": "Suspended",
    "DNR": "Reserve: Did Not Report",
    "PUP-P": "Physically Unable to Perform (Preseason)",
    "PUP-R": "Physically Unable to Perform (Regular Season)",
    "NFI": "Non-Football Injury",
    "NFI-A": "Non-Football Injury (Active)",
    "NFI-R": "Non-Football Injury (Reserve)",
    "EX": "Reserve: Exemption",
    "Reserve-Ex": "Reserve: Exemption",
    "CEL": "Reserve: Commissioner Exempt List",
    "Reserve-CEL": "Reserve: Commissioner Exempt List",
    "RET": "Reserve: Retired",
    "Reserve-Ret": "Reserve: Retired"
}
