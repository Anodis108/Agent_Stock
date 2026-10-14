from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT_DIR = next((p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()), Path(__file__).resolve().parents[4])
_SRC_DIR = str(_ROOT_DIR / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


from backend.domain.graph.workflow import save_graph_visualization


def main() -> None:
    parser = argparse.ArgumentParser(description="Export graph visualization")
    parser.add_argument(
        "--out",
        type=str,
        default="resources/docs/agent_graph.png",
        help="Path to save the graph visualization",
    )
    args = parser.parse_args()

    saved_path = save_graph_visualization(args.out)
    print(f"Graph visualization saved to: {saved_path}")


if __name__ == "__main__":
    main()
