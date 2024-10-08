import os
import json
from pathlib import Path
from typing import List


def read_file_paths(path: str, supported_formats: List[str] = [".jpg"]) -> List[str]:
    """Read files in a directory and return their content as a list of strings

    Args:
        path (str): the path to the directory containing the file paths to read
        supported_formats (List[str], optional): the supported file formats. Defaults to [".jpg"].

    Returns:
        list: list of valid file paths

    Raises:
        FileNotFoundError: if the directory does not exist
    """

    path = Path(path)

    # check if the directory exists and is a directory
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Directory {path} not found")

    # get the list of files in the directory
    file_paths = [file for file in path.iterdir() if file.is_file()]

    # filter file paths based on the supported formats
    if supported_formats:
        file_paths = [file for file in file_paths if file.suffix in supported_formats]
    else:
        file_paths = []

    return file_paths


def validate_json_save_path(path: str) -> None:
    # Check if the path ends with .json
    if not path.endswith('.json'):
        raise ValueError(f"The file '{path}' does not have a .json extension.")

    # Get the directory part of the path
    directory = os.path.dirname(path)

    # Check if the directory exists or create it if requested
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def load_json_file(path: str) -> dict:
    # Check if the file exists
    if os.path.isfile(path):
        try:
            # Open and load the JSON file
            with open(path, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading JSON from '{path}': {e}")
            return {}
    else:
        # If the file does not exist, return an empty dictionary
        return {}
