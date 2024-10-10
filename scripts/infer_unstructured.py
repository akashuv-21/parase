import os
import time
import json
import argparse
from pathlib import Path

import unstructured_client
from unstructured_client.models import operations, shared
from unstructured.staging.base import elements_from_dicts

from utils import read_file_paths, validate_json_save_path, load_json_file


CATEGORY_MAP = {
    "NarrativeText": "paragraph",
    "ListItem": "paragraph",
    "Title": "heading1",
    "Address": "paragraph",
    "Header": "header",
    "Footer": "footer",
    "UncategorizedText": "paragraph",
    "Formula": "equation",
    "FigureCaption": "caption",
    "Table": "table",
    "PageBreak": "paragraph",
    "Image": "figure",
    "PageNumber": "paragraph",
    "CodeSnippet": "paragraph"
}


class UnstructuredInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"]
    ):
        """Initialize the UnstructuredInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported file formats.
        """
        self.formats = input_formats

        self.api_key = os.getenv("UNSTRUCTURED_API_KEY") or ""
        self.url = os.getenv("UNSTRUCTURED_URL") or ""

        self.languages = ["eng", "kor"]
        self.get_coordinates = True
        self.infer_table_structure = True

        # create save basepath
        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

        self.client = unstructured_client.UnstructuredClient(
            api_key_auth=self.api_key,
            server_url=self.url,
        )

    def post_process(self, data):
        processed_dict = {}
        for input_key in data.keys():
            output_data = data[input_key]

            processed_dict[input_key] = {
                "elements": []
            }

            id_counter = 0
            for elem in output_data:
                transcription = elem
                category = CATEGORY_MAP.get(elem.category, "paragraph")
                if elem.metadata.coordinates is None:
                    continue

                xy_coord = [{"x": x, "y": y} for x, y in elem.metadata.coordinates.points]

                if category == "table":
                    transcription = elem.metadata.text_as_html

                data_dict = {
                    "coordinates": xy_coord,
                    "category": category,
                    "id": id_counter,
                    "content": {
                        "text": str(transcription) if category != "table" else "",
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

            with open(filepath, "rb") as f:
                data = f.read()

            req = operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(
                        content=data,
                        file_name=str(filepath),
                    ),
                    # --- Other partition parameters ---
                    strategy=shared.Strategy.HI_RES,
                    pdf_infer_table_structure=self.infer_table_structure,
                    coordinates=self.get_coordinates,
                    languages=self.languages,
                ),
            )

            try:
                res = self.client.general.partition(request=req)
                elements = elements_from_dicts(res.elements)
            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

            result_dict[filename] = elements

        result_dict = self.post_process(result_dict)

        with open(self.save_path, "w") as f:
            json.dump(result_dict, f)


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

    unstructured_inference = UnstructuredInference(
        args.save_path,
        input_formats=args.input_formats
    )
    unstructured_inference.infer(args.data_path)

