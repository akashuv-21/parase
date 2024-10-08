"""
Most of the code in this file is derived from the paper "Image-based table recognition: data, model, and evaluation".
The original paper can be accessed at: https://arxiv.org/pdf/1911.10683.
The code is available at: https://github.com/ibm-aur-nlp/PubTabNet.
A slight modification has been added to the code to improve the evaluation process.
"""

import distance

from bs4 import BeautifulSoup

from lxml import etree, html
from collections import deque
from apted.helpers import Tree
from apted import APTED, Config


class TableTree(Tree):
    """Table Tree class for APTED"""
    def __init__(self, tag, colspan=None, rowspan=None, content=None, *children):
        self.tag = tag
        self.colspan = colspan
        self.rowspan = rowspan
        self.content = content
        self.children = list(children)

    def bracket(self):
        """Show tree using brackets notation"""
        if self.tag == 'td':
            result = '"tag": %s, "colspan": %d, "rowspan": %d, "text": %s' % \
                     (self.tag, self.colspan, self.rowspan, self.content)
        else:
            result = '"tag": %s' % self.tag
        for child in self.children:
            result += child.bracket()
        return "{{{}}}".format(result)


class CustomConfig(Config):
    """Custom Configuration for APTED"""
    @staticmethod
    def maximum(*sequences):
        """Get maximum possible value"""
        return max(map(len, sequences))

    def normalized_distance(self, *sequences):
        """Get distance from 0 to 1"""
        return float(distance.levenshtein(*sequences)) / self.maximum(*sequences)

    def rename(self, node1, node2):
        """Compares attributes of trees"""
        if (node1.tag != node2.tag) or \
                (node1.colspan != node2.colspan) or \
                (node1.rowspan != node2.rowspan):
            return 1.
        if node1.tag == 'td':
            if node1.content or node2.content:
                return self.normalized_distance(
                    node1.content, node2.content
                )
        return 0.


class TEDSEvaluator(object):
    """Tree Edit Distance basead Similarity"""
    def __init__(self, structure_only=False, n_jobs=1, ignore_nodes=None):
        assert isinstance(n_jobs, int) and (n_jobs >= 1), (
            'n_jobs must be an integer greather than 1'
        )
        self.structure_only = structure_only
        self.n_jobs = n_jobs
        self.ignore_nodes = ignore_nodes
        self.__tokens__ = []

    def tokenize(self, node):
        """Tokenizes table cells"""
        self.__tokens__.append('<%s>' % node.tag)
        if node.text is not None:
            self.__tokens__ += list(node.text)
        for n in node.getchildren():
            self.tokenize(n)
        if node.tag != 'unk':
            self.__tokens__.append('</%s>' % node.tag)
        if node.tag != 'td' and node.tail is not None:
            self.__tokens__ += list(node.tail)

    def load_html_tree(self, node, parent=None):
        """Converts HTML tree to the format required by apted"""
        global __tokens__
        if node.tag == 'td':
            if self.structure_only:
                cell = []
            else:
                self.__tokens__ = []
                self.tokenize(node)
                cell = self.__tokens__[1:-1].copy()
            new_node = TableTree(
                node.tag,
                int(node.attrib.get('colspan', '1')),
                int(node.attrib.get('rowspan', '1')),
                cell, *deque()
            )
        else:
            new_node = TableTree(node.tag, None, None, None, *deque())
        if parent is not None:
            parent.children.append(new_node)
        if node.tag != 'td':
            for n in node.getchildren():
                self.load_html_tree(n, new_node)
        if parent is None:
            return new_node

    def evaluate(self, pred, true):
        """Computes TEDS score between the prediction and the ground truth of a given sample"""
        if (not pred) or (not true):
            return 0.0
        parser = html.HTMLParser(remove_comments=True, encoding='utf-8')
        pred = html.fromstring(pred, parser=parser)
        true = html.fromstring(true, parser=parser)

        if pred.xpath('body/table') and true.xpath('body/table'):
            pred = pred.xpath('body/table')[0]
            true = true.xpath('body/table')[0]
            if self.ignore_nodes:
                etree.strip_tags(pred, *self.ignore_nodes)
                etree.strip_tags(true, *self.ignore_nodes)
            n_nodes_pred = len(pred.xpath('.//*'))
            n_nodes_true = len(true.xpath('.//*'))
            n_nodes = max(n_nodes_pred, n_nodes_true)
            tree_pred = self.load_html_tree(pred)
            tree_true = self.load_html_tree(true)
            distance = APTED(tree_pred, tree_true, CustomConfig()).compute_edit_distance()
            return 1.0 - (float(distance) / n_nodes)
        else:
            return 0.0


def remove_table_tags(html_text : str) -> str:
    """Remove the <table> tags from the html text.

    Args:
        html_text (str): The html text to remove the <table> tags from.
    Returns:
        str: The html text without the <table> tags.
    """
    if "<table>" not in html_text:
        return html_text

    soup = BeautifulSoup(html_text, 'html.parser')

    # Get contents of the <tbody> tag
    table_contents = ''
    for tag in soup.table.find_all(recursive=False):
        table_contents += str(tag)

    return table_contents


def extract_tables(
    data : dict, is_pred_data : bool = False
) -> str:
    """Extract tables from the dictionary data.

    Args:
        data (dict): The data to extract tables from.

    Returns:
        str: The extracted tables from the data and a boolean indicating if the data has a table.
    """

    # return as is if data is a string
    html = '<html><body>'
    for elem in data['elements']:
        if elem['category'].lower() == 'table':
            if is_pred_data:
                table_html = remove_table_tags(elem['content']['html'])
            else:
                table_html = elem['content']['html']

            html += f'<table>{table_html}</table>'
    html += '</body></html>'

    return html


def has_table_content(html_data : str) -> bool:
    """Check if the table has content between <html><body> and </body></html>.

    Args:
        html_data (str): The html data to check.
    Returns:
        bool: True if the table has content, False otherwise
    """
    has_content = True
    if html_data.replace('<html><body>', '').replace('</body></html>', '') == '':
        has_content = False

    return has_content


def prepare_table_dataset(gt_data, pred_data):
    """Prepare the tables for evaluation.
    Args:
        gt_data (dict): The ground truth dataset to evaluate.
        pred_data (dict): The predicted dataset to evaluate.

    Returns:
        tuple (list, list): The list of ground truth and predicted tables.
    """

    gt_table_list = []
    pred_table_list = []
    for image_key in gt_data.keys():

        gt_elem = gt_data.get(image_key)
        pred_elem = pred_data.get(image_key)

        gt_tables = extract_tables(gt_elem)
        pred_tables = extract_tables(pred_elem, is_pred_data=True)

        if not has_table_content(gt_tables):
            continue

        gt_table_list.append(gt_tables)
        pred_table_list.append(pred_tables)

    return gt_table_list, pred_table_list


def calc_table_score(gt_string, pred_string, evaluator):
    """Calculate the table evaluation score between the gold and pred strings.

    Args:
        gt_string (str): The ground truth html string to compare.
        pred_string (str): The predicted html string to compare.
        evaluator (TEDS/TEDS-S): The TEDS/TEDS-S evaluator to use.
    Returns:
        float: The table evaluation score.
    """
    refined_pred = pred_string
    refined_gold = gt_string
    if pred_string.startswith('<table>') and pred_string.endswith('</table>'):
        refined_pred = '<html><body>' + pred_string + '</body></html>'
    elif not pred_string.startswith('<html><body><table>') and not pred_string.endswith('</table></body></html>'):
        refined_pred = '<html><body><table>' + refined_pred + '</table></body></html>'

    if gt_string.startswith('<table>') and gt_string.endswith('</table>'):
        refined_gold = '<html><body>' + gt_string + '</body></html>'
    elif not gt_string.startswith('<html><body><table>') and not gt_string.endswith('</table></body></html>'):
        refined_gold = '<html><body><table>' + refined_gold + '</table></body></html>'

    # remove thead and tbody
    for tok in ['<thead>', '</thead>', '<tbody>', '</tbody>']:
        refined_pred = refined_pred.replace(tok, '')
        refined_gold = refined_gold.replace(tok, '')

    score = evaluator.evaluate(refined_pred, refined_gold)

    return score


def evaluate_table(
    gt : dict,
    pred : dict
) -> tuple:
    """Evaluate the table of the gt against the pred.

    Args:
        gt (dict): The gt layout to evaluate.
        pred (dict): The pred layout to evaluate against.

    Returns:
        tuple(float, float): The TEDS and TEDS-S scores for the table evaluation.
    """

    gt_table_list, pred_table_list = prepare_table_dataset(gt, pred)

    avg_teds_score = 0.0
    avg_teds_s_score = 0.0

    if len(gt_table_list) == 0:
        print('[Warning] No tables found in the ground truth dataset.')
    elif len(pred_table_list) == 0:
        print('[Warning] No tables found in the prediction dataset.')
    else:
        # Construct Table Evaluator for TEDS
        # TEDS only evaluates the structure of the table
        table_evaluator = TEDSEvaluator(structure_only=True)
        teds_s_scores = []
        for gt_table_elem, pred_table_elem in zip(gt_table_list, pred_table_list):
            teds_s_score = calc_table_score(gt_table_elem, pred_table_elem, table_evaluator)
            teds_s_scores.append(teds_s_score)
        avg_teds_s_score= sum(teds_s_scores) / len(teds_s_scores)

        # Construct Table Evaluator for TEDS-S
        # TEDS-S evaluates the structure and content of the table
        table_evaluator = TEDSEvaluator(structure_only=False)
        teds_scores = []
        for gt_table_elem, pred_table_elem in zip(gt_table_list, pred_table_list):
            teds_score = calc_table_score(gt_table_elem, pred_table_elem, table_evaluator)
            teds_scores.append(teds_score)
        avg_teds_score = sum(teds_scores) / len(teds_scores)

    return avg_teds_score, avg_teds_s_score
