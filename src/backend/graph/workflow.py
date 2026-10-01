from __future__ import annotations

import argparse
from pathlib import Path

from backend.domain.graph.workflow import save_graph_visualization


def main() -> None:
    parser = argparse.ArgumentParser(description="Export graph visualization")
    parser.add_argument(
        "--out",
        type=str,
        default="docs/agent_graph.png",
        help="Path to save the graph visualization",
    )
    args = parser.parse_args()

    saved_path = save_graph_visualization(args.out)
    print(f"Graph visualization saved to: {saved_path}")


if __name__ == "__main__":
    main()
