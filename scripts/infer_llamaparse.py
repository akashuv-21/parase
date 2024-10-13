import os
import time
import json
import markdown
import requests
import argparse
from pathlib import Path

from bs4 import BeautifulSoup
from utils import read_file_paths, validate_json_save_path, load_json_file


CATEGORY_MAP = {
    "text": "paragraph",
    "heading": "heading1",
    "table": "table"
}


class LlamaParseInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"]
    ):
        """Initialize the LlamaParseInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported file formats.
        """
        self.formats = input_formats

        self.api_key = os.getenv("LLAMAPARSE_API_KEY") or ""
        self.post_url = os.getenv("LLAMAPARSE_POST_URL") or ""
        self.get_url = os.getenv("LLAMAPARSE_GET_URL") or ""

        if not all([self.api_key, self.post_url, self.get_url]):
            raise ValueError("Please set the environment variables for LlamaParse")

        self.headers = {
              "Accept": "application/json",
              "Authorization": f"Bearer {self.api_key}",
        }

        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

    def post_process(self, data):
        processed_dict = {}
        for input_key in data.keys():
            output_data = data[input_key]

            processed_dict[input_key] = {
                "elements": []
            }

            id_counter = 0
            for elem in output_data["pages"]:
                for item in elem["items"]:

                    coord = [[0, 0], [0, 0], [0, 0], [0, 0]]
                    category = item["type"]
                    if category == "table":
                        transcription = markdown.markdown(
                            item["md"],
                            extensions=["markdown.extensions.tables"]
                        )
                        transcription = transcription.replace("\n", "")
                    else:
                        transcription = item["value"]
                        pts = item["bBox"]
                        if "x" in pts and "y" in pts and \
                                "w" in pts and "h" in pts:
                            coord = [
                                [pts["x"], pts["y"]],
                                [pts["x"] + pts["w"], pts["y"]],
                                [pts["x"] + pts["w"], pts["y"] + pts["h"]],
                                [pts["x"], pts["y"] + pts["h"]],
                            ]

                    xy_coord = [{"x": x, "y": y} for x, y in coord]

                    category = CATEGORY_MAP.get(category, "paragraph")
                    data_dict = {
                        "coordinates": xy_coord,
                        "category": category,
                        "id": id_counter,
                        "content": {
                            "text": transcription if category != "table" else "",
                            "html": transcription if category == "table" else "",
                            "markdown": ""
                        }
                    }
                    processed_dict[input_key]["elements"].append(data_dict)

                    id_counter += 1

        for key in self.processed_data:
            processed_dict[key] = self.processed_data[key]

        return processed_dict

    def infer(self, file_path):
        """Infer the layout of the documents in the given file path
        Args:
            file_path (str): the path to the file or directory containing the documents to process
        """
        paths = read_file_paths(file_path, supported_formats=self.formats)

        error_files = []

        result_dict = {}
        for filepath in paths:
            print("({}/{}) Processing {}".format(paths.index(filepath) + 1, len(paths), filepath))

            filename = filepath.name
            if filename in self.processed_data.keys():
                print(f"'{filename}' is already in the loaded dictionary. Skipping this sample")
                continue

            try:
                with open(filepath, "rb") as file_data:
                    file_data = {
                        "file": ("dummy.pdf", file_data, "")
                    }
                    data = {
                        "invalidate_cache": True,
                        "premium_mode": True,
                        "disable_ocr": False
                    }
                    response = requests.post(
                        self.post_url, headers=self.headers, files=file_data, data=data
                    )

                result_data = response.json()
                status = result_data["status"]
                id_ = result_data["id"]

                while status == "PENDING":
                    get_url = f"{self.get_url}/{id_}"
                    response = requests.get(get_url, headers=self.headers)

                    response_json = response.json()
                    status = response_json["status"]
                    if status == "SUCCESS":
                        get_url = f"{self.get_url}/{id_}/result/json"
                        response = requests.get(get_url, headers=self.headers)
                        break

                    time.sleep(1)

                result_dict[filename] = response.json()
            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

        result_dict = self.post_process(result_dict)

        with open(self.save_path, "w") as f:
            json.dump(result_dict, f)

        for error_file in error_files:
            print(f"Error processing file: {error_file}")

        print("Finished processing all documents")
        print("Results saved to: {}".format(self.save_path))
        print("Number of errors: {}".format(len(error_files)))


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument(
        "--data_path",
        type=str, default="", required=True,
        help="Path containing the documents to process"
    )
    args.add_argument(
        "--save_path",
        type=str, default="", required=True,
        help="Path to save the results"
    )
    args.add_argument(
        "--input_formats",
        type=list, default=[
            ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"
        ],
        help="Supported input file formats"
    )
    args = args.parse_args()

    llamaparse_inference = LlamaParseInference(
        args.save_path,
        input_formats=args.input_formats
    )
    llamaparse_inference.infer(args.data_path)

