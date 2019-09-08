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

<a name="usage"></a>
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

<a name="features"></a>
### Additional Features

The Yahoo Fantasy Football Metrics Report Generator also supports several additional features if you choose to utilize them. Currently it is capable of uploading your generated reports to Google Drive, and also directly posting your generated reports to the Slack Messenger app.

<a name="google"></a>
#### Google Drive Integration Setup

`Coming soon!`

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
