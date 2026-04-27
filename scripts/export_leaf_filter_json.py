from __future__ import annotations

import sys
from pathlib import Path

from grok_x_lead_monitor.leaf_filter import export_leaf_filter_json


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: .venv/bin/python scripts/export_leaf_filter_json.py <input.csv> <output.json>", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    export_leaf_filter_json(input_path, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
