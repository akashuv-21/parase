# Document Parsing Models - Inference Guide
## Overview
The scripts in this folder allows users to extract structured data from unstructured documents using different document parsing services and libraries. 
Each service follows a standard installation procedure and provides an infer_* script to perform inference on PDF/Image samples.

You can choose from document parsing products such as **Upstage DP**, **AWS Textract**, **Google Document AI**, **Microsoft Azure Form Recognizer**, **LlamaParse**, or **Unstructured**. Most of these services require an API key for access. Make sure to follow specific setup instructions for each product to properly configure the environment.    

Each service generates a JSON output file in a consistent format.
You can find detailed information about the output format [here](https://github.com/UpstageAI/document-parse-benchmark-private?tab=readme-ov-file#dataset-format).


## Upstage

Follow the [official Upstage DP Documentation](https://developers.upstage.ai/docs/apis/document-parse) to set up Upstage for Document Parsing.

Use the script below to make an inference:
```
$ python infer_upstage.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

## AWS
To use AWS Textract for document parsing, install AWS CLI and Boto3 for API interaction:

```
$ curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
$ unzip awscliv2.zip
$ sudo ./aws/install
$ aws configure
$ pip install boto3
```
Refer to the [AWS Textract Documentation](https://docs.aws.amazon.com/en_us/textract/latest/dg/getting-started.html) for detailed instructions.  

Use the script below to make an inference:
```
$ python infer_aws.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

## Google
Install Google Cloud SDK and Google Document AI for document parsing on Google's platform:

```
$ apt-get install apt-transport-https ca-certificates gnupg curl
$ curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
$ echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
$ apt-get update && apt-get install google-cloud-cli
$ gcloud init
$ pip install google-cloud-documentai
```

More information can be found in the [Google Document AI Documentation](https://console.cloud.google.com/ai/document-ai?hl=en)  

Use the script below to make an inference:
```
$ python infer_google.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

## LlamaParse
Refer to the [official LlamaParse Documentation](https://docs.cloud.llamaindex.ai/category/API/parsing) to install and use LlamaParse for document analysis.  

Use the script below to make an inference:
```
$ python infer_llamaparse.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

## Microsoft
Install the Azure AI Form Recognizer SDK:
```
$ pip install azure-ai-formrecognizer==3.3.0
```
See the [Microsoft Azure Form Recognizer Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/quickstarts/get-started-sdks-rest-api?view=doc-intel-3.0.0&preserve-view=true&pivots=programming-language-python) for additional details.  

Use the script below to make an inference:
```
$ python infer_microsoft.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

## Unstructured

To handle various document formats with Unstructured, follow the steps below:
```
$ pip install "unstructured[all-docs]"
$ pip install poppler-utils

$ apt install tesseract-ocr libtesseract-dev
$ apt install tesseract-ocr-[lang] # use an appropriate language code 
```
Detailed installation instructions can be found [here](https://unstructured-io.github.io/unstructured/installing.html). Use [Tesseract Language Codes](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html) for OCR support in different languages.

Use the script below to make an inference:
```
$ python infer_unstructured.py \
    --data_path <path to the benchmark dataset> \
    --save_path <path to save the .json file>
```

# Standardize Layout Class Mapping
Within each `infer_*` script, a `CATEGORY_MAP` is defined to standardize the mapping of layout elements across different products.  
This ensures uniform evaluation by mapping the extracted document layout classes to the standardized layout categories for comparative analysis and evaluation purposes.  

Be sure to modify the `CATEGORY_MAP` in the inference scripts according to the document layout categories you are working with for accurate results.  

Below is an example of a [CATEGORY_MAP](https://github.com/UpstageAI/document-parse-benchmark-private/blob/776d9212fedb4a07671dcba666f400faf3faad4c/scripts/infer_llamaparse.py#L13) used inside LlamaParse inference script: 
```
CATEGORY_MAP = {
    "text": "paragraph",
    "heading": "heading1",
    "table": "table"
}
```


