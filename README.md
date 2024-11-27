# Java AI Grader

The Java AI Grader is a Python tool for grading student Java code submissions using a scoring sheet. It provides a GUI and CLI for flexibility and efficiency.

---

## Usage

1. Create a scoring sheet that tells the AI how to grade

2. Repare the assignment PDF that was given to students

3. Run the app

4. Upload scoring sheet, assignment pdf, and folder that contains student Java files

4. Choose an directory to output the grading brakedowns to

6. Run the grader and review results.

7. Export results as a table in csv, xlsx, or tsv format.

## Things to note

1. Student names are obtained from the first line of their header.
2. You can view the progress of grading through the terminal used to launch the app.

---

## Installation

### Automatic Installation (Recommended)

1. Ensure **Python 3.8+** is installed.
2. Clone the repository:

   ```bash
   git clone https://github.com/trrt-good/JavaAIGrader.git
   cd JavaAIGrader
   ```

3. Run the script:

   ```bash
   ./runapp.sh
   ```

   This will install dependencies and launch the application. Supported on **Linux** and **Mac** only. It's recommended to run this script to launch the application each time.

---

### Manual Installation

1. Ensure **Python 3.8+** is installed.
2. Clone the repository:

   ```bash
   git clone https://github.com/trrt-good/JavaTypeAlongGrader.git
   cd JavaTypeAlongGrader
   ```

3. Make virtual environment:

   ```bash
   python -m venv env
   source env/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the GUI:

   ```bash
   python typealong_app.py
   ```

6. Use the CLI (optional):

   ```bash
   python typealong_grader.py <source_code> <student_directory> <total_points>
   ```

---

### Installing GitHub on Mac (with Homebrew)

1. Install Homebrew (if not already installed):

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install Git using Homebrew:

   ```bash
   brew install git
   ```

3. Verify the installation:

   ```bash
   git --version
   ```

4. Configure Git with your name and email:

   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

Now you're ready to use Git and GitHub on your Mac!

---

---

Happy Grading! 🚀
