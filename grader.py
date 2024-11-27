import os
import re
import json
import argparse
from typing import Dict, List, Tuple, Optional, Any
from tqdm import tqdm
import pandas as pd
from colorama import init, Fore, Style
from openai import OpenAI
from anthropic import Anthropic
from groq import Groq
from pdfminer.high_level import extract_text


# Initialize colorama for colored output
init(autoreset=True)

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    with open(config_path, "r") as f:
        return json.load(f)

config = load_config()

def initialize_clients(config: Dict[str, Any]) -> Dict[str, Any]:
    clients = {}
    if 'openai' in config['api_keys']:
        clients['openai'] = OpenAI(api_key=config['api_keys']['openai'])
    if 'anthropic' in config['api_keys']:
        clients['anthropic'] = Anthropic(api_key=config['api_keys']['anthropic'])
    if 'groq' in config['api_keys']:
        clients['groq'] = Groq(api_key=config['api_keys']['groq'])
    return clients

clients = initialize_clients(config)

def color_print(text: str, color: str = Fore.WHITE, style: str = Style.NORMAL) -> None:
    """Print colored text to the console."""
    print(f"{style}{color}{text}")

def parse_assignment_pdf(path_to_pdf: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        text = extract_text(path_to_pdf)
    except Exception as e:
        color_print(f"Error extracting text from PDF: {e}", Fore.RED)
        return None, None
        
    if not text:
        color_print("The PDF file is empty or text extraction failed.", Fore.YELLOW)
        return None, None

    text = text.replace('\t', ' ')

    # Split text into assignment name and assignment prompt
    lines = text.strip().split('\n', 1)
    assignment_name = lines[0].strip()
    assignment_prompt = lines[1].strip() if len(lines) > 1 else ''

    color_print("PDF extraction complete.", Fore.GREEN)
    return assignment_name, assignment_prompt

def generate_system_prompt(assignment_name: str, assignment_prompt: str, scoring_sheet: str) -> str:
    """Generate the system prompt for the AI grader."""
    return f"""
You are an AI grader for a Java programming class. Specifically, you are grading an assignment called {assignment_name}. Some grading instructions, the assignment prompt, and the scoring sheet will be provided below. The user will provide you their code to grade. Do your best job grading.

### **Grading instructions:** 
1. Meticulously go through each and every point in the scoring sheet
    a) first write out the piece of student's code that corresponds to the point(s)
    b) then, explain whether or not the student's code satisfies the scoring sheet requirements
    c) deduct point(s) if necessary. 
2. Combine all deductions and subtract from the total score to obtain the student's score.
3. Output your grading with the following format:
SCORE:[score]
COMMENTS:[a single sentence summary]
CONFIDENCE:[score from 1-5 for the confidence you have in your given grade]

### **Assignment Prompt:**
'''
{assignment_prompt}
'''

### **Scoring Sheet:**
'''
{scoring_sheet}
'''
"""

def call_api(clients: Dict[str, Any], model: str, system_prompt: str, user_prompt: str, config: Dict[str, Any]) -> str:
    """Call the appropriate API based on the selected model."""
    if model.startswith(("gpt", "o1")):
        response = clients['openai'].chat.completions.create(
            model=config['model_map'][model],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config['default_temperature']
        )
        return response.choices[0].message.content.strip()
    elif model.startswith(("llama", "mixtral")):
        response = clients['groq'].chat.completions.create(
            model=config['model_map'][model],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config['default_temperature']
        )
        return response.choices[0].message.content.strip()
    else:  # Assume Anthropic model
        response = clients['anthropic'].messages.create(
            model=config['model_map'][model],
            max_tokens=4096,
            temperature=config['default_temperature'],
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text.strip()

def parse_ai_response(response: str) -> Tuple[float, str, str]:
    # Remove all newlines, whitespace, and stars
    cleaned_response = re.sub(r'[\n\s*#]', '', response)
    
    # Extract score, comments, and confidence using regex
    score_match = re.search(r'SCORE:(.*?)COMMENTS:', cleaned_response)
    comments_match = re.search(r'COMMENTS:(.*?)CONFIDENCE:', cleaned_response)
    confidence_match = re.search(r'CONFIDENCE:(.*?)$', cleaned_response)
    
    # Extract the matched groups or use empty string if not found
    score = score_match.group(1) if score_match else ""
    comments = comments_match.group(1) if comments_match else ""
    confidence = confidence_match.group(1) if confidence_match else ""
    
    # Parse score into a float
    try:
        score = float(score)
    except ValueError:
        score = -100  # Default to -100 if parsing fails
    
    return score, comments, confidence

def preprocess_student_submission(file_path: str) -> Tuple[str, str]:
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Extract student name from the first non-empty line
    student_name = ""
    for line in lines:
        line = line.strip()
        if line:
            student_name = re.sub(r'[^\w\s]', '', line).strip()
            break
    
    # Find the index of the first "import" or "public class" statement
    import_index = next((i for i, line in enumerate(lines) if line.strip().startswith("import")), None)
    public_class_index = next((i for i, line in enumerate(lines) if line.strip().startswith("public class")), None)
    
    # Determine the start of the code
    code_start_index = min(filter(lambda x: x is not None, [import_index, public_class_index, len(lines)]))
    
    # Join all lines before the code as the header
    student_header = ''.join(lines[:code_start_index])

    def remove_comment_symbols(text: str) -> str:
        text = re.sub(r'^\s*//+\s?', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*|\*/', '', text)
        text = re.sub(r'^\s*\*\s?', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*$\n', '', text, flags=re.MULTILINE)
        return text.strip()

    student_header = remove_comment_symbols(student_header)
    
    # Join all lines as the student's code
    student_code = ''.join(lines[code_start_index:])
    
    processed_code = f"**HEADER:**\n{student_header}\n\n**CODE:**\n```java\n{student_code}```"

    # print(student_name)
    # print(processed_code)
    
    return student_name, processed_code

def check_new_lines(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Find the first and last print statements
    first_print = None
    last_print = None
    
    for line in lines:
        if line.startswith('System.out.println('):
            if first_print is None:
                first_print = line
            last_print = line
    
    # Check if both first and last print statements exist
    if first_print is None or last_print is None:
        return False
    
    # Check if the first and last print statements match the required format
    required_print = 'System.out.println("\\n\\n\\n");'
    return first_print != required_print + last_print != required_print

import re

def remove_comments_and_strings(code):
    # Pattern to match comments and strings
    pattern = r'''
        //.*?$              |   # Line comments
        /\*[\s\S]*?\*/      |   # Block comments
        "(?:\\.|[^"\\])*"   |   # Double-quoted strings
        '(?:\\.|[^'\\])*'       # Single-quoted chars
    '''
    regex = re.compile(pattern, re.MULTILINE | re.VERBOSE)
    # Replace matched patterns with spaces to keep line numbers consistent
    return regex.sub(lambda m: ' ' * (m.end() - m.start()), code)

def check_brackets(filepath):
    with open(filepath) as f:
        code = f.read()
    # Remove comments and strings to avoid false positives
    code_no_comments = remove_comments_and_strings(code)
    lines = code_no_comments.split('\n')
    errors = 0
    for line_num, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Skip empty lines
        if '{' in stripped_line or '}' in stripped_line:
            # If the line is exactly '{' or '}', it's acceptable
            if stripped_line == '{' or stripped_line == '}':
                continue
            else:
                # If '{' or '}' is not alone on the line, it's not Allman style
                errors += 1
    # All braces are correctly placed in Allman style
    return errors

def check_formatting(file_path: str, config: Dict[str, Any]) -> float:
    deductions = 0
    deductions += min(config["format_scoring"]["brackets"]["max"], check_brackets(file_path)*config["format_scoring"]["brackets"]["per"])
    deductions += min(config["format_scoring"]["new_lines"]["max"], check_new_lines(file_path)*config["format_scoring"]["new_lines"]["per"])
    return deductions

def find_student_java_files(student_code_dir: str) -> List[str]:
    """Find all Java files in the given directory."""
    return [os.path.join(dirpath, filename)
            for dirpath, dirnames, filenames in os.walk(student_code_dir)
            for filename in filenames if filename.endswith('.java')]

def grade_submissions(student_code_dir: str, assignment_pdf: str, scoring_sheet_file: str, grading_breakdown_dir: str = "GradingBreakdowns", config: Dict[str, Any] = config) -> pd.DataFrame:
    """
    Grade all student submissions in the given directory.

    This function processes Java files in the specified directory, grades them based on the assignment details
    and scoring criteria, and returns a DataFrame with grading results.

    Parameters:
    - student_code_dir (str): Path to the directory containing student code submissions.
    - assignment_pdf (str): Path to the PDF file containing assignment details.
    - scoring_sheet_file (str): Path to the file containing the scoring sheet.
    - grading_breakdown_dir (str): Path to the directory where grading breakdowns will be saved. 
      Defaults to "GradingBreakdowns".
    - config (Dict[str, Any]): Configuration dictionary containing various settings. 
      Defaults to a pre-defined config.

    Returns:
    - pd.DataFrame: A DataFrame containing grading results with columns for student name, score, 
      confidence, and comments.

    The function performs the following steps:
    1. Finds all Java files in the student code directory.
    2. Loads the scoring sheet.
    3. Parses the assignment PDF to extract assignment details.
    4. Generates a system prompt for the AI grading model.
    5. Creates the grading breakdown directory if it doesn't exist.
    6. For each Java file:
       - Preprocesses the student submission.
       - Calls the AI API for grading.
       - Saves the AI's grading breakdown to a file.
       - Parses the AI response to extract score, comments, and confidence.
       - Applies a formatting check and adjusts the score if necessary.
       - Adds the results to a list.
    7. Returns the results as a pandas DataFrame.

    """
    results = []
    java_files = find_student_java_files(student_code_dir)
    
    # Load scoring sheet
    with open(scoring_sheet_file, 'r') as f:
        scoring_sheet_content = f.read()
        
    assignment_name, assignment_info = parse_assignment_pdf(assignment_pdf)
    system_prompt = generate_system_prompt(assignment_name, assignment_info, scoring_sheet_content)
    
    os.makedirs(grading_breakdown_dir, exist_ok=True)

    for java_file in tqdm(java_files, desc="Grading submissions"):
        student_name, student_code = preprocess_student_submission(java_file)

        user_prompt = student_code
        
        try:
            ai_response = call_api(clients, config['default_model'], system_prompt, user_prompt, config)
            
            student_name_no_spaces = student_name.replace(" ", "")

            with open(f"{config['grading_breakdown_folder']}/{student_name_no_spaces}-GradingBreakdown.txt", "w") as f:
                f.write(ai_response)
            
            score, comments, confidence = parse_ai_response(ai_response)
            
            score -= check_formatting(java_file, config)
            
            results.append({
                "Name": student_name,
                "Score": score,
                "Confidence": confidence,
                "Comments": comments
            })
            
        except Exception as e:
            color_print(f"Error grading {student_name}: {str(e)}", Fore.RED)
    
    return pd.DataFrame(results)

def main() -> None:
    parser = argparse.ArgumentParser(description="AI Grader for Java Programming Class")
    parser.add_argument('--scoring_sheet', required=True, help="Path to the scoring sheet file")
    parser.add_argument('--assignment_pdf', required=True, help="Assignment pdf")
    parser.add_argument('--submissions_dir', required=True, help="Directory containing student submissions")
    parser.add_argument('--output_file', default='Graded.csv', help="Path to the output CSV file (default: Graded.csv)")
    parser.add_argument('--breakdown_dir', default='GradingBreakdowns', help="Directory to put the detailed AI grading breakdowns")
    args = parser.parse_args()

    color_print("AI Grader for Java Programming Class", Fore.CYAN, Style.BRIGHT)

    results = grade_submissions(args.submissions_dir, args.assignment_pdf, args.scoring_sheet, args.breakdown_dir, config)
    
    # Save results to CSV
    results.to_csv(args.output_file, index=False)
    color_print(f"Results saved to {args.output_file}", Fore.GREEN)

    color_print("Grading completed successfully!", Fore.GREEN, Style.BRIGHT)

if __name__ == "__main__":
    main()
