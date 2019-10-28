#!/bin/bash

echo -e "===================================================================="
echo -e "RUNNING SETUP BASH SCRIPT FOR FANTASY FOOTBALL METRICS WEEKLY REPORT"
echo -e "====================================================================\n"


echo -e "===================================================================="
PYTHON3="$(python3 -V 2>&1)"
if [[ "$PYTHON3" == *"Python 3"* ]]; then
  echo -e "Python 3 version installed: ${PYTHON3}. Continuing setup...\n\n"

  PYTHON="$(python -V 2>&1)"
  if [[ "$PYTHON" == *"Python 3"* ]]; then
    echo -e "Python 3 is set as default Python. Continuing setup...\n\n"
  else
    echo -e "Python 3 is NOT set as default Python. Changing deafult Python to Python 3...\n\n"
    touch ~/.bashrc
    printf '\n' >> ~/.bashrc
    echo 'export PATH="/usr/local/opt/python/libexec/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
  fi
else
  echo "Python 3 is not installed. Installing...\n\n"
  which -s brew
  if [[ $? != 0 ]]; then
    # Install Homebrew
    echo -e "Homebrew not installed. Installing...\n\n"
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

    echo -e "Adding Homebrew path to PATH..."
    touch ~/.bashrc
    printf '\n' >> ~/.bashrc
    echo 'export PATH="/usr/local/opt/python/libexec/bin:$PATH"' >> ~/.bashrc
  else
    brew update
  fi
  echo -e "Installing Python 3 with Homebrew...\n\n"
  brew install python
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
INSTALLEDVENV="$(pip show virtualenv)"
if [[ $? != 0 ]] ; then
  echo -e "Pip virtualenv module not found. Installing with pip...\n\n"
  pip install virtualenv
else
  echo -e "Module 'virtualenv' already installed. Continuing setup...\n\n"
fi

INSTALLEDVENVWRAP="$(pip show virtualenvwrapper)"
if [[ $? != 0 ]] ; then
  echo -e "Pip virtualenvwrapper module not found. Installing with pip...\n\n"
  pip install virtualenvwrapper
else
  echo -e "Module 'virtualenvwrapper' already installed. Continuing setup...\n\n"
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
GIT="$(git --version 2>&1)"
if [[ "$GIT" == *"git version"* ]]; then
  echo -e "Git version installed: ${GIT}. Continuing setup...\n\n"
else
  echo -e "Git not found. Installing with Homebrew...\n\n"
  brew install git
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
REPO="$(basename `git rev-parse --show-toplevel`)"
if [[ $REPO == "fantasy-football-metrics-weekly-report" ]]; then
  echo -e "Project $REPO already installed and you are in repo directory. Continuing setup...\n\n"
  git pull
elif [[ -d "fantasy-football-metrics-weekly-report" ]]; then
  echo -e "Project $REPO already installed. Entering directory and continuing setup...\n\n"
  cd fantasy-football-metrics-weekly-report
  git pull
else
  echo -e "Cloning Fantasy Football Metrics Weekly Report project from GitHub...\n\n"
  git clone https://github.com/uberfastman/fantasy-football-metrics-weekly-report.git
  cd fantasy-football-metrics-weekly-report
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
touch ~/.bashrc
RCVENVWORKON="$(cat ~/.bashrc | grep 'export WORKON_HOME=$HOME/.virtualenvs')"
if [[ $? != 0 ]] ; then
  echo -e "Adding WORKON_HOME environment variable to '~/.bashrc'...\n\n"
  printf '\n' >> ~/.bashrc
  echo 'export WORKON_HOME=$HOME/.virtualenvs' >> ~/.bashrc
else
  echo -e "WORKON_HOME environment variable is already properly defined. Continuing setup...\n\n"
fi

RCVENVPYTHON="$(cat ~/.bashrc | grep 'export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3')"
if [[ $? != 0 ]] ; then
  echo -e "Adding VIRTUALENVWRAPPER_PYTHON environment variable to '~/.bashrc'...\n\n"
  printf '\n' >> ~/.bashrc
  echo 'export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3' >> ~/.bashrc
else
  echo -e "VIRTUALENVWRAPPER_PYTHON environment variable is already properly defined. Continuing setup...\n\n"
fi

RCVENVWRAP="$(cat ~/.bashrc | grep "source $(which virtualenvwrapper.sh)")"
if [[ $? != 0 ]] ; then
  echo -e "Sourcing virtualenvwrapper.sh in '~/.bashrc'...\n\n"
  printf '\n' >> ~/.bashrc
  echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
else
  echo -e "Sourcing virtualenvwrapper.sh is already properly configured. Continuing setup...\n\n"
fi
# echo 'export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3' >> ~/.bashrc
source ~/.bashrc
printf '\n' >> ~/.bash_profile
echo '[ -r ~/.bashrc ] && . ~/.bashrc' >> ~/.bash_profile
source ~/.bash_profile
echo -e "====================================================================\n"

echo -e "===================================================================="
EXISTSVENV="$(lsvirtualenv | grep 'fantasy-football-metrics-weekly-report' 2>&1)"
if [[ $? != 0 ]] ; then
  echo -e "Virtualenv 'fantasy-football-metrics-weekly-report' does not exist. Creating...\n\n"
  mkvirtualenv -p $(which python3) fantasy-football-metrics-weekly-report
else
  echo -e "Virtualenv 'fantasy-football-metrics-weekly-report' already exists. Recreating...\n\n"
  { # try
    deactivate &> /dev/null && echo -e "Virtualenv active. Exiting and continuing setup...\n\n"
  } || { # catch
    echo -e "Virtualenv not active. Continuing setup...\n\n"
  }
  rmvirtualenv fantasy-football-metrics-weekly-report
  mkvirtualenv -p $(which python3) fantasy-football-metrics-weekly-report
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
echo -e "Installing Fantasy Football Metrics Weekly Report project requirements in virtualenv with pip...\n\n"
pip install -r requirements.txt
echo -e "====================================================================\n"

echo -e "Exiting virtualenv...\n\n"
deactivate

echo -e "===================================================================="
echo -e "===================================================================="
echo -e "===================================================================="
echo "SETUP COMPLETE FOR FANTASY FOOTBALL METRICS WEEKLY REPORT."
echo -e "To use application, first run:\n\n    cd $(pwd) && workon fantasy-football-metrics-weekly-report\n"
echo "Once the above has been run, you will be ready to use the report app with 'python main.py'"
echo -e "===================================================================="
echo -e "===================================================================="
echo -e "====================================================================\n"
