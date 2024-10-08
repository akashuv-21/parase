import os
import json
import argparse

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from utils import read_file_paths, validate_json_save_path, load_json_file


CATEGORY_MAP = {
    "Title": "heading1",
    "SectionHeading": "heading1",
    "footnote": "footnote",
    "PageHeader": "header",
    "PageFooter": "footer",
    "Paragraph": "paragraph",
    "Subheading": "heading1",
    "SectionMarks": "paragraph",
    "PageNumber": "paragraph"
}


class MicrosoftInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"]
    ):
        """Initialize the MicrosoftInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported file formats.
        """
        KEY = os.getenv("MICROSOFT_API_KEY") or ""
        ENDPOINT = os.getenv("MICROSOFT_ENDPOINT") or ""

        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=ENDPOINT, credential=AzureKeyCredential(KEY)
        )

        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

        self.formats = input_formats

    def post_process(self, data):
        processed_dict = {}
        for input_key in data.keys():
            output_data = data[input_key]

            processed_dict[input_key] = {
                "elements": []
            }

            id_counter = 0
            for par_elem in output_data["paragraphs"]:
                category = par_elem["role"]
                category = CATEGORY_MAP.get(category, "paragraph")

                transcription = par_elem["content"]
                coord = [[pt["x"], pt["y"]] for pt in par_elem["bounding_regions"][0]["polygon"]]
                xy_coord = [{"x": x, "y": y} for x, y in coord]

                data_dict = {
                    "coordinates": xy_coord,
                    "category": category,
                    "id": id_counter,
                    "content": {
                        "text": transcription,
                        "html": "",
                        "markdown": ""
                    }
                }
                processed_dict[input_key]["elements"].append(data_dict)

                id_counter += 1

            html_transcription = ""
            for table_elem in output_data["tables"]:
                coord = [[pt["x"], pt["y"]] for pt in table_elem["bounding_regions"][0]["polygon"]]
                xy_coord = [{"x": x, "y": y} for x, y in coord]

                category = "table"

                html_transcription += "<table>"

                # Create a matrix to represent the table
                table_matrix = [
                    ["" for _ in range(table_elem["column_count"])] for _ in range(table_elem["row_count"])
                ]

                # Fill the matrix with table data
                for cell in table_elem["cells"]:
                    row = cell["row_index"]
                    col = cell["column_index"]
                    rowspan = cell.get("row_span", 1)
                    colspan = cell.get("column_span", 1)
                    content = cell["content"]

                    # Insert content into the matrix, handle rowspan and colspan
                    for r in range(row, row + rowspan):
                        for c in range(col, col + colspan):
                            if r == row and c == col:
                                table_matrix[r][c] = f"<td rowspan='{rowspan}' colspan='{colspan}'>{content}</td>"
                            else:
                                # Mark cells covered by rowspan or colspan
                                table_matrix[r][c] = None

                # Generate HTML from the matrix
                for row in table_matrix:
                    html_transcription += "<tr>"
                    for cell in row:
                        if cell is not None:
                            html_transcription += f"{cell}"
                    html_transcription += "</tr>"

                html_transcription += "</table>"

                data_dict = {
                    "coordinates": xy_coord,
                    "category": category,
                    "id": id_counter,
                    "content": {
                        "text": "",
                        "html": html_transcription,
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
        for idx, filepath in enumerate(paths):
            print("({}/{}) {}".format(idx+1, len(paths), filepath))

            filename = filepath.name
            if filename in self.processed_data.keys():
                print(f"'{filename}' is already in the loaded dictionary. Skipping this sample")
                continue

            input_data = open(filepath, "rb")

            try:
                poller = self.document_analysis_client.begin_analyze_document(
                    "prebuilt-layout", document=input_data
                )
                result = poller.result()

                json_result = result.to_dict()
            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

            result_dict[filename] = json_result

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
        type=str, default=[
            ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"
        ],
        help="Supported input file formats"
    )
    args = args.parse_args()

    microsoft_inference = MicrosoftInference(
        args.save_path,
        input_formats=args.input_formats
    )
    microsoft_inference.infer(args.data_path)
