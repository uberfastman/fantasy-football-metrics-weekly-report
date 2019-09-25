# Yahoo Fantasy Football Report

<a name="about"></a>
### About
The Yahoo Fantasy Football Report application automatically generates a report in the form of a PDF file that contains a host of metrics and rankings for teams in a given Yahoo Fantasy Football league.

<a name="dependencies"></a>
### Dependencies
The application has only been tested in macOS, but should be cross-platform compatible. The app requires Python 3 (Python 2 is no longer supported).

Project dependencies can be viewed in the `requirements.txt` file.

<a name="setup"></a>
### Setup*

* Log in to a Yahoo account with access to whatever fantasy football leagues from which you wish to retrieve data.
* Go to [https://developer.yahoo.com/apps/create/](https://developer.yahoo.com/apps/create/) and create an app (you must be logged into your Yahoo account as stated above). For the app, select the following options:
    * `Application Name` (**Required**): `yffpy` (you can name your app whatever you want, but this is just an example).
    * `Application Type` (**Required**): select the `Installed Application` radio button.
    * `Description` (*Optional*): you *may* write a description of what the app does.
    * `Home Page URL` (*Optional*): if you have a web address related to your app you *may* add it here.
    * `Redirect URI(s)` (**Required**): this field must contain a valid redirect address, so you can use `localhost:8080`
    * `API Permissions` (**Required**): check the `Fantasy Sports` checkbox. You can leave the `Read` option selected (appears in an accordion expansion underneath the `Fantasy Sports` checkbox once you select it).
    * Click the `Create App` button.
    * Once the app is created, it should redirect you to a page for your app, which will show both a `Client ID` and a `Client Secret`.
    * Rename `EXAMPLE-private.json` (located in the `authentication/yahoo` directory) to just `private.json`, and copy the `Client ID` and `Client Secret` values to their respective fields (make sure the strings are wrapped regular quotes (`""`), NOT formatted quotes (`“”`)). The path to this file will be needed to point YFFPY to your credentials.
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

* In the `config.ini`, change the value for `league_id` to your above located league id.

* Run `pip install -r requirements.txt`

* Run `python main.py`. You should see the following prompts: 
    * `Generate report for default league? (y/n) -> `. 
    
        Type `y` and hit enter. 
    * `Generate report for default week? (y/n) ->`. 
        
        Type `y` and hit enter.
    * The ***FIRST*** time you run the app, a browser window will automatically open, and if you correctly followed the instructions in the [Report Setup](#setup) section, you should see a verifier code (something like `w6nwjvz`).
    * Copy the above verifier code and return to the command line window, where you should now see the following prompt:
      ```
      Enter verifier :
      ```
      Paste the verifier code there and hit enter.
    * Assuming the above went as expected, the application should now generate a report for your fantasy league for the selected NFL week.

_\* General setup excludes Google Drive and Slack integrations. See below sections for details on including those additional features._

<a name="configuration"></a>
### Configuration

The Yahoo Fantasy Football Report application allows certain aspects of the generated report to be configured with a `.ini` file. Included in the repository is `EXAMPLE-config.ini`, containing default values, as well as league settings that point to a public Yahoo league as a "demo" of the app.

The app ***REQUIRES*** that `config.ini` be present, so you will need to rename `EXAMPLE-config.ini` to just `config.ini`. Then update the values to reflect the league for which you wish to generate a report, as well as any other settings you wish to change from the default values.

The available settings are as follows:

|                  Option                  | Description |
| ---------------------------------------: | :---------- |
| `league_id`                              | The league id of the Yahoo fantasy football for which you are running the report. |
| `game_id`                                | Yahoo NFL game id by season (see: [Game Resource](https://developer.yahoo.com/fantasysports/guide/game-resource.html#game-resource-desc)) |
| `data_dir`                               | Directory where saved data is stored. |
| `output_dir`                             | Directory where generated reports are created. |
| `chosen_week`                            | Selected NFL season week for which to generate a report.|
| `num_playoff_simulations`                | Number of Monte Carlo simulations to run for playoff predictions. The more sims, the longer the report will take to generate. |
| `num_teams`                              | Number of teams in selected league. |
| `num_regular_season_weeks`               | Number of regular season weeks in selected league. |
| `num_playoff_slots`                      | Number of playoff slots in selected league. |
| `coaching_efficiency_disqualified_teams` | Teams manually DQed from coaching efficiency rankings (if any). |
| `weekly_highest_ce`                      | Dictionary of weeks when multiple teams are tied for highest coaching efficiency and the weekly winner needs to be manually assigned (until such a time as a coaching efficiency tie-break is programmatically implemented) |
| `yahoo_auth_dir`                         | Directory where Yahoo OAuth accesses and stores credentials and refresh tokens. |
| `google_drive_upload`                    | Turn on (`True`) or off (`False`) the Google Drive upload functionality. |
| `google_auth_token`                      | Google OAuth refresh token. |
| `google_drive_root_folder_name`          | Online folder in Google Drive where reports are uploaded. |
| `reupload_file`                          | File path to selected report that you wish to re-upload to Google Drive by running `upload_to_google_drive.py` as a standalone script. |
| `post_to_slack`                          | Turn on (`True`) or off (`False`) the Slack upload functionality. |
| `slack_channel`                          | Selected Slack channel where reports are uploaded. |

<a name="usage"></a>
### Usage

After completing the above setup and configuration steps, you should now be able to simply run `python main.py` to regenerate a report. The report generator script (`main.py`) also supports several command line options that allow you to specify the following:

|             Flag             |                                      Description                                     |
| :--------------------------- | :----------------------------------------------------------------------------------- |
| `-h, --help`                 | Print command line usage message |
| `-l --league-id <league_id>` | Yahoo Fantasy Football league ID |
| `-w --week <week>`           | Chosen week for which to generate report |
| `-g --game-id <game_id>`     | Chosen Yahoo NFL fantasy game id for which to generate report. Defaults to "nfl", which Yahoo interprets as the current season. |
| `-y, --year <year>`          | Chosen year (season) of the league for which a report is being generated. | 
| `-s, --save-data`            | Save all retrieved data locally for faster future report generation |
| `-p, --playoff-prob-sims <int>` | Number of Monte Carlo playoff probability simulations to run." |
| `-b, --break-ties`           | Break ties in metric rankings |
| `-q, --disqualify-ce`        | Automatically disqualify teams ineligible for coaching efficiency metric |
| `-t, --test`                 | Generate TEST report (for development) |
| `-d, --dev-offline`          | Run ***OFFLINE*** (for development). Must have previously run report with -s option. |


When you are done working within the `virtualenv`, you can run `deactivate` within the environment to exit:
```
(fantasy-football-metrics)host-machine:yahoo-fantasy-football-metrics user$ deactivate
```

When you wish to work within the `virtualenv` once more, do the following:
 
 * Run `source ~/.bashrc`
 
 * View `virtualenvs` that you have available: `lsvirtualenv`
 
 * Run `workon fantasy-football-metrics`

<a name="features"></a>
### Additional Features

The Yahoo Fantasy Football Metrics Report Generator also supports several additional features if you choose to utilize them. Currently it is capable of uploading your generated reports to Google Drive, and also directly posting your generated reports to the Slack Messenger app.

<a name="google"></a>
#### Google Drive Integration Setup

The Yahoo Fantasy Football Report application includes Google Drive integration, allowing your generated reports to be uploaded and stored in Google Drive, making it easy to share the report with all league members.

The following setup steps are ***required*** in order to allow the Google Drive integration to function properly:

* Log in to your Google account (or make one if you don't have one).
* Create a [new project](https://console.developers.google.com/projectcreate?folder=&organizationId=0) in the Google Developers Console.
* Accept the terms & conditions.
* Name your project, something like `yyff-report-drive-uploader`, but it can be anything you like.
* Click "CREATE".
* It will take a few moments for the project to be created, but once it is there will be a notification.
* Go to the [Google Developers Console](https://console.developers.google.com/apis/dashboard).
* Your new project should automatically load in the dashboard, but in the event it does not or you have other projects (a different project might load by default), click the project name on the top left of the page (to the right of where it says "Google APIs"), and select your new project.
* Either click the `+ ENABLE APIS AND SERVICES` button on the top of the page, or select "Library" from the menu on the left, search for "Google Drive API", and click "Google Drive API" when it comes up.
* Click `ENABLE`.
* After a moment it will be enabled. Click "Credentials" from the left menu and then click "Create Credentials".
* From the menu that drops down, select "OAuth client ID".
* Click on "Configure Consent Screen".
* Put `yff-report-drive-uploader` in `Application name`.
* Click `Add Scope`, check the box next to the `../auth/drive` scope, and click `ADD`.
* Click `SAVE` at the bottom of the screen.
* Now go click "Credentials" again from the left menu and then click "Create Credentials", then select "OAuth client ID".
* Select "Other" from the radio buttons, and put `yff-report-drive-uploader-client-id`.
* Click "Create".
* A popup with your `client ID` and `client secret` will appear. Click "OK".
* On the far right of your new credential, click the little arrow that displays "Download JSON" when you hover over it.
* Your credentials JSON file will download. Rename it `credentials.json`, and put it in the `authentication/google/` directory where `EXAMPLE-credentials.json` is located.
* Open a terminal window and run `python utils/quickstart.py`.
* A browser window will open asking you to either select a Google account to log into (if you have multiple) or log in. Select your account/login.
* A warning screen will appear saying "This app isn't verified". Click "Advanced" and then "Go to yff-report-drive-uploader (unsafe)" (this screen may vary depending on your web browser, but the point is you need to proceed past the warning).
* On the next screen, a popup saying "Grant yff-report-drive-uploader permission" will appear. Click "Allow", then "Allow" again on the following "Confirm your choices" screen.
* You will see a screen that says only "The authentication flow has completed.", which you can close.
* Go back to your terminal window where you ran `python utils/quickstart.py`. It should have printed "Authentication successful.", as well as a list of 10 files in your Google Drive to confirm it can access your drive. It will also have automatically generated a `token.json` file in `authentication/google/`, which you should just leave where it is and do ***NOT*** edit or modify in any way!
* *You can now upload your reports to Google Drive, either by changing the value of `google_drive_upload` to `True` in `config.ini`, or by setting the value of `reupload_file` in `config.ini` to the filepath to the report you wish to upload, opening a Terminal window, and running `python utils/upload_to_google_drive.py`*.

<a name="slack"></a>
#### Slack Integration Setup

`Coming soon!`

<a name="troubleshooting"></a>
### Troubleshooting

Occasionally when you use the Yahoo fantasy football API, there are hangups on the other end that can cause data not to transmit, and you might encounter an error similar to this:
```
Traceback (most recent call last):
  File "yffpy-app.py", line 114, in <module>
    var = app.run()
  File "/Users/your_username/PATH/T0/LOCAL/PROJECT/yffpy-app.py", line 429, in run
    for team in team_standings:
IndexError: list index out of range
```

Typically when the above error (or a similar error) occurs, it simply means that one of the Yahoo Fantasy Football API calls failed and so no data was retrieved. This can be fixed by simply re-running data query.
