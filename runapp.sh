#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python is not installed. Please install Python and try again."
    exit 1
fi

# Change to the parent directory of the script
cd "$(dirname "$0")" || exit

# Run git pull
git pull


# Check if virtual environment exists
if [ ! -d "env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv env
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Activating existing virtual environment..."
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Run the Python script
python grader_app.py
