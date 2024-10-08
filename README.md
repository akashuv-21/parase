# DP-Bench: Document Parsing Benchmark

<div align="center">
  <img src="https://cdn-uploads.huggingface.co/production/uploads/6524ab1e27d1f3d84ad07705/Q7CC2z4CAJzZ4-CGaSnBO.png" width="800px">
</div>


Document parsing refers to the process of converting complex documents, such as PDFs and scanned images, into structured text formats like HTML and Markdown.
It is especially useful as a preprocessor for [RAG](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) systems, as it preserves key structural information from visually rich documents.

While various parsers are available on the market, there is currently no standard evaluation metric to assess their performance.
To address this gap, we propose a set of new evaluation metrics along with a benchmark dataset designed to measure parser performance.

## Metrics
We propose assessing the performance of parsers using three key metrics: 
NID for element detection and serialization, TEDS and TEDS-S for table structure recognition.

### Element detection and serialization

**NID (Normalized Indel Distance).**
NID evaluates how well a parser detects and serializes document elements according to human reading order.
NID is similar to the [normalized edit distance](https://en.wikipedia.org/wiki/Levenshtein_distance) metric but excludes substitutions during evaluation, making it more sensitive to length differences between strings.

The NID metric is computed as follows:

$$
NID = 1 - \frac{\text{distance}}{\text{len(reference)} + \text{len(prediction)}}
$$

The distance measures the similarity between the reference and predicted text, with values ranging from 0 to 1, where 0 represents perfect alignment and 1 denotes complete dissimilarity. 
Here, the predicted text is compared against the reference text to determine how many character-level insertions and deletions are needed to match it.
A higher NID score reflects better performance in both recognizing and ordering the text within the document's detected layout regions.

### Table structure recognition

Tables are one of the most complex elements in documents, often presenting both structural and content-related challenges. 
Yet, during NID evaluation, table elements (as well as figures and charts) are excluded, allowing the metric to focus on text elements such as paragraphs, headings, indexes, and footnotes. To specifically evaluate table structure and content extraction, we use the [TEDS](https://arxiv.org/abs/1911.10683) and [TEDS-S](https://arxiv.org/abs/1911.10683) metrics.

The [traditional metric](https://ieeexplore.ieee.org/document/1227792) fails to account for the hierarchical nature of tables (rows, columns, cells), but TEDS/TEDS-S measures the similarity between the predicted and ground-truth tables by comparing both structural layout and content, offering a more comprehensive evaluation. 

**TEDS (Tree Edit Distance-based Similarity).**
The TEDS metric is computed as follows:

$$
TEDS(T_a, T_b) = 1 - \frac{EditDist(T_a, T_b)}{\max(|T_a|, |T_b|)}
$$

The equation evaluates the similarity between two tables by modeling them as tree structures ($T_a$ and $T_b$).
This metric evaluates how accurately the table structure is predicted, including the content of each cell.
A higher TEDS score indicates better overall performance in capturing both the table layout and the textual content.

**TEDS-S (Tree Edit Distance-based Similarity-Struct).**
TEDS-S stands for Tree Edit Distance-based Similarity-Struct, measuring the structural similarity between the predicted and reference tables.

## Benchmark dataset

### Document sources
The benchmark dataset is gathered from three sources: 90 samples from the Library of Congress; 90 samples from Open Educational Resources; and 20 samples from Upstage's internal resources, which is composed of company/product materials and [Solar 10.7B](https://arxiv.org/abs/2312.15166) paper. Together, these sources provide a broad and specialized range of information.

<div style="width: 500px;">
  
| Sources                    | Count|
|:--------------------------:|:----:|
| Library of Congress        | 90   |
| Open educational resources | 90   |
| Upstage                    | 20   |

</div>

### Layout elements

While works like [ReadingBank](https://github.com/doc-analysis/ReadingBank) often focus solely on text conversion in document parsing, we have taken a more detailed approach by dividing the document into specific elements, with a particular emphasis on table performance. 

This benchmark dataset was created by extracting pages with various layout elements from multiple types of documents. The layout elements consist of 12 element types: **Table, Paragraph, Figure, Chart, Header, Footer, Caption, Equation, Heading1, List, Index, Footnote**. This diverse set of layout elements ensures that our evaluation covers a wide range of document structures and complexities, providing a comprehensive assessment of document parsing capabilities.

Note that only Heading1 is included among various heading sizes because it represents the main structural divisions in most documents, serving as the primary section title. 
This high-level segmentation is sufficient for assessing the core structure without adding unnecessary complexity. 
Detailed heading levels like Heading2 and Heading3 are omitted to keep the evaluation focused and manageable.

<div style="width: 500px;">
  
| Category   | Count |
|:----------:|:-----:|
| Paragraph  | 804   |
| Heading1   | 194   |
| Footer     | 168   |
| Caption    | 154   |
| Header     | 101   |
| List       | 91    |
| Chart      | 67    |
| Footnote   | 63    |
| Equation   | 58    |
| Figure     | 57    |
| Table      | 55    |
| Index      | 10    |

</div>

### Dataset format

The dataset is in JSON format, representing elements extracted from a PDF file, with each element defined by its position, layout class, and content. 
The **category** field represents various layout classes, including but not limited to text regions, headings, footers, captions, tables, and more.
The **content** field has three options: the **text** field contains text-based content, **html** represents layout regions where equations are in LaTeX and tables in HTML, and **markdown** distinguishes between regions like Heading1 and other text-based regions such as paragraphs, captions, and footers.
Each element includes coordinates (x, y), a unique ID, and the page number it appears on. The dataset’s structure supports flexible representation of layout classes and content formats for document parsing.

```
{
    "01030000000001.pdf": {
        "elements": [
            {
                "coordinates": [
                    {
                        "x": 170.9176246670229,
                        "y": 102.3493458064781
                    },
                    {
                        "x": 208.5023846755278,
                        "y": 102.3493458064781
                    },
                    {
                        "x": 208.5023846755278,
                        "y": 120.6598699131856
                    },
                    {
                        "x": 170.9176246670229,
                        "y": 120.6598699131856
                    }
                ],
                "category": "Header",
                "id": 0,
                "page": 1,
                "content": {
                    "text": "314",
                    "html": "",
                    "markdown": ""
                }
            },
            ...
    ...
```

<div style="width: 800px;">
  
### Document domains
| Domain                              | Subdomain               | Count |
|:-----------------------------------:|:-----------------------:|:-----:|
| Social Sciences                     | Economics               | 26    |
|                                     | Political Science       | 18    |
|                                     | Sociology               | 16    |
|                                     | Law                     | 12    |
|                                     | Cultural Anthropology   | 11    |
|                                     | Education               | 8     |
|                                     | Psychology              | 4     |
| Natural Sciences                    | Environmental Science   | 26    |
|                                     | Biology                 | 10    |
|                                     | Astronomy               | 4     |
| Technology                          | Technology              | 33    |
| Mathematics and Information Sciences| Mathematics             | 13    |
|                                     | Informatics             | 9     |
|                                     | Computer Science        | 8     |
|                                     | Statistics              | 2     |

</div>

## Usage

### Setup

To set the environment, clone the repository and install the required dependencies by running the following commands:

```
$ git clone httpshttps://huggingface.co/datasets/upstage/document-parse-benchmark.git
$ cd document-parse-benchmark
$ pip install -r requirements.txt
```
The repository includes necessary scripts for performing inference and evaluation of document parsers. 

### Dataset
The benchmark dataset can be found in the `dataset` folder. 
It contains a wide range of document layouts, from text-heavy pages to complex tables, enabling a thorough evaluation of the parser’s performance. 
The dataset comes with annotations for layout elements such as paragraphs, headings, and tables.


### Element detection and serialization evaluation
This evaluation will compute the NID metric to assess how accurately the text in the document is recognized considering the structure and order of the document layout.
To evaluate the document layout results, run the following command:

```
$ python evaluate.py \
  --label_path <path to the reference json file> \
  --pred_path <path to the predicted json file> \
  --mode layout
```


### Table structure recognition evaluation
This will compute TEDS-S (structural accuracy) and TEDS (structural and textual accuracy).
To evaluate table recognition performance, use the following command:

```
$ python evaluate.py \
  --label_path <path to the reference json file> \
  --pred_path <path to the predicted json file> \
  --mode table
```

# Leaderboard
<div style="width: 800px;">
  
| Source               | Date      | TEDS       | TEDS-S    | NID         |  Avg. Time  |
|:--------------------:|:---------:|:----------:|:---------:|:-----------:|:-----------:|
| aws                  | 24.09.26  | 86.39      | 90.22     | 95.94       |  14.47      |
| llamaparse           | 24.09.26  | 68.9       | 70.86     | 90.92       |  4.14       |
| unstructured         | 24.09.26  | 64.49      | 69.9      | 90.42       |  13.14      |
| google               | 24.09.26  | 62.44      | 68.75     | 90.09       |  5.85       |
| microsoft            | 24.09.26  | 85.54      | 89.07     | 87.03       |  4.44       |
| upstage              | 24.09.26  | 91.01      | 93.47     | 96.27       |  3.79       |

</div>