import os
import json
import google
import argparse

from glob import glob
from typing import Optional, Sequence

from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from utils import read_file_paths, validate_json_save_path, load_json_file

CATEGORY_MAP = {
    "paragraph": "paragraph",
    "footer": "footer",
    "header": "header",
    "heading-1": "heading1",
    "heading-2": "heading1",
    "heading-3": "heading1",
    "table": "table",
    "title": "heading1"
}


class GoogleInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"]
    ):
        """Initialize the GoogleInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported file formats.
        """
        self.project_id = os.getenv("GOOGLE_PROJECT_ID") or ""

        self.processor_id = os.getenv("GOOGLE_PROCESSOR_ID") or ""

        self.location = os.getenv("GOOGLE_LOCATION") or ""

        self.endpoint = os.getenv("GOOGLE_ENDPOINT") or ""

        self.processor_version = "rc"

        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

        self.formats = input_formats

    @staticmethod
    def generate_html_table(table_data):
        html = "<table border='1'>\n"

        # Process body rows
        for row in table_data["bodyRows"]:
            html += "  <tr>\n"
            for cell in row["cells"]:
                text = cell["blocks"][0]["textBlock"]["text"] if cell["blocks"] else ""
                row_span = f" rowspan='{cell['rowSpan']}'" if cell["rowSpan"] > 1 else ""
                col_span = f" colspan='{cell['colSpan']}'" if cell["colSpan"] > 1 else ""
                html += f"    <td{row_span}{col_span}>{text}</td>\n"
            html += "  </tr>\n"

        html += "</table>"
        return html

    @staticmethod
    def iterate_blocks(data):
        block_sequence = []

        def recurse_blocks(blocks):
            for block in blocks:
                block_id = block.get("blockId", "")
                block_type = block.get("textBlock", {}).get("type", "")
                block_text = block.get("textBlock", {}).get("text", "")

                if block_type:
                    # Append block information as a tuple to the sequence list
                    block_sequence.append((block_id, block_type, block_text))

                block_id = block.get("blockId", "")
                block_table = block.get("tableBlock", {})

                if block_table:
                    block_table_html = GoogleInference.generate_html_table(block_table)
                    block_sequence.append((block_id, "table", block_table_html))

                # If the block contains sub-blocks, recurse through them
                if block.get("textBlock", {}).get("blocks", []):
                    recurse_blocks(block["textBlock"]["blocks"])

        if "documentLayout" in data:
            recurse_blocks(data["documentLayout"].get("blocks", []))

        return block_sequence

    def post_process(self, data):

        processed_dict = {}
        for input_key in data.keys():
            output_data = data[input_key]

            processed_dict[input_key] = {
                "elements": []
            }

            blocks = self.iterate_blocks(output_data)

            id_counter = 0
            for _, category, transcription in blocks:
                category = CATEGORY_MAP.get(category, "paragraph")

                data_dict = {
                    "coordinates": [[0, 0], [0, 0], [0, 0], [0, 0]],
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

    def process_document_layout_sample(self, file_path, mime_type, chunk_size=1000) -> None:
        process_options = documentai.ProcessOptions(
            layout_config=documentai.ProcessOptions.LayoutConfig(
                chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                    chunk_size=chunk_size,
                    include_ancestor_headings=True,
                )
            )
        )
        document = self.process_document(
            file_path,
            mime_type,
            process_options=process_options,
        )

        document_dict = json.loads(google.cloud.documentai_v1.Document.to_json(document))

        return document_dict

    def process_document(
        self, file_path,
        mime_type: str,
        process_options: Optional[documentai.ProcessOptions] = None,
    ) -> documentai.Document:
        client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(
                api_endpoint=f"{self.endpoint}"
            )
        )

        with open(file_path, "rb") as image:
            image_content = image.read()

        name = client.processor_version_path(
            self.project_id,
            self.location,
            self.processor_id,
            self.processor_version
        )
        request = documentai.ProcessRequest(
            name=name,
            raw_document=documentai.RawDocument(
                content=image_content, mime_type=mime_type
            ),
            process_options=process_options,
        )

        result = client.process_document(request=request)

        return result.document

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

            if filepath.suffix == ".pdf":
                mime_type = "application/pdf"
            elif filepath.suffix == ".jpg" or filepath.suffix == ".jpeg":
                mime_type = "image/jpeg"
            elif filepath.suffix == ".png":
                mime_type = "image/png"
            else:
                raise NotImplementedError

            filename = filepath.name

            if filename in self.processed_data.keys():
                print(f"'{filename}' is already in the loaded dictionary. Skipping this sample")
                continue

            try:
                document_dict = self.process_document_layout_sample(filepath, mime_type)
            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

            result_dict[filename] = document_dict

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

    google_inference = GoogleInference(
        args.save_path,
        input_formats=args.input_formats
    )
    google_inference.infer(args.data_path)
