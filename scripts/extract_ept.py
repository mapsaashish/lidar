"""Extract an EPSG:3857 bounding box from Palm Beach County EPT to LAZ using PDAL."""
import argparse
import json
import subprocess
from pathlib import Path

EPT_URL = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ept.json"

def main():
    parser = argparse.ArgumentParser(description="Extract a full-resolution EPT subset into compressed LAZ")
    for name in ("xmin", "ymin", "xmax", "ymax"):
        parser.add_argument("--" + name, type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.xmin >= args.xmax or args.ymin >= args.ymax:
        parser.error("Required: xmin < xmax and ymin < ymax")
    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    pipeline = {"pipeline": [
        {"type": "readers.ept", "filename": EPT_URL,
         "bounds": f"([{args.xmin}, {args.xmax}], [{args.ymin}, {args.ymax}])"},
        {"type": "writers.las", "filename": str(target), "compression": "laszip"}
    ]}
    config = target.with_suffix(".pipeline.json")
    config.write_text(json.dumps(pipeline, indent=2), encoding="utf-8")
    print(f"Running PDAL pipeline from {config}")
    subprocess.run(["pdal", "pipeline", str(config)], check=True)
    print(f"Created {target}")

if __name__ == "__main__":
    main()
