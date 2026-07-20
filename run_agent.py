from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physical_agent.config import load_settings
from physical_agent.image_io import write_sample_png
from physical_agent.orchestrator import run_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MVP physical image editing agent.")
    parser.add_argument("--image", type=Path, help="Input PNG image. If omitted, a synthetic sample is created.")
    parser.add_argument(
        "--instruction",
        default="Remove the red ball from the scene and also remove its shadow, keeping the floor and background physically consistent.",
        help="Natural-language edit instruction.",
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()

    image_path = args.image or (ROOT / "data" / "samples" / "red_ball_shadow.png")
    if args.image is None and not image_path.exists():
        write_sample_png(image_path)

    settings = load_settings()
    state = run_agent(settings, image_path.resolve(), args.instruction, args.output_root.resolve())
    print(json.dumps(asdict(state), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
