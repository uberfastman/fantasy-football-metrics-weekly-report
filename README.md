# Yahoo Fantasy Football Metrics Report Generator

### About
The Yahoo Fantasy Football Metrics Report Generator is a small application designed to automatically generate a report in the form of a PDF file that contains a host of metrics and rankings for teams in a given Yahoo Fantasy Football league.

### Dependencies
The application has only been tested in macOS, and has now been adapted to run only on Python 3. While previous versions of the app were only compatible with Python 2, Python 2 is now no longer supported.

Project dependencies can be viewed in the `requirements.txt` file.

### Report Generator Setup*

* Go to [https://developer.yahoo.com/apps/create/](https://developer.yahoo.com/apps/create/) and create an app (you must be logged into your Yahoo account). For the app, select the following options:
    * Set `Application Name` to `fantasy-football-metrics` (you can name your app whatever you want, but this is just an example).
    * For `Application Type`, select the `Installed Application` radio button.
    * For `Description`, you may write a description of what the app does (optional).
    * For `API Permissions`, check the `Fantasy Sports` checkbox. You can leave the `Read` option selected (appears in an accordion expansion underneath the `Fantasy Sports` checkbox once you select it).
    * Click the `Create App` button.
    * Once the app is created, it should redirect you to a page for your app, which will show both a `Client ID` and a `Client Secret`.
    * Copy the `Client ID` to the first line of `yahoo-fantasy-football-metrics/authentication/yahoo/private.txt`, and then copy the `Client Secret` to the second line of the `private.txt` file.
    * Now you should be ready to initialize the OAuth connection between the report generator and your Yahoo account.
    
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

* Run `python generate_report.py`. You should see the following prompts: 
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

After completing the above setup steps, you should now be able to simply run `python generate_report.py` to regenerate a report. The report generator script (`generate_report.py`) also supports several command line options that allow you to specify the following:

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
  File "generate_report.py", line 114, in <module>
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
