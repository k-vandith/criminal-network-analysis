"""Small CLI for validating an interaction CSV without launching the UI."""
from __future__ import annotations

import argparse

import pandas as pd

from .core import analyze, build_from_interactions, graph_stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and summarize a LinkLens interaction CSV")
    parser.add_argument("csv", nargs="?", help="CSV with source and target columns")
    parser.add_argument("--source", default="source", help="Source entity column (default: source)")
    parser.add_argument("--target", default="target", help="Target entity column (default: target)")
    args = parser.parse_args()
    if not args.csv:
        parser.print_help()
        return
    frame = pd.read_csv(args.csv)
    bundle = build_from_interactions(frame, args.source, args.target, source_label=args.csv)
    print("LinkLens network summary")
    for key, value in graph_stats(bundle).items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    print("\nTop entities by structural review priority:")
    print(analyze(bundle)["metrics"][["name", "direct_links", "bridge_links", "review_priority"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
