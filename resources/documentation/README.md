# Development Setup

##### <sup>Open issues for development:</sup> [![Help Wanted](https://img.shields.io/github/labels/uberfastman/fantasy-football-metrics-weekly-report/help%20wanted)](https://github.com/uberfastman/fantasy-football-metrics-weekly-report/labels/help%20wanted)

### Table of Contents
* [Note to Users](#note-to-users)
* [Manual Setup](#manual-setup)
* [Running the Report Application](#running-the-report-application)
    * [macOS Launch Script](#macos-launch-script)
* [Virtual Environment](#virtual-environment)

---

<a name="note-to-users"></a>
### Note to Users
***The following setup instructions are intended for developer use only! For information about how to set up the Fantasy Football Metrics Weekly Report app for regular usage, please see the setup documentation [HERE](../../README.md#setup) for more information.***

--- 
 
<a name="manual-setup"></a>
### Manual Setup

* Make sure your operating system (OS) has Python 3.7 (or later) installed. See the above section on [dependencies](../../README.md#dependencies) for instructions.

* After you've finished installing Python 3.7, check that it has been successfully installed by running `python3 --version` (or `py -0p` (or `py -3` to see if you can launch Python 3 if `py -0p` fails) if using the [Python launcher for Windows](https://docs.python.org/3/using/windows.html#python-launcher-for-windows) in Windows to list installed Python version with their paths) in the command line again, and confirming that it outputs `Python 3.x.x`. If it *does **not***, double check that you followed all Python 3 installation steps correctly.

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

    * **macOS/Linux**:

        * Run `pip3 install virtualenv virtualenvwrapper` (if not already installed).

        * Run `touch ~/.bashrc`.

        * Run 
            ```bash
            echo 'export WORKON_HOME=$HOME/.virtualenvs' >> ~/.bashrc
            echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
            ```
  
        * Run `source ~/.bashrc`

        * Run `which python3`. This should output something like `/usr/local/bin/python3`. Copy that path for the next step.
        
    * **Windows**:
   
        * Run `pip3 install virtualenv virtualenvwrapper-win`
            
        * ***Details for using `virtualenvwrapper-win` can be found [here](https://pypi.org/project/virtualenvwrapper-win/).***

    
* Run `mkvirtualenv -p /usr/local/bin/python3 fantasy-football-metrics-weekly-report`.

* When the previous command is finished running, your command line prompt should now look something like this:

    ```bash
    (fantasy-football-metrics-weekly-report) [username@Computer 02:52:01 PM] ~/fantasy-football-metrics-weekly-report $
    ```
        
    Congratulations, you have successfully created a Python 3 virtual environment for the project to run in!
            
        
* Finally, run `pip install -r requirements.txt`

---

<a name="running-the-report-application"></a>
### Running the Report Application

* If you are running on macOS, see [below](#macos-launch-script)!

* *If you followed the setup instructions and set up the application to run in a virtual environment, once you have navigated to the project directory, you **MUST** run*

    ```bash
    workon fantasy-football-metrics-weekly-report
    ```
  
  *before running the report **EVERY TIME** you open a new command line prompt to run the application!*

* Make sure you have updated the default league ID (`league_id` value) in the `config.ini` file to your own league id. Please see the respective setup instructions for your chosen platform for directions on how to find your league ID.

* Run `python main.py`. You should see the following prompts: 

    * `Generate report for default league? (y/n) -> `. 
    
        Type `y` and hit enter. 
        
    * `Generate report for default week? (y/n) ->`. 
        
        Type `y` and hit enter.
        
    * The ***FIRST*** time you run the app, a browser window will automatically open, and if you correctly followed the instructions in the [Report Setup](../../README.md#setup) section, you should see a verifier code (something like `w6nwjvz`).
    
    * Copy the above verifier code and return to the command line window, where you should now see the following prompt:
    
      ```bash
      Enter verifier :
      ```
      
      Paste the verifier code there and hit enter.
      
    * Assuming the above went as expected, the application should now generate a report for your fantasy league for the selected NFL week.
    
***NOTE***: You can also specify a large number of configuration options directly in the command line. Please see the [usage section](../../README.md#usage) for more information.

<a name="macos-launch-script"></a>
##### macOS Launch Script
If you are running on macOS, there is an additional bash script available in the project, [run_in_virtualenv.command](../run_in_virtualenv.command). This script allows you to double-click it and run the app in a new Terminal window. It ***REQUIRES*** you to have completed all steps in [Setup](../../README.md#setup), and also the above steps in [Running the Report Application](#running-the-report-application), with the exception of running the `workon` command or the `python main.py` command. Instead, do the following:

* Right click on [run_in_virtualenv.command](../run_in_virtualenv.command) and select `Open With`, then select `TextEdit`.

* Modify the path you find in the script after `cd` to point to wherever you cloned the application. You can either use the absolute path (something like `/Users/username/Projects/fantasy-football-metrics-weekly-report`), or a shortcut to your home directory (`~`), like `~/Documents/fantasy-football-metrics-weekly-report`).

* Move [run_in_virtualenv.command](../run_in_virtualenv.command) wherever you wish it to be for easy access.

* **You can now double-click [run_in_virtualenv.command](../run_in_virtualenv.command) and it will open a new Terminal window and run the application!** *If that fails, you may need to change the permissions on [run_in_virtualenv.command](../run_in_virtualenv.command)*. You can do that as follows:
    
    * Open a Terminal window.
    
    * Run `cd path/to/wherever/you/put/run_in_virtualenv.command`
    
    * Run `chmod +x run_in_virtualenv.command`
    
    * If you get a permissions error after running the `chmod` command, you may need to run it as an administrator:
    
        ```bash
        sudo chmod +x run_in_virtualenv.command
        ```
     
        And then put in your password to allow the operating system to modify the permissions on [run_in_virtualenv.command](../run_in_virtualenv.command).
        
    * ***NOW*** you should be able to double-click [run_in_virtualenv.command](../run_in_virtualenv.command) to launch the application!

---

<a name="virtual-environment"></a>
#### Virtual Environment

When you are done working within the `virtualenv`, you can run `deactivate` within the environment to exit:

```bash
(fantasy-football-metrics) host-machine: fantasy-football-metrics-weekly-report $ deactivate
```

When you wish to work within the `virtualenv` once more, do the following:
 
 * Run `source ~/.bashrc`
 
 * View `virtualenvs` that you have available: `lsvirtualenv`
 
 * Run `workon fantasy-football-metrics-weekly-report` (or whatever you named your virtual environment for the application).

---
