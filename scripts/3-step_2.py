import json
import os
import re
import requests
import sys

# from pdfminer.high_level import extract_pages, extract_text
from docling.document_converter import DocumentConverter
from colorama import init, Fore, Back, Style

prompt_step_2 = """Role: You are a strict and methodical Senior Academic Reviewer and Artifact Evaluation Committee Member for the DSN (Dependable Systems and Networks) conference.
Task: Your objective is to perform a rigorous Quality Assessment (QA) on the FULL TEXT of a scientific paper that has already been accepted into a Systematic Literature Review. You must score the paper based on five specific methodological criteria.
SCORING RUBRIC (0 to 2 points per criterion):
- Q1: Reproducibility & Open Science
 - 0 points: No mention of making the source code, datasets, or experimental artifacts publicly available.
 - 1 point: Mentions reproducibility or provides partial details (e.g., pseudo-code), but no working links to public repositories (like GitHub/GitLab) or open datasets are provided.
 - 2 points: Explicitly provides working links to a public repository containing the code, Docker containers, scripts, or full datasets used in the evaluation.
- Q2: Experimental Rigor & Environment
 - 0 points: The evaluation is purely theoretical, lacks a concrete experimental setup, or uses a very small-scale "toy example".
 - 1 point: The evaluation relies entirely on standard software simulations (e.g., ns-3, OMNeT++) without physical hardware or large-scale deployment.
 - 2 points: The evaluation uses physical testbeds (real hardware deployment), emulations (e.g., Mininet with real network stacks), or massive-scale, highly realistic simulations (e.g., cloud deployments).
- Q3: Fault and Threat Model Definition
 - 0 points: The fault or threat model is vague, absent, or poorly defined. The paper does not specify what types of failures the system CANNOT handle.
 - 1 point: Faults are mentioned implicitly or scattered throughout the text without a dedicated, formal definition of assumptions.
 - 2 points: The paper has a clear, explicit section or formal definition detailing the "Fault Model" or "Threat Model", stating precise assumptions (e.g., asynchronous network, up to f Byzantine nodes).
- Q4: Trade-off and Overhead Analysis
 - 0 points: The paper only presents the benefits/successes of the fault tolerance mechanism without measuring its costs.
 - 1 point: The paper acknowledges overhead (e.g., increased latency, CPU usage) but evaluates it superficially.
 - 2 points: The paper provides a rigorous, data-driven analysis of the performance trade-offs (e.g., quantifying the exact cost of replication, checkpointing overhead, or energy consumption).

## OUTPUT FORMAT:
Return ONLY a valid JSON object. Do not include markdown formatting like ```json or any conversational text. Follow this exact structure:
{
"chain_of_thought_evaluation": {
"Q1_analysis": "Explain briefly if code/data links were found.",
"Q2_analysis": "Identify the experimental environment (simulation vs. testbed).",
"Q3_analysis": "State if a formal fault model exists.",
"Q4_analysis": "Explain how overhead/trade-offs were measured."
},
"scores": {
"Q1_reproducibility": [0, 1, or 2],
"Q2_experimental_rigor": [0, 1, or 2],
"Q3_fault_model": [0, 1, or 2],
"Q4_tradeoffs": [0, 1, or 2]
},
"total_quality_score": "[Sum of the 5 scores, from 0 to 10]",
"major_weakness": "In one sentence, identify the area where the paper scored the lowest or lacks detail."
}

## INPUT DATA:

[FULL PAPER TEXT]:



"""

def folder_error(folder_path: str) -> str:
    """
    Use this function to create the string error pointing that a folder path
    was identified as not exists or for not being a directory.

    PARAMETERS:

    folder_path (str): the folder path that isn't a dir or doesn't exists

    RETURNS (str): The standardized string error
    """
    return f"Error: Aparently the path {folder_path} doesn't exists or isn't a folder."

def file_error(file_path: str, exception_msg: str) -> str:
    """
    Use this function to create the string error pointing that a file path was
    identified as not exists or for not being a file.

    PARAMETERS:

    file_path (str): the file path that isn't a file or doesn't exists
    exception_msg (str): the exception message while working with the file

    RETURNS (str): The standardized string error
    """
    return f"Error: Aparently the path {file_path} doesn't exists or isn't a file.\n\n{exception_msg}"

def lmstudio_request_error(exception_msg: str) -> str:
    """
    Use this function to create the string error pointing that something bad
    happened while asking LMStudio to run a prompt on a specift model.

    PARAMETERS:

    exception_msg (str): the exception message while making the request or from the LMStudio response

    RETURNS (str): The standardized string error
    """
    return f"Error: Aparently some error occured while making LMStudio a request.\n\n{exception_msg}."

def save_result_error(result_path: str, exception_msg: str) -> str:
    """
    Use this function to create the string error pointing that a error
    happened while trying to save the LLM result.

    PARAMETERS:

    result_path (str): the filepath to save the result
    exception_msg (str): the exception message

    RETURNS (str): The standardized string error
    """
    return f"Error: some problem happened while saving the results on path {result_path}.\n\n{exception_msg}"

def read_paper_content(paper_filepath: str) -> tuple[str, str]:
    if not os.path.exists(paper_filepath) or not os.path.isfile(paper_filepath):
        return file_error(paper_filepath, '')

    try:
        converter = DocumentConverter()

        result = converter.convert(paper_filepath)

        return (
            result.document.export_to_markdown(),
            ""
        )
    except BaseException as e:
        exception_message = str(e)
        return (
            "",
            file_error(paper_filepath, exception_message)
        )

def make_llstudio_request(
    model: str,
    prompt: str,
    paper_content: str,
    lmStudio_chat_URL: str = "http://localhost:1234/api/v1/chat") -> tuple[str, str]:
    """
    Make a request to LMStudio.

    PARAMETERS:

    model (str): The model name to be invoked
    prompt (str): the prompt to be used
    paper_content (str): The paper content in markdown
    lmStudioChatURL (str): the LMStudio URL point exacly to the API chat route

    RETURNS (tuple[str, str]): tuple[
        string with LLM response (no thinking), empty string in case of error,
        string with execution error, empty string in case of no error
    ]
    """
    try:
        response = requests.post(
            lmStudio_chat_URL,
            headers={
                # "Authorization": f"Bearer {os.environ['LM_API_TOKEN']}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": '/no_think '+ prompt + paper_content,
            }
        )
        response_json = response.json()
        return (
            response_json['output'][0]['content'],
            ""
        )
    except BaseException as e:
        exception_message = str(e)
        return (
            "",
            lmstudio_request_error(exception_message)
        )

def save_json_results(
    llm_result_json: str,
    result_path: str) -> str:
    """
    Save the LLM result to a json file. If some error occur, return a string
    with the error, an empty string is returned with no error occur.

    PARAMETERS:

    llm_result_json (str): The step 2 json response from the LLM
    result_path (str): The filepath to save the paper result

    RETURNS (str): a message pointing the error that occured while creating or
    saving the LLM response to the file, empty string if no error occured.
    """

    try:
        with open(result_path, 'x', encoding="utf-8") as f:
            f.write(llm_result_json)
    except BaseException as e:
        exception_message = str(e)
        save_result_error(result_path, exception_message)

    return ""

def function_step_2(
    papers_folder: str,
    results_folder: str,
    model: str,
    prompt: str) -> str:
    """
    This function process uses a LLM running on LMStudio to process all
    cientific papers inside a specific folder. The objective is to access and
    quantify the paper quality (reproductibility, experimental rigor, fault
    and threat to the research; and trade-off). After process each paper, the
    result is written to a json (with the result of the specific paper).

    PARAMETERS:

    papers_folder (str): The paper folder absolute path 
    results_folder (str): The path to the results folder
    model (str): Name of the model running on the LMStudio
    prompt (str): The prompt to evaluate the papers (individualy)

    RESULT (str): String pointing some error that hapenned durring the
    execution, empty string otherwise. 
    """

    if not os.path.exists(papers_folder) or not os.path.isdir(papers_folder):
        return folder_error(papers_folder)
    
    if not os.path.exists(results_folder) or not os.path.isdir(results_folder):
        return folder_error(results_folder)

    papers = os.walk(papers_folder)
    for root, subdirs, files in papers:
        for file in files:
            print(Fore.BLUE + Back.BLACK + Style.BRIGHT + f"Start of processing: {file}")
            paper_file_path = os.path.join(root, file)

            [content, error] = read_paper_content(paper_file_path)
            if error != "":
                print(Fore.RED + Back.BLACK + Style.BRIGHT + error)
                error_file = 'ERROR_' + os.path.splitext(file)[0] + '.txt'
                with open(os.path.join(results_folder, error_file), 'x', encoding="utf-8") as f:
                    f.write(error)
                continue

            [result, error] = make_llstudio_request(model, prompt, content)
            if error != "":
                print(Fore.RED + Back.BLACK + Style.BRIGHT + error)
                error_file = 'ERROR_' + os.path.splitext(file)[0] + '.txt'
                with open(os.path.join(results_folder, error_file), 'x', encoding="utf-8") as f:
                    f.write(error)
                continue

            result_file_name = os.path.splitext(file)[0] + '.json'
            file_result_path = os.path.join(results_folder, result_file_name)
            error = save_json_results(result, file_result_path)
            if error != "":
                print(Fore.RED + Back.BLACK + Style.BRIGHT + error)
                error_file = 'ERROR_' + os.path.splitext(file)[0] + '.txt'
                with open(os.path.join(results_folder, error_file), 'x', encoding="utf-8") as f:
                    f.write(error)
                continue
            print(Fore.BLUE + f"End of processing: {file}")

if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) != 3:
        print(Fore.RED + Back.BLACK + Style.BRIGHT + 'Tem que passar o parametro com o caminho absoluto para escrita dos prompts')
        sys.exit()
    
    papers_folder = sys.argv[1]
    results_folder = sys.argv[2]
    
    # function_step_2(papers_folder, results_folder, 'deepseek-r1-0528-qwen3-8b', prompt_step_2)
    # function_step_2(papers_folder, results_folder, 'gemma-4-e4b-it', prompt_step_2)
    # function_step_2(papers_folder, results_folder, 'qwen3.5-9b', prompt_step_2)
    function_step_2(papers_folder, results_folder, 'llama-3.1-8b-instruct', prompt_step_2)