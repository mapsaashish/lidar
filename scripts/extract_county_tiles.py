"""Tile the USGS Palm Beach County EPT extent into compressed LAZ files.

Default is a dry run. Use --execute to extract. Bounding rectangles cover the
EPT extent, not the exact Palm Beach County jurisdictional boundary.
"""
import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ept.json"
# EPSG:3857, official conforming bounds from ept.json.
EXTENT = (-9004531, 3038567, -8908435, 3119996)

def main():
    p = argparse.ArgumentParser(description="Extract Palm Beach EPT in small LAZ tiles")
    p.add_argument("--output", default="T:/LiDAR/PalmBeach")
    p.add_argument("--tile-size", type=int, default=1000, help="Tile side length in metres (EPSG:3857)")
    p.add_argument("--execute", action="store_true", help="Actually run PDAL (otherwise preview)")
    p.add_argument("--max-tiles", type=int, default=1, help="Tiles to process; use 0 for entire bounding rectangle")
    p.add_argument("--xmin", type=float)
    p.add_argument("--ymin", type=float)
    p.add_argument("--xmax", type=float)
    p.add_argument("--ymax", type=float)
    args = p.parse_args()
    coords = (args.xmin, args.ymin, args.xmax, args.ymax)
    if any(c is not None for c in coords) and not all(c is not None for c in coords):
        p.error("Specify all four custom extent arguments or none.")
    xmin, ymin, xmax, ymax = EXTENT if coords[0] is None else coords
    if xmin >= xmax or ymin >= ymax or args.tile_size <= 0 or args.max_tiles < 0:
        p.error("Invalid bounds, tile size or maximum tile count.")
    out = Path(args.output)
    nx = math.ceil((xmax - xmin) / args.tile_size)
    ny = math.ceil((ymax - ymin) / args.tile_size)
    total = nx * ny
    limit = total if args.max_tiles == 0 else min(total, args.max_tiles)
    print(f"Grid: {nx} by {ny} = {total} possible tiles. Selected: {limit}.")
    print("NOTE: Bounding extent is NOT a county boundary; some tiles may contain no points.")
    if not args.execute:
        print("DRY RUN. Add --execute to actually download.")
        return
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "extraction_manifest.csv"
    with manifest.open("a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if manifest.stat().st_size == 0:
            wr.writerow(["tile", "status", "xmin", "ymin", "xmax", "ymax"])
        completed = 0
        for iy in range(ny):
            for ix in range(nx):
                if completed >= limit:
                    return
                completed += 1
                x0 = xmin + ix * args.tile_size
                x1 = min(x0 + args.tile_size, xmax)
                y0 = ymin + iy * args.tile_size
                y1 = min(y0 + args.tile_size, ymax)
                name = f"palmbeach_{iy:03d}_{ix:03d}.laz"
                dest = out / name
                if dest.exists() and dest.stat().st_size:
                    print(f"SKIP {name}: already exists")
                    continue
                pipeline = {"pipeline": [
                    {"type": "readers.ept", "filename": EPT,
                     "bounds": f"([{x0}, {x1}], [{y0}, {y1}])"},
                    {"type": "writers.las", "filename": str(dest), "compression": "laszip"}
                ]}
                config = out / f"pipeline_{iy:03d}_{ix:03d}.json"
                config.write_text(json.dumps(pipeline, indent=2), encoding="utf-8")
                print(f"Extract {completed}/{limit}: {name}", flush=True)
                try:
                    subprocess.run(["pdal", "pipeline", str(config)], check=True)
                    status = "complete" if dest.exists() and dest.stat().st_size else "empty"
                except (subprocess.CalledProcessError, OSError) as exc:
                    status = "error"
                    print(f"{name}: {exc}", flush=True)
                wr.writerow([name, status, x0, y0, x1, y1])
                f.flush()

if __name__ == "__main__":
    main()
