import argparse

from src.utils import read_file, check_data_validity
from src.layout_evaluation import evaluate_layout
from src.table_evaluation import evaluate_table


def parse_args():
    parser = argparse.ArgumentParser(description="Arguments for evaluation")
    parser.add_argument(
        "--label_path",
        type=str, required=True,
        help="Path to the ground truth file"
    )
    parser.add_argument(
        "--pred_path",
        type=str, required=True,
        help="Path to the prediction file"
    )
    parser.add_argument(
        "--ignore_classes_for_layout",
        type=list, default=["figure", "table", "chart"],
        help="List of layout classes to ignore. This is used only for layout evaluation."
    )
    parser.add_argument(
        "--mode",
        type=str, default="layout",
        help="Mode for evaluation (layout/table)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("Arguments:")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")
    print("-" * 50)

    label_data = read_file(args.label_path)
    pred_data = read_file(args.pred_path)

    check_data_validity(label_data, pred_data)

    if args.mode == "layout":
        score = evaluate_layout(
            label_data, pred_data,
            ignore_classes=args.ignore_classes_for_layout,
        )
        print(f"NID Score: {score:.4f}")
    elif args.mode == "table":
        teds_score, teds_s_score = evaluate_table(label_data, pred_data)
        print(f"TEDS Score: {teds_score:.4f}")
        print(f"TEDS-S Score: {teds_s_score:.4f}")
    else:
        raise ValueError(f"{args.mode} mode not supported")


if __name__ == "__main__":
    main()
