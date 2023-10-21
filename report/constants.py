
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
