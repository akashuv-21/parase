import os
import sys
import json
import requests
import argparse

from pathlib import Path
from utils import read_file_paths, validate_json_save_path, load_json_file


class UpstageInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"],
        output_formats=["text", "html", "markdown"],
        model_name="document-parse-240910",
    ):
        """Initialize the UpstageInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported input file formats.
            output_formats (list, optional): the supported output formats.
            model_name (str, optional): the model name. Defaults to "document-parse-240910".
        """

        self.endpoint = os.getenv("UPSTAGE_ENDPOINT", "")
        self.api_key = os.getenv("UPSTAGE_API_KEY", "")

        if not all([self.endpoint, self.api_key]):
            raise ValueError("Please set the environment variables for Upstage")

        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

        self.input_formats = input_formats
        self.output_formats = output_formats

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        self.data = {
            "ocr": "force",
            "model": model_name,
            "output_formats": f"{self.output_formats}"
        }

    def infer(self, file_path) -> None:
        """Infer the layout of the documents in the given file path
        Args:
            file_path (str): the path to the file or directory containing the documents to process
        """

        paths = read_file_paths(file_path, self.input_formats)

        error_files = []

        result_dict = {}
        for idx, filepath in enumerate(paths):
            print("({}/{}) {}".format(idx+1, len(paths), filepath))

            filename = Path(filepath).name
            if filename in self.processed_data.keys():
                print(f"'{filename}' is already in the loaded dictionary. Skipping this sample")
                continue

            files = {
                "document": open(filepath, "rb"),
            }

            try:
                # The API does not support files exceeding 50MB
                # or containing more than 100 pages.
                response = requests.post(
                    self.endpoint,
                    headers=self.headers,
                    files=files,
                    data=self.data
                )
                json_result = response.json()

                result_dict[filename] = json_result

            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

        for key in self.processed_data:
            result_dict[key] = self.processed_data[key]

        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=4)

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
    args.add_argument(
        "--output_formats",
        type=list, default=["text", "html", "markdown"],
        help="Output formats supported by the API"
    )
    args = args.parse_args()

    upstage_inference = UpstageInference(
        args.save_path,
        input_formats=args.input_formats,
        output_formats=args.output_formats
    )
    upstage_inference.infer(args.data_path)
