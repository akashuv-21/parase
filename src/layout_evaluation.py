from rapidfuzz import fuzz

def calc_nid(
    gt_text : list,
    pred_text : list,
) -> float:
    """Calculate the Normalized InDel score between the gt and pred text.

    Args:
        gt_text (str): The string of gt text to compare.
        pred_text (str): The string of pred text to compare.

    Returns:
        float: The nid score between gt and pred text.
    """

    # if gt and pred is empty, return 1
    if len(gt_text) == 0 and len(pred_text) == 0:
        score = 1
    # if pred is empty while gt is not, return 0
    elif len(gt_text) > 0 and len(pred_text) == 0:
        score = 0
    else:
        score = fuzz.ratio(gt_text, pred_text)

    return score


def extract_text(
    data : dict,
    ignore_classes : list = [],
    strings_to_remove : list = ["\n"],
) -> str:
    """Extract text from the dictionary data.

    Args:
        data (dict): The data to extract text from.
        ignore_classes (list): A list of classes to ignore during extraction.
        strings_to_remove (list): A list of strings to remove from the extracted text.

    Returns:
        str: The concatenated text extracted from the data.
    """

    ignore_classes = [x.lower() for x in ignore_classes]

    concatenated_text = ""

    for elem in data["elements"]:
        if elem["category"].lower() in ignore_classes:
            continue

        concatenated_text += elem["content"]["text"] + ' '

    # remove unwanted strings
    for string in strings_to_remove:
        concatenated_text = concatenated_text.replace(string, '')

    return concatenated_text


def evaluate_layout(
    gt : dict,
    pred : dict,
    ignore_classes : list = [],
) -> float:
    """Evaluate the layout of the gt against the pred.

    Args:
        gt (dict): The gt layout to evaluate.
        pred (dict): The pred layout to evaluate against.
        ignore_classes (list): A list of classes to ignore during evaluation.

    Returns:
        float: The layout evaluation score.
    """
    scores = []
    for image_key in gt.keys():
        gt_data = gt.get(image_key)
        pred_data = pred.get(image_key)

        gt_text = extract_text(gt_data, ignore_classes)
        pred_text = extract_text(pred_data, ignore_classes)

        score = calc_nid(gt_text, pred_text)

        scores.append(score)

    if len(scores) > 0:
        avg_score = sum(scores) / (len(scores) * 100)
    else:
        avg_score = 0

    return avg_score
