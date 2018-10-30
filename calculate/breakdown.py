from collections import defaultdict
import pandas as pd

# noinspection PyTypeChecker
class Breakdown(object):
    def __init__(self):
        pass
    
    @staticmethod
    def execute_breakdown(teams, matchups_list):
        """
        calculate win/loss/tie breakdown, win chances and luck (based on zscore + win chance)
        
        still uses name field for identifying teams and not team_id
        """
        df = pd.DataFrame(list(teams.values()))
        matchups = {name: value for pair in matchups_list for name, value in list(pair.items())}
        num_teams = len(df.index)

        def breakdown(x):
            return pd.Series({
                'W': len(df[df.score < x.score].index),
                'L': len(df[df.score > x.score].index),
                'T': (len(df[df.score == x.score].index) - 1)
            })
        
        def win_chance(x):
            return (x['W'] / (num_teams - 1)) + (x['T'] / ((num_teams - 1) * 2))

        def luck(x):
            opponent_team_name = matchups[x['name']]["opponent"]
            opponent_zscore = df.loc[df['name'] == opponent_team_name].iloc[0].zscore
            return (x.win_chance - 0.5) + (0 if not x.zscore else x.zscore - opponent_zscore)
        
        df = df.merge(df.apply(breakdown, axis=1), left_index=True, right_index=True)
        df['win_chance'] = df.apply(win_chance, axis=1)
        df['luck'] = df.apply(luck, axis=1)

        # convert back to non dataframe since rest of code doesnt support this stuff
        result = defaultdict(dict) 
        for index, row in df.iterrows():
            team = result[row['name']]
            team['luck'] = row.luck
            team['win_chance'] = row.win_chance
            team['breakdown'] = {
                'W': row['W'],
                'L': row['L'],
                'T': row['T']
            }

        return result


# for testing and such
if __name__ == "__main__":
    bd = Breakdown()

    teams = {
        'team1': {
            'team_id': 1,
            'name': 'team1',
            'score': 30,
            'zscore': 0.5
        },
        'team2': {
            'team_id': 2,
            'name': 'team2',
            'score': 20,
            'zscore': 0.8
        },
        'team3': {
            'team_id': 3,
            'name': 'team3',
            'score': 100,
            'zscore': 2
        },
        'team4': {
            'team_id': 4,
            'name': 'team4',
            'score': 10,
            'zscore': -1
        }
    }

    matchups = [
        {
            'team1': {
                'result': 'W',
                'opponent': 'team2'
            },
            'team2': {
                'result': 'L',
                'opponent': 'team1'
            }
        },
        {
            'team3': {
                'result': 'W',
                'opponent': 'team4'
            },
            'team4': {
                'result': 'L',
                'opponent': 'team3'
            }
        }
    ]

    result = bd.execute_breakdown(teams, matchups)
    import json
    print(json.dumps(result, indent=2))