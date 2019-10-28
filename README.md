# Fantasy Football Metrics Weekly Report

[![Build Status](https://travis-ci.org/uberfastman/fantasy-football-metrics-weekly-report.svg?branch=develop)](https://travis-ci.org/uberfastman/fantasy-football-metrics-weekly-report)

### Table of Contents
* [About](#about)
    * [Example Report](#example-report)
* [Dependencies](#dependencies)
* [Setup](#setup)
    * [Automated Setup](#automated-setup)
    * [Manual Setup](#manual-setup)
    * [Yahoo Setup](#yahoo-setup)
    * [Fleaflicker Setup](#fleaflicker-setup)
    * [Sleeper Setup](#sleeper-setup)
    * [ESPN Setup](#espn-setup)
* [Running the Report Application](#running-the-report-application)
    * [macOS Launch Script](#macos-launch-script)
* [Configuration](#configuration)
   * [Report Features](#report-features)
   * [Report Settings](#report-settings)
* [Usage](#usage)
    * [Virtual Environment](#virtual-environment)
* [Additional Integrations](#additional-integrations)
    * [Google Drive](#google-drive-setup)
    * [Slack](#slack-setup)
* [Troubleshooting](#troubleshooting)
    * [Logs](#logs)
    * [Yahoo](#yahoo)

---

<a name="about"></a>
### About
The Fantasy Football Metrics Weekly Report application automatically generates a report in the form of a PDF file that contains a host of metrics and rankings for teams in a given fantasy football league.

Currently supported fantasy football platforms:

* **Yahoo**
  
* **Fleaflicker**

* **Sleeper**

* **ESPN**

<a name="example-report"></a>
#### Example Report
***You can see an example of what a report looks like [here](https://github.com/uberfastman/fantasy-football-metrics-weekly-report/blob/develop/resources/files/EXAMPLE-report.pdf)!***

---

<a name="dependencies"></a>
### Dependencies
The application has only been tested in macOS, but should be cross-platform compatible. The app requires Python 3 (Python 2 is no longer supported). To check if you have Python 3 installed, open up a window in Terminal (macOS), Command Prompt (Windows), or a command line shell of your choice, and run `python --version`. If the return is `Python 3.x.x`, you are good to go. If the return is `Python 2.x.x`, you will need to install Python 3. Check out the instructions [here](https://realpython.com/installing-python/) for how to install Python 3 on your system.

Project dependencies can be viewed in the [`requirements.txt`](requirements.txt) file.

---

<a name="setup"></a>
### Setup*

The Fantasy Football Metrics Weekly Report requires several different sets of setup steps, depending on how you wish to run it. To get the application running locally, you will first need to go through the following steps.

_\* General setup excludes Google Drive and Slack integrations. See [Additional Integrations](#additional-integrations) for details on including those add-ons._

<a name="automated-setup"></a>
#### Automated Setup

##### ***FOR USERS RUNNING macOS ONLY (and potentially Linux, although this is untested in Linux)***
There is a pre-made setup bash script in the top level of this repository called `setup.sh`. In lieu of doing the manual setup steps, you can simply do the following:
 
* download the script by righ-clicking [https://raw.githubusercontent.com/uberfastman/fantasy-football-metrics-weekly-report/develop/setup.sh](https://raw.githubusercontent.com/uberfastman/fantasy-football-metrics-weekly-report/develop/setup.sh) and selecting "Download Linked File". A file download should start to your local downloads folder (default is `~/Downloads/` on macOS).

* Open a command line prompt
    * ***macOS***: type `Cmd + Space` (`⌘ + Space`) to bring up Spotlight, and search for "Terminal" and hit enter).
    
* Navigate to wherever you wish to have the Fantasy Football Metrics Weekly Report application set up:
    
    Example (use whatever directory in which you wish to store the app):
    
    ```
    cd ~/projects
    ```

* Move the the `setup.sh` script to the above location:
    
    Example (move the file from your downloads folder):
    
    ```
    mv ~/Downloads/setup.sh .
    ```
  
* Run `./setup.sh`

    * If you get an error when running `./setup.sh`, the script might not be executable. You can run `chmod +x setup.sh` to make it executable. You may need to execute the `chmod` command as an administrator, depending on your system permissions, in which case you can run `sudo chmod +x setup.sh` and then enter your password.

* You can now skip ahead to [Running the Report Application](#running-the-report-application).
  
--- 
 
<a name="manual-setup"></a>
#### Manual Setup

* Make sure your operating system (OS) has Python 3 installed. See the above section on [dependencies](#dependencies) for instructions.

* After you've finished installing Python 3, check that it has been successfully installed by running `python3 --version` (or `py -0p` (or `py -3` to see if you can launch Python 3 if `py -0p` fails) if using the [Python launcher for Windows](https://docs.python.org/3/using/windows.html#python-launcher-for-windows) in Windows to list installed Python version with their paths) in the command line again, and confirming that it outputs `Python 3.x.x`. If it *does **not***, double check that you followed all Python 3 installation steps correctly.

* Open a command line prompt
    * ***macOS***: type `Cmd + Space` (`⌘ + Space`) to bring up Spotlight, and search for "Terminal" and hit enter).
    * ***Windows***: type `Windows + R` to open the "Run" box, then type `cmd` and then click "OK" to open a regular Command Prompt (or type `cmd` and then press `Ctrl + Shift + Enter` to open an administrator Command Prompt)
    * ***Linux***: type `Ctrl+Alt+T` (in Ubuntu).
    
* Install `git` (if you do not already have it installed). You can see instructions for installation on your OS [here](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git). If you are comfortable using the command line, feel free to just install `git` for the command line. *However*, if using the command line is not something you have much experience with and would prefer to do less in a command line shell, you should install [Git for Desktop](https://desktop.github.com).

* Clone this project to whichever directory you wish:

    * If you already have an account on [GitHub](https://github.com), then I recommend using [SSH to connect with GitHub](https://help.github.com/en/articles/connecting-to-github-with-ssh).
    
    * If using SSH (as described in the link above), run:
    ```bash
    git clone git@github.com:uberfastman/fantasy-football-metrics-weekly-report.git
    ```
  
    * If ***not*** using SSH, then use HTTPS by running:
    ```bash
    git clone https://github.com/uberfastman/fantasy-football-metrics-weekly-report.git
    ```
  
* Run `cd fantasy-football-metrics-weekly-report` to enter the project directory.

* Set up a virtual environment:
    * macOS/Linux:

        * Run `pip3 install virtualenv virtualenvwrapper` (if not already installed).

        * Run `touch ~/.bashrc`.

        * Run 
            ```bash
            echo 'export WORKON_HOME=$HOME/.virtualenvs' >> ~/.bashrc
            echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
            ```
  
        * Run `source ~/.bashrc`

        * Run `which python3`. This should output something like `/usr/local/bin/python3`. Copy that path for the next step.

        * Run `mkvirtualenv -p /usr/local/bin/python3 fantasy-football-metrics-weekly-report`.

        * When the previous command is finished running, your command line prompt should now look something like this:
            ```
            (fantasy-football-metrics-weekly-report) [username@Computer 02:52:01 PM] ~/fantasy-football-metrics-weekly-report $
            ```
        Congratulations, you have successfully created a Python 3 virtual environment for the project to run in!

    * Windows:
        * ***If you are using Windows, please follow the instructions for using `virtualenvwrapper-win` [here](https://pypi.org/project/virtualenvwrapper-win/), and adjust the above steps for setting up a virtualenv in macOS/Linux accordingly!***

* Finally, run `pip install -r requirements.txt`

---

<a name="yahoo-setup"></a>
#### Yahoo Setup

* Log in to a Yahoo account with access to whatever fantasy football leagues from which you wish to retrieve data.

* Retrieve your Yahoo Fantasy football league id, which you can find by going to [https://football.fantasysports.yahoo.com](https://football.fantasysports.yahoo.com), clicking on your league, and looking here:

    ![yahoo-fantasy-football-league-id-location.png](resources/images/yahoo-fantasy-football-league-id-location.png)
    
* Change the `league_id` value in `config.ini` to the above located league id.

* Go to [https://developer.yahoo.com/apps/create/](https://developer.yahoo.com/apps/create/) and create an app (you must be logged into your Yahoo account as stated above). For the app, select the following options:

    * `Application Name` (**Required**): `yffpy` (you can name your app whatever you want, but this is just an example).
    
    * `Application Type` (**Required**): select the `Installed Application` radio button.
    
    * `Description` (*Optional*): you *may* write a description of what the app does.
    
    * `Home Page URL` (*Optional*): if you have a web address related to your app you *may* add it here.
    
    * `Redirect URI(s)` (**Required**): this field must contain a valid redirect address, so you can use `localhost:8080`
    
    * `API Permissions` (**Required**): check the `Fantasy Sports` checkbox. You can leave the `Read` option selected (appears in an accordion expansion underneath the `Fantasy Sports` checkbox once you select it).
    
    * Click the `Create App` button.
    
    * Once the app is created, it should redirect you to a page for your app, which will show both a `Client ID` and a `Client Secret`.
    
    * Rename `EXAMPLE-private.json` (located in the `auth/yahoo` directory) to just `private.json`, and copy the `Client ID` and `Client Secret` values to their respective fields (make sure the strings are wrapped regular quotes (`""`), NOT formatted quotes (`“”`)). The path to this file will be needed to point YFFPY to your credentials.
    
    * The first time you run the app, it will initialize the OAuth connection between the report generator and your Yahoo account.
    
* **NOTE**: *If your Yahoo league uses FAAB (Free Agent Acquisition Budget) for player waivers, you must set the `initial_faab_budget` value in the `config.ini` file to reflect your league's starting budget, since this information does not seem to be available in the Yahoo API.

* You are now ready to [generate a report!](#running-the-report-application)

---

<a name="fleaflicker-setup"></a>
#### Fleaflicker Setup

Fleaflicker recently implemented a public API, but at the present time it is undocumented and subject to unexpected and sudden changes. *Please note, some of the data required to provide certain information to the report is not currently available in the Sleeper API, so for the time being web-scraping is used to supplement the data gathered from the Fleaflicker API.*

* Retrieve your Fleaflicker league ID. You can find it by looking at the URL of your league in your browser:

    ![fleaflicker-fantasy-football-league-id-location.png](resources/images/fleaflicker-fantasy-football-league-id-location.png)
    
* Change the `league_id` value in `config.ini` to the above located league id.

* Make sure that you have accurately set the `season` configuration value in the `config.ini` file to reflect the desired year/season for which you are running the report application. This will ensure that the location of locally saved data is correct and API requests are properly formed.

* You can also specify the `year` from the command line by running the report with the `-y <chosen_year>` flag.

* Fleaflicker does not require any authentication to access their API at this time, so no additional steps are necessary.

* You are now ready to [generate a report!](#running-the-report-application)

---

<a name="sleeper-setup"></a>
#### Sleeper Setup

Sleeper has a public API, the documentation for which is available [here](https://docs.sleeper.app). The Fantasy Football Metrics Weekly Report application uses this API to retrieve the necessary data to generate reports. *Please note, some of the data required to provide certain information to the report is not currently available in the Sleeper API, so a few small things are excluded in the report until such a time as the data becomes available*. That being said, the missing data does not fundamentally limit the capability of the app to generate a complete report.

* Retrieve your Sleeper league ID. You can find it by looking at the URL of your league in your browser:

    ![sleeper-fantasy-football-league-id-location.png](resources/images/sleeper-fantasy-football-league-id-location.png)
    
* Change the `league_id` value in `config.ini` to the above located league id.

* Make sure that you have accurately set the `current_week` configuration value in the `config.ini` file to reflect the current/ongoing NFL week at the time of running the report. ***This is required for the Fantasy Football Metrics Weekly Report app to run correctly!***

* Sleeper does not require any authentication to access their API at this time, so no additional steps are necessary.

* You are now ready to [generate a report!](#running-the-report-application)

---

<a name="espn-setup"></a>
#### ESPN Setup

ESPN has a public API, but it was just changed from v2 to v3, which introduced some variance to its functionality. At the present time it is also undocumented and subject to unexpected and sudden changes. *Please note, some of the data required to provide certain information to the report is not currently available in the Sleeper API, so a few small things are excluded in the report until such a time as the data becomes available*. That being said, the missing data does not fundamentally limit the capability of the app to generate a complete report.

* Retrieve your ESPN league ID. You can find it by looking at the URL of your league in your browser:

    ![espn-fantasy-football-league-id-location.png](resources/images/espn-fantasy-football-league-id-location.png)
    
* Change the `league_id` value in `config.ini` to the above located league id.

* Make sure that you have accurately set the `season` configuration value in the `config.ini` file to reflect the desired year/season for which you are running the report application. This will ensure that the location of locally saved data is correct and API requests are properly formed.

* You can also specify the `year` from the command line by running the report with the `-y <chosen_year>` flag.

* Public ESPN leagues do not require any authentication to access their API at this time, so no additional steps are necessary for those leagues. However, certain data will not be available if you are not authenticated, so it is advised for you to still follow the below authentication steps anyway. For private leagues, you ***must*** complete the following authentication steps:

    * Steven Morse has done a great deal of fantastic work to help teach people how to use the ESPN fantasy API, and has a useful blog post [here](https://stmorse.github.io/journal/espn-fantasy-3-python.html) detailing how to get your own session cookies. As stated in the aforementioned blog, you can get the cookies by doing the following:
        
        * *"A lot of the ESPN Fantasy tools are behind a login-wall. Since accounts are free, this is not a huge deal, but becomes slightly annoying for GET requests because now we somehow need to “login” through the request. One way to do this is to send session cookies along with the request. Again this can take us into a gray area, but to my knowledge there is nothing prohibited about using your own cookies for personal use within your own league.*
        
          *Specifically, our GET request from the previous post is modified to look like, for example:*

                r = requests.get('http://games.espn.com/ffl/api/v2/scoreboard', 
                 params={'leagueId': 123456, 'seasonId': 2017, 'matchupPeriodId': 1},
                 cookies={'swid': '{SWID-COOKIE-HERE}',
                 		  'espn_s2': 'LONG_ESPN_S2_COOKIE_HERE'})
                 		  
           *This should return the info you want even for a private league. I saw that the SWID and the ESPN_S2 cookies were the magic tickets based on the similar coding endeavors here and here and here.*

           *You can find these cookies in Safari by opening the Storage tab of Developer tools (you can turn on developer tools in preferences), and looking under espn.com in the Cookies folder. In Chrome, you can go to Preferences -> Advanced -> Content Settings -> Cookies -> See all cookies and site data, and looking for ESPN.*
    
    * Depending on what web browser (Firefox, Chrome, Edge, Brave, etc.) you are using, the process for viewing your session cookies in the web inspector will be different. I recommend Googling *"how to inspect element in [browser]"* (for your specific browser) to learn how to use that browser's web inspector.
           
    * Rename `auth/espn/EXAMPLE-private.json` to `auth/espn/private.json`, and copy the above cookies into their respective fields. Please note, the `swid` will be surrounded by curly braces (`{...}`), which must be included.
    
* **NOTE**: *Because ESPN made the change to their API between 2018 and 2019, ESPN support in the Fantasy Football Metrics Weekly Report application is currently limited to the 2019 season and later. Support for historical seasons will be implemented at a later time.

* You are now ready to [generate a report!](#running-the-report-application)

---

<a name="running-the-report-application"></a>
### Running the Report Application

* If you are running on macOS, see [below](#macos-launch-script)!

* *If you followed the setup instructions and set up the application to run in a virtual environment, once you have navigated to the project directory, you **MUST** run*

    ```
    workon fantasy-football-metrics-weekly-report
    ```
  *before running the report **EVERY TIME** you open a new command line prompt to run the application!*

* Make sure you have updated the default league ID (`league_id` value) in the `config.ini` file to your own league id. Please see the respective setup instructions for your chosen platform for directions on how to find your league ID.

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
    
***NOTE***: You can also specify a large number of configuration options directly in the command line. Please see the [usage section](#usage) for more information.

<a name="macos-launch-script"></a>
##### macOS Launch Script
If you are running on macOS, there is an additional bash script available in the project, [run_in_virtualenv.command](run_in_virtualenv.command). This script allows you to double-click it and run the app in a new Terminal window. It ***REQUIRES*** you to have completed all steps in [Setup](#setup), and also the above steps in [Running the Report Application](#running-the-report-application), with the exception of running the `workon` command or the `python main.py` command. Instead, do the following:

* Right click on [run_in_virtualenv.command](run_in_virtualenv.command) and select `Open With`, then select `TextEdit`.

* Modify the path you find in the script after `cd` to point to wherever you cloned the application. You can either use the absolute path (something like `/Users/username/Projects/fantasy-football-metrics-weekly-report`), or a shortcut to your home directory (`~`), like `~/Documents/fantasy-football-metrics-weekly-report`).

* Move [run_in_virtualenv.command](run_in_virtualenv.command) wherever you wish it to be for easy access.

* **You can now double-click [run_in_virtualenv.command](run_in_virtualenv.command) and it will open a new Terminal window and run the application!** *If that fails, you may need to change the permissions on [run_in_virtualenv.command](run_in_virtualenv.command)*. You can do that as follows:
    
    * Open a Terminal window.
    
    * Run `cd path/to/wherever/you/put/run_in_virtualenv.command`
    
    * Run `chmod +x run_in_virtualenv.command`
    
    * If you get a permissions error after running the `chmod` command, you may need to run it as an administrator:
    
        ```
        sudo chmod +x run_in_virtualenv.command
        ```
     
        And then put in your password to allow the operating system to modify the permissions on [run_in_virtualenv.command](run_in_virtualenv.command).
        
    * ***NOW*** you should be able to double-click [run_in_virtualenv.command](run_in_virtualenv.command) to launch the application!

---

<a name="configuration"></a>
### Configuration

The Fantasy Football Metrics Weekly Report application allows certain aspects of the generated report to be configured with a `.ini` file. Included in the repository is `EXAMPLE-config.ini`, containing default values, as well as league settings that point to a public Yahoo league as a "demo" of the app.

The app ***REQUIRES*** that `config.ini` be present, so you will need to rename `EXAMPLE-config.ini` to just `config.ini`. Then update the values to reflect the league for which you wish to generate a report, as well as any other settings you wish to change from the default values.

<a name="report-features"></a>
#### Report Features

For those of you who wish to configure the report to include a custom subset of the available features (for instance, if you want league stats but not team pages, or if you want score rankings but not coaching efficiency), the `Report` section in the config file allows all features to be turned on or off. You must use a boolean value (`True` or `False`) to turn on/off any of the available report features, which are the following:

    league_standings = True
    league_playoff_probs = True
    league_power_rankings = True
    league_z_score_rankings = True
    league_score_rankings = True
    league_coaching_efficiency_rankings = True
    league_luck_rankings = True
    league_weekly_top_scorers = True
    league_weekly_highest_ce = True
    league_bad_boy_rankings = True
    league_beef_rankings = True
    report_time_series_charts = True
    report_team_stats = True
    team_points_by_position_charts = True
    team_bad_boy_stats = True
    team_beef_stats = True
    team_boom_or_bust = True

<a name="report-settings"></a>
#### Report Settings

In addition to turning on/off the features of the report PDF itself, there are additional configuration options, which are as follows:

|                  Option                  | Description |
| ---------------------------------------: | :---------- |
| `platform`                               | Fantasy football platform for which you are generating a report. |
| `supported_platforms`                    | Comma-delimited list of currently supported fantasy football platforms. |
| `league_id`                              | The league id of the fantasy football for which you are running the report. |
| `game_id`                                | Game id by season (see: [Game Resource](https://developer.yahoo.com/fantasysports/guide/game-resource.html#game-resource-desc) for Yahoo) |
| `data_dir`                               | Directory where saved data is stored. |
| `output_dir`                             | Directory where generated reports are created. |
| `chosen_week`                            | Selected NFL season week for which to generate a report.|
| `num_playoff_simulations`                | Number of Monte Carlo simulations to run for playoff predictions. The more sims, the longer the report will take to generate. |
| `bench_positions`                        | Comma-delimited list of available bench positions in your league. |
| `prohibited_statuses`                    | Comma-delimited list of possible statuses in your league that indicate a player was not able to play (only needed if you plan to utilize the automated coaching efficiency disqualification functionality). |
| `initial_faab_budget`                    | Set the initial FAAB (Free Agent Acquisition Budget) for Yahoo leagues, since this information does not seem to be exposed in the API. |
| `num_teams`                              | Number of teams in selected league. |
| `num_regular_season_weeks`               | Number of regular season weeks in selected league. |
| `num_playoff_slots`                      | Number of playoff slots in selected league. |
| `coaching_efficiency_disqualified_teams` | Teams manually DQed from coaching efficiency rankings (if any). |
| `yahoo_auth_dir`                         | Directory where Yahoo OAuth accesses and stores credentials and refresh tokens. |
| `google_drive_upload`                    | Turn on (`True`) or off (`False`) the Google Drive upload functionality. |
| `google_auth_token`                      | Google OAuth refresh token. |
| `google_drive_root_folder_name`          | Online folder in Google Drive where reports are uploaded. |
| `reupload_file`                          | File path of selected report that you wish to re-upload to Google Drive by running `upload_to_google_drive.py` as a standalone script. |
| `post_to_slack`                          | Turn on (`True`) or off (`False`) the Slack upload functionality. |
| `slack_auth_token`                       | Slack authentication token. |
| `post_or_file`                           | Choose whether you post a link to the generated report on Slack (set to `post`), or upload the report PDF itself to Slack (set to `file`).
| `slack_channel`                          | Selected Slack channel where reports are uploaded. |
| `notify_channel`                         | Turn on (`True`) or off (`False`) using the `@here` slack tag to notify chosen Slack channel of a posted report file. |
| `repost_file`                            | File path of selected report that you wish to repost to Slack. | 

---

<a name="usage"></a>
### Usage

After completing the above setup and configuration steps, you should now be able to simply run `python main.py` to regenerate a report. The report generator script (`main.py`) also supports several command line options that allow you to specify the following:

|             Flag             |                                      Description                                     |
| :--------------------------- | :----------------------------------------------------------------------------------- |
| `-h, --help`                 | Print command line usage message |
| `-l, --fantasy-platform <platform>` | Fantasy football platform on which league for report is hosted. |
| `-l --league-id <league_id>` | Fantasy Football league ID |
| `-w --week <week>`           | Chosen week for which to generate report |
| `-g --game-id <game_id>`     | Chosen fantasy game id for which to generate report. Defaults to "nfl", interpreted as the current season if using Yahoo. |
| `-y, --year <year>`          | Chosen year (season) of the league for which a report is being generated. | 
| `-s, --save-data`            | Save all retrieved data locally for faster future report generation |
| `-s, --refresh-web-data`     | Refresh all web data from external APIs (such as bad boy and beef data) |
| `-p, --playoff-prob-sims <int>` | Number of Monte Carlo playoff probability simulations to run." |
| `-b, --break-ties`           | Break ties in metric rankings |
| `-q, --disqualify-ce`        | Automatically disqualify teams ineligible for coaching efficiency metric |
| `-d, --dev-offline`          | Run ***OFFLINE*** (for development). Must have previously run report with -s option. |
| `-t, --test`                 | Generate TEST report (for development) |

---

<a name="virtual-environment"></a>
#### Virtual Environment

When you are done working within the `virtualenv`, you can run `deactivate` within the environment to exit:
```
(fantasy-football-metrics) host-machine: fantasy-football-metrics-weekly-report $ deactivate
```

When you wish to work within the `virtualenv` once more, do the following:
 
 * Run `source ~/.bashrc`
 
 * View `virtualenvs` that you have available: `lsvirtualenv`
 
 * Run `workon fantasy-football-metrics-weekly-report` (or whatever you named your virtual environment for the application).

---

<a name="additional-integrations"></a>
### Additional Integrations

The Fantasy Football Metrics Weekly Report application also supports several additional integrations if you choose to utilize them. Currently it is capable of uploading your generated reports to Google Drive, and also directly posting your generated reports to the Slack Messenger app.

<a name="google-drive-setup"></a>
#### Google Drive Setup

The Fantasy Football Metrics Weekly Report application includes Google Drive integration, allowing your generated reports to be uploaded and stored in Google Drive, making it easy to share the report with all league members.

The following setup steps are ***required*** in order to allow the Google Drive integration to function properly:

* Log in to your Google account (or make one if you don't have one).

* Create a [new project](https://console.developers.google.com/projectcreate?folder=&organizationId=0) in the Google Developers Console.

* Accept the terms & conditions.

* Name your project, something like `ff-report-drive-uploader`, but it can be anything you like.

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

* Your credentials JSON file will download. Rename it `credentials.json`, and put it in the `auth/google/` directory where `EXAMPLE-credentials.json` is located.

* Open a terminal window and run `python utils/quickstart.py`.

* A browser window will open asking you to either select a Google account to log into (if you have multiple) or log in. Select your account/login.

* A warning screen will appear saying "This app isn't verified". Click "Advanced" and then "Go to yff-report-drive-uploader (unsafe)" (this screen may vary depending on your web browser, but the point is you need to proceed past the warning).

* On the next screen, a popup saying "Grant yff-report-drive-uploader permission" will appear. Click "Allow", then "Allow" again on the following "Confirm your choices" screen.

* You will see a screen that says only "The authentication flow has completed.", which you can close.

* Go back to your terminal window where you ran `python resources/google_quickstart.py`. It should have printed "Authentication successful.", as well as a list of 10 files in your Google Drive to confirm it can access your drive. It will also have automatically generated a `token.json` file in `auth/google/`, which you should just leave where it is and do ***NOT*** edit or modify in any way!

* *You can now upload your reports to Google Drive, either by changing the value of `google_drive_upload` to `True` in `config.ini`, or by setting the value of `reupload_file` in `config.ini` to the filepath of the report you wish to upload, opening a Terminal window, and running `python integrations/drive.py`*.

---

<a name="slack-setup"></a>
#### Slack Setup

The Fantasy Football Metrics Weekly Report application includes integration with the poplular personal and business chat app Slack, allowing your generated reports (or links to where they are stored on Google Drive) to be uploaded directly to Slack,  making it easy to share the report with all league members.

The following setup steps are ***required*** in order to allow the Slack integration to function properly:

* Sign in to your slack workspace [here](https://slack.com/signin).

* Once logged in, you need to [create a new app](https://api.slack.com/apps?new_app=1) for your workspace.

* After the popup appears, fill in the fields as follows:

    * `App Name`: `ff-report` (this name can be anything you want)
    
    * `Development Slack Workspace`: Select your chosen Slack workspace from the dropdown menu.
    
* Click `Create App`. You should now be taken to the page for your new app, where you can configure things like the app title card color, the icon, the description, as well as a whole host of other features (see [here](https://api.slack.com/slack-apps) for more information).

* Select `OAuth & Permissions` from the menu on the left.

* Scroll down to the `Scopes` section, from the dropdown menu select the following:

    * `Send messages as ff-report` (`chat:write:bot`) from the `Conversations` category/section 
    
    * `Upload and modify files as user` (`files:write:user`) from the `Files` category/section (Only select this option if you want to be able to upload the actual report PDFs to Slack, otherwise if you are only going to upload a Google Drive link, you can disregard this scope. Slack does not currently provide a way to upload files as the app, only as the logged in user.)
    
* Click `Save Changes`.

* Scroll back to the top of the page and click `Install App to Workspace`. You should be redirected to a confirmation page telling you what your app will be able to do. Click `Allow`.

* You should be redirected back to the app management page for your app. At the top of the `OAuth & Permissions` section you should now see a field containing and `OAuth Access Token`.

* Rename `auth/slack/EXAMPLE-token.json` to `token.json`, and copy the above `OAuth Access Token` into the field value of `token.json` where it says `"SLACK_APP_OAUTH_ACCESS_TOKEN_STRING"`, replacing that string. Make sure you are using douple quotes (`"`) on either side of your token string. 

* *You can now upload your reports to Slack, either by updating the following values in `config.ini`:*

    * `post_to_slack = True`
    
    * `slack_channel = channel-name` (this can be set to whichever channel you wish to post (as long as the user who created the app has access to that channel)
    
  *Or by setting the value of `repost_file` in `config.ini` to the filepath of the report you wish to upload, opening a Terminal window, and running `python integrations/slack.py`*.  

---

<a name="troubleshooting"></a>
### Troubleshooting

<a name="logs"></a>
#### Logs

In addition to printing output from the application to the commadn line, the Fantasy Football Metrics Weekly Report also logs all of the same output to [out.log](logs/out.log), which you can view at any time to see output from past runs of the application.

<a name="yahoo"></a>
#### Yahoo

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
