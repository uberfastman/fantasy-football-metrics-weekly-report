# Yahoo Fantasy Football Metrics Report Generator

### About
The Yahoo Fantasy Football Metrics Report Generator is a small application designed to automatically generate a report in the form of a PDF file that contains a host of metrics and rankings for teams in a given Yahoo Fantasy Football league.

### Dependencies
The application has only been tested in macOS, and must run on Python 2.x, as several of the required dependencies either do not exist or have changed too much when updated to support Python 3.

Eventually a Python 3 update will be attempted, but for the time being please use a virtualenv to run the app in a sandboxed Python 2 environment.

Project dependencies can be viewed in the `requirements.txt` file.

### Report Generator Setup*

* Open a Terminal window (command line prompt)

* Run `pip install virtualenv virtualenvwrapper` (if not already installed)

* Add the below virtualenvwrapper configs to `~/.bashrc`:
    ```
    export WORKON_HOME=$HOME/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh
    ```
* Run `source ~/.bashrc`

* Navigate to the project root directory:
    ```
    cd /INSERT/PATH/TO/LOCAL/PROJECT/HERE/yahoo-fantasy-football-metrics
    ```

* Run `mkvirtualenv fantasy-football-metrics`

* Update the default Yahoo Fantasy football league id in the `config.ini` to your own league id. You can find your league id by going to [https://football.fantasysports.yahoo.com](https://football.fantasysports.yahoo.com), clicking on your league, and looking here:

    ![yahoo-fantasy-football-league-id-location.png](resources/yahoo-fantasy-football-league-id-location.png)

* In the `config.ini`, change the value for `chosen_league_id` to your above located league id.

* Run `pip install -r requirements.txt`

* Run `python report_generator.py`. You should see the following prompts: 
    * `Generate report for default league? (y/n) -> `. 
    
        Type `y` and hit enter. 
    * `Generate report for default week? (y/n) ->`. 
        
        Type `y` and hit enter.
    * ```
      Visit url https://api.login.yahoo.com/oauth/v2/request_auth?oauth_token=bwu6hgt and get a verifier string
      Enter the code:
      ```
 
        Copy the above URL into a browser window and hit enter, hit the "Agree" button, and then type in the provided code where the command prompt says `Enter the code:`

* Assuming the above went as expected, the application should now generate a report for your fantasy league for the previous NFL week.

_\* General setup excludes Google Drive and Slack integrations. See below sections for details on including those additional features._

### Usage

After completing the above setup steps, you should now be able to simply run `python report_generator.py` to regenerate a report. The report generator script (`report_generator.py`) also supports several command line options that allow you to specify the following:

* `-h`: print command line usage

* `-t`: generate a "test" report (for development)

* `-l [league_id]`: pre-specify the league id for which you wish to generate a report

* `-w [week]`: pre-specify the NFL week for which you wish to generate a report

When you are done working within the `virtualenv`, you can run the `deactivate` within the environment to exit:
```
(fantasy-football-metrics)host-machine:yahoo-fantasy-football-metrics user$ deactivate
```

When you wish to work within the `virtualenv` once more, do the following:
 
 * Run `source ~/.bashrc`
 
 * View `virtualenvs` that you have available: `lsvirtualenv`
 
 * Run `workon fantasy-football-metrics`


### Additional Features

The Yahoo Fantasy Football Metrics Report Generator also supports several additional features if you choose to utilize them. Currently it is capable of uploading your generated reports to Google Drive, and also directly posting your generated reports to the Slack Messenger app.

#### Google Drive Integration Setup

`Coming soon!`

#### Slack Integration Setup

`Coming soon!`

### Troubleshooting

Occasionally when you run the report generator, you encounter an error like this:
```
Traceback (most recent call last):
  File "report_generator.py", line 114, in <module>
    generated_report = fantasy_football_report.create_pdf_report()
  File "/Users/your_username/PATH/T0/LOCAL/PROJECT/yahoo-fantasy-football-metrics/fantasy_football_report_builder.py", line 429, in create_pdf_report
    report_info_dict = self.calculate_metrics(chosen_week=str(week_counter))
  File "/Users/your_username/PATH/T0/LOCAL/PROJECT/yahoo-fantasy-football-metrics/fantasy_football_report_builder.py", line 296, in calculate_metrics
    team_results_dict = self.retrieve_data(chosen_week)
  File "/Users/your_username/PATH/T0/LOCAL/PROJECT/yahoo-fantasy-football-metrics/fantasy_football_report_builder.py", line 250, in retrieve_data
    for player in roster_stats_data[0].get("roster").get("players").get("player"):
IndexError: list index out of range
```

Typically when the above error (or a similar error) occurs, it simply means that one of the Yahoo Fantasy Football API calls failed and so the data needed to generate the report is missing. This can be fixed by simply re-running the report generator.
