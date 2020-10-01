#!/bin/bash

echo "Running Fantasy Football Metrics Weekly Report application from within virtual environment..."

source ~/.bashrc

cd ~/Projects/fantasy-football-metrics-weekly-report

workon fantasy-football-metrics-weekly-report

python main.py
