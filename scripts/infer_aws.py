import os
import cv2
import json
import time
import boto3
import argparse

from utils import read_file_paths, validate_json_save_path, load_json_file

CATEGORY_MAP = {
    "LAYOUT_TEXT": "paragraph",
    "LAYOUT_LIST": "list",
    "LAYOUT_HEADER": "header",
    "LAYOUT_FOOTER": "footer",
    "LAYOUT_PAGE_NUMBER": "paragraph",
    "LAYOUT_FIGURE": "figure",
    "LAYOUT_TABLE": "table",
    "LAYOUT_TITLE": "heading1",
    "LAYOUT_SECTION_HEADER": "heading1",
    "TABLE": "table"
}


class AWSInference:
    def __init__(
        self,
        save_path,
        input_formats=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heic"]
    ):
        """Initialize the AWSInference class
        Args:
            save_path (str): the json path to save the results
            input_formats (list, optional): the supported file formats.
        """
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") or ""
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") or ""
        AWS_REGION = os.getenv("AWS_REGION") or ""
        AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME") or ""
        self.client = boto3.client(
            "textract",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        self.s3 = boto3.resource("s3")
        self.s3_bucket_name = AWS_S3_BUCKET_NAME

        validate_json_save_path(save_path)
        self.save_path = save_path
        self.processed_data = load_json_file(save_path)

        self.formats = input_formats

    def post_process(self, data):
        def get_text(result, blocks_map):
            text = ""
            if "Relationships" in result:
                for relationship in result["Relationships"]:
                    if relationship["Type"] == "CHILD":
                        for child_id in relationship["Ids"]:
                            word = blocks_map[child_id]
                            if word["BlockType"] == "WORD":
                                text += " " + word["Text"]
            return text[1:]

        processed_dict = {}
        for input_key in data.keys():
            output_data = data[input_key]

            processed_dict[input_key] = {
                "elements": []
            }

            all_elems = {}
            for page_data in output_data:
                for elem in page_data["Blocks"]:
                    _id = elem["Id"]
                    all_elems[_id] = elem

            for page_data in output_data:
                for idx, elem in enumerate(page_data["Blocks"]):
                    if elem["BlockType"] == "LAYOUT_LIST":
                        continue

                    if "LAYOUT" in elem["BlockType"] and elem["BlockType"] != "LAYOUT_TABLE":

                        bbox = elem["Geometry"]["BoundingBox"]

                        x = bbox["Left"]
                        y = bbox["Top"]
                        w = bbox["Width"]
                        h = bbox["Height"]

                        coord = [
                            [x, y],
                            [x + w, y],
                            [x + w, y + h],
                            [x, y + h]
                        ]
                        xy_coord = [{"x": x, "y": y} for x, y in coord]

                        category = CATEGORY_MAP.get(elem["BlockType"], "paragraph")

                        transcription = ""

                        if elem["BlockType"] != "LAYOUT_FIGURE":
                            for item in all_elems[elem["Id"]]["Relationships"]:
                                for id_ in item["Ids"]:
                                    if all_elems[id_]["BlockType"] == "LINE":
                                        word = all_elems[id_]["Text"]
                                        transcription += word + "\n"

                        data_dict = {
                            "coordinates": xy_coord,
                            "category": category,
                            "id": idx,
                            "content": {
                                "text": transcription,
                                "html": "",
                                "markdown": ""
                            }
                        }
                        processed_dict[input_key]["elements"].append(data_dict)

                    elif elem["BlockType"] == "TABLE":

                        bbox = elem["Geometry"]["BoundingBox"]

                        x = bbox["Left"]
                        y = bbox["Top"]
                        w = bbox["Width"]
                        h = bbox["Height"]

                        coord = [
                            [x, y],
                            [x + w, y],
                            [x + w, y + h],
                            [x, y + h]
                        ]
                        xy_coord = [{"x": x, "y": y} for x, y in coord]

                        category = CATEGORY_MAP.get(elem["BlockType"], "paragraph")

                        table_cells = {}
                        for relationship in elem["Relationships"]:
                            if relationship["Type"] == "CHILD":
                                for cell_id in relationship["Ids"]:
                                    cell_block = next((block for block in page_data["Blocks"] if block["Id"] == cell_id), None)
                                    if cell_block is not None and cell_block["BlockType"] == "CELL":
                                        row_index = cell_block["RowIndex"] - 1
                                        column_index = cell_block["ColumnIndex"] - 1
                                        row_span = cell_block["RowSpan"]
                                        column_span = cell_block["ColumnSpan"]
                                        table_cells[(row_index, column_index)] = {
                                            "block": cell_block,
                                            "span": (row_span, column_span),
                                            "text": get_text(cell_block, all_elems),
                                        }
                        max_row_index = max(cell[0] for cell in table_cells.keys())
                        max_column_index = max(cell[1] for cell in table_cells.keys())
                        for relationship in elem["Relationships"]:
                            if relationship["Type"] == "MERGED_CELL":
                                for cell_id in relationship["Ids"]:
                                    cell_block = next((block for block in page_data["Blocks"] if block["Id"] == cell_id), None)
                                    if cell_block is not None and cell_block["BlockType"] == "MERGED_CELL":
                                        row_index = cell_block["RowIndex"] - 1
                                        column_index = cell_block["ColumnIndex"] - 1
                                        row_span = cell_block["RowSpan"]
                                        column_span = cell_block["ColumnSpan"]
                                        for i in range(row_span):
                                            for j in range(column_span):
                                                del table_cells[(row_index + i, column_index + j)]
                                        text = ""
                                        for child_ids in cell_block["Relationships"][0]["Ids"]:
                                            child_cell_block = next((block for block in page_data["Blocks"] if block["Id"] == child_ids), None)
                                            text += " " + get_text(child_cell_block, all_elems)
                                        table_cells[(row_index, column_index)] = {
                                            "block": cell_block,
                                            "span": (row_span, column_span),
                                            "text": text[1:],
                                        }
                        html_table = "<table>"

                        for row_index in range(max_row_index + 1):
                            html_table += "<tr>"
                            for column_index in range(max_column_index + 1):
                                cell_data = table_cells.get((row_index, column_index))
                                if cell_data:
                                    cell_block = cell_data["block"]
                                    row_span, column_span = cell_data["span"]

                                    cell_text = cell_data["text"]
                                    html_table += f"<td rowspan='{row_span}' colspan='{column_span}''>{cell_text}</td>"
                            html_table += "</tr>"
                        html_table += "</table>"

                        data_dict = {
                            "coordinates": xy_coord,
                            "category": category,
                            "id": idx,
                            "content": {
                                "text": "",
                                "html": html_table,
                                "markdown": ""
                            }
                        }
                        processed_dict[input_key]["elements"].append(data_dict)

        for key in self.processed_data:
            processed_dict[key] = self.processed_data[key]

        return processed_dict


    def start_job(self, object_name):
        filename_with_ext = os.path.basename(object_name)

        print(f"uploading {filename_with_ext} to s3")
        self.s3.Bucket(self.s3_bucket_name).upload_file(object_name, filename_with_ext)

        response = None
        response = self.client.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": self.s3_bucket_name,
                    "Name": filename_with_ext
                }
            },
            FeatureTypes = ["LAYOUT", "TABLES"]
        )

        return response["JobId"]

    def is_job_complete(self, job_id):
        time.sleep(1)
        response = self.client.get_document_analysis(JobId=job_id)
        status = response["JobStatus"]
        print("Job status: {}".format(status))

        while(status == "IN_PROGRESS"):
            time.sleep(1)
            response = self.client.get_document_analysis(JobId=job_id)
            status = response["JobStatus"]
            print("Job status: {}".format(status))

        return status

    def get_job_results(self, job_id):
        pages = []
        time.sleep(1)
        response = self.client.get_document_analysis(JobId=job_id)
        pages.append(response)
        print("Resultset page received: {}".format(len(pages)))
        next_token = None
        if "NextToken" in response:
            next_token = response["NextToken"]

        while next_token:
            time.sleep(1)
            response = self.client.\
                get_document_analysis(JobId=job_id, NextToken=next_token)
            pages.append(response)
            print("Resultset page received: {}".format(len(pages)))
            next_token = None
            if "NextToken" in response:
                next_token = response["NextToken"]

        return pages

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

            try:
                if os.path.splitext(filepath)[-1] == ".pdf":
                    job_id = self.start_job(filepath)
                    print("Started job with id: {}".format(job_id))
                    if self.is_job_complete(job_id):
                        result = self.get_job_results(job_id)
                else:
                    with open(filepath, "rb") as file:
                        img_test = file.read()
                        bytes_test = bytearray(img_test)

                    result = self.client.analyze_document(
                        Document={"Bytes": bytes_test},
                        FeatureTypes = ["LAYOUT", "TABLES"]
                    )
            except Exception as e:
                print(e)
                print("Error processing document..")
                error_files.append(filepath)
                continue

            result_dict[filename] = result

        result_dict = self.post_process(result_dict)

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
    args = args.parse_args()

    aws_inference = AWSInference(
        args.save_path,
        input_formats=args.input_formats
    )
    aws_inference.infer(args.data_path)
