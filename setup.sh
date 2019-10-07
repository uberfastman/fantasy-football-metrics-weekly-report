#!/bin/bash

echo -e "===================================================================="
echo -e "RUNNING SETUP BASH SCRIPT FOR FANTASY FOOTBALL METRICS WEEKLY REPORT"
echo -e "====================================================================\n"


PYTHON="$(python3 -V 2>&1)"
if [[ "$PYTHON" == *"Python 3"* ]]; then
  echo -e "===================================================================="
  echo -e "Python 3 version installed: ${PYTHON}"
  echo -e "Continuing setup...\n"
  echo -e "====================================================================\n"
else
  echo -e "===================================================================="
  echo "Python 3 is not installed. Installing..."
  which -s brew
  if [[ $? != 0 ]]; then
    # Install Homebrew
    echo "Homebrew not installed. Installing..."
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    echo -e "====================================================================\n"

    echo "Adding Homebrew path to PATH..."
    touch ~/.profile
    echo 'export PATH="/usr/local/opt/python/libexec/bin:$PATH"' >> ~/.profile
    echo -e "====================================================================\n"
  else
    brew update
    echo -e "====================================================================\n"
  fi
  echo -e "===================================================================="
  echo "Installing Python 3 with Homebrew..."
  brew install python
  echo -e "====================================================================\n"
fi

echo -e "===================================================================="
INSTALLEDVENV="$(pip show virtualenv)"
if [[ $? != 0 ]] ; then
  echo "Installing virtualenv with pip..."
  pip install virtualenv
else
  echo "Module 'virtualenv' already installed. Continuing setup..."
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
INSTALLEDVENVWRAP="$(pip show virtualenvwrapper)"
if [[ $? != 0 ]] ; then
  echo "Installing virtualenvwrapper with pip..."
  pip install virtualenvwrapper
else
  echo "Module 'virtualenvwrapper' already installed. Continuing setup..."
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
GIT="$(git --version 2>&1)"
if [[ "$GIT" == *"git version"* ]]; then
  echo "Git version installed: ${GIT}"
  echo "Continuing setup..."
else
  echo "Installing Git with Homebrew..."
  brew install git
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
REPO="$(basename `git rev-parse --show-toplevel`)"
if [[ $REPO == "fantasy-football-metrics-weekly-report" ]]; then
  echo "Project $REPO already installed and you are in repo directory. Continuing setup..."
  git pull
elif [[ -d "fantasy-football-metrics-weekly-report" ]]; then
  echo "Project $REPO already installed. Entering directory and continuing setup..."
  cd fantasy-football-metrics-weekly-report
  git pull
else
  echo "Cloning Fantasy Football Metrics Weekly Report project from GitHub..."
  git clone https://github.com/uberfastman/fantasy-football-metrics-weekly-report.git
  cd fantasy-football-metrics-weekly-report
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
echo "Adding virtualenv environment variables to '~/.bashrc'..."
touch ~/.bashrc
echo 'export WORKON_HOME=$HOME/.virtualenvs' >> ~/.bashrc
echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
# echo 'export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3' >> ~/.bashrc
source ~/.bashrc
echo -e "====================================================================\n"

echo -e "===================================================================="
EXISTSVENV="$(lsvirtualenv | grep 'fantasy-football-metrics-weekly-report' 2>&1)"
if [[ $? != 0 ]] ; then
  echo "Creating virtualenv 'fantasy-football-metrics-weekly-report' for Fantasy Football Metrics Weekly Report app..."
  mkvirtualenv -p $(which python3) fantasy-football-metrics-weekly-report
else
  echo "Recreating virtualenv 'fantasy-football-metrics-weekly-report' for Fantasy Football Metrics Weekly Report app..."
  deactivate
  rmvirtualenv fantasy-football-metrics-weekly-report
  mkvirtualenv -p $(which python3) fantasy-football-metrics-weekly-report
fi
echo -e "====================================================================\n"

echo -e "===================================================================="
echo "Installing Fantasy Football Metrics Weekly Report project requirements in virtualenv with pip..."
pip install -r requirements.txt
echo -e "====================================================================\n"

echo "Exiting virtualenv..."
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
