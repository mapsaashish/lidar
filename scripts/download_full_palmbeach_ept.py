"""Download all public Palm Beach County USGS EPT objects from AWS.
No AWS login, administrator rights or PDAL needed. Requires boto3.
The downloader resumes partial files and verifies their byte counts.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path, PurePosixPath

BUCKET = "usgs-lidar-public"
PREFIX = "USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/"
REGION = "us-west-2"
CHUNK = 8 * 1024 * 1024


def human_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:,.2f} {unit}"
        value /= 1024
    return f"{value:,.2f} PiB"


def make_client():
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config
    except ImportError:
        sys.exit("Install boto3 first: python -m pip install boto3")
    return boto3.client(
        "s3", region_name=REGION,
        config=Config(signature_version=UNSIGNED, max_pool_connections=16,
                      retries={"max_attempts": 10, "mode": "standard"}),
    )


def list_remote(client):
    objects = []
    pages = client.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX)
    for page in pages:
        for item in page.get("Contents", []):
            key = item["Key"]
            relative = key[len(PREFIX):]
            if not relative or key.endswith("/"):
                continue
            parts = PurePosixPath(relative).parts
            if any(part in (".", "..") for part in parts) or relative.startswith("/"):
                raise ValueError(f"Unsafe S3 key: {key}")
            objects.append((key, Path(*parts), int(item["Size"])))
    return objects


def file_progress(root: Path, relative: Path, length: int):
    destination = root / relative
    if destination.exists() and destination.stat().st_size == length:
        return 0, True
    part = Path(str(destination) + ".part")
    if part.exists() and part.stat().st_size <= length:
        return length - part.stat().st_size, False
    return length, False


def download_one(client, root: Path, job):
    key, relative, length = job
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == length:
        return "skipped"
    part = Path(str(destination) + ".part")
    last_error = None
    for attempt in range(1, 6):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset > length:
                part.unlink()
                offset = 0
            if offset == length:
                part.replace(destination)
                return "downloaded"
            kwargs = {"Bucket": BUCKET, "Key": key}
            if offset:
                kwargs["Range"] = f"bytes={offset}-"
            response = client.get_object(**kwargs)
            body = response["Body"]
            try:
                if offset:
                    content_range = response.get("ContentRange", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        raise IOError("Server did not confirm the requested byte range")
                if int(response["ContentLength"]) != length - offset:
                    raise IOError("Unexpected response length; file may have changed")
                with part.open("ab" if offset else "wb") as output:
                    for data in body.iter_chunks(chunk_size=CHUNK):
                        if data:
                            output.write(data)
            finally:
                body.close()
            if part.stat().st_size != length:
                raise IOError("Downloaded size does not match AWS object size")
            part.replace(destination)
            return "downloaded"
        except Exception as exc:
            last_error = exc
            if attempt < 5:
                time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"{relative}: {last_error}")


def run(args):
    root = Path(args.output).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    print(f"AWS: s3://{BUCKET}/{PREFIX}", flush=True)
    print(f"Local destination: {root}", flush=True)
    client = make_client()
    print("Listing ALL project objects and sizes from AWS...", flush=True)
    jobs = list_remote(client)
    if not jobs:
        sys.exit("No files returned. Verify bucket access and project prefix.")

    total = sum(job[2] for job in jobs)
    remaining = 0
    complete = 0
    for _, relative, length in jobs:
        needed, done = file_progress(root, relative, length)
        remaining += needed
        complete += int(done)
    available = shutil.disk_usage(root).free
    print(f"Total: {len(jobs):,} objects, {human_size(total)}")
    print(f"Completed: {complete:,} files")
    print(f"Still needed: approximately {human_size(remaining)}")
    print(f"Disk space free: {human_size(available)}")

    if not args.download:
        print("CHECK ONLY. Run again with --download to fetch ALL files.")
        return 0

    pending = [job for job in jobs if not file_progress(root, job[1], job[2])[1]]
    if args.max_files:
        pending = pending[:args.max_files]
        print(f"TEST MODE: downloading at most {args.max_files} missing files")
    selected_remaining = sum(file_progress(root, job[1], job[2])[0] for job in pending)
    if available < selected_remaining + 1024**3:
        sys.exit("Not enough free disk space. Change --output to a larger drive.")
    if not pending:
        print("All files are present with matching sizes.")
        return 0

    errors = []
    processed = 0
    workers = max(1, min(16, args.workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        active = set()

        def collect_done(done_futures):
            nonlocal processed
            for future in done_futures:
                processed += 1
                try:
                    future.result()
                except Exception as exc:
                    errors.append(str(exc))
                    print(f"ERROR: {exc}", flush=True)
                if processed % 25 == 0 or processed == len(pending):
                    print(f"Finished {processed:,}/{len(pending):,} objects; errors: {len(errors)}", flush=True)

        for job in pending:
            while len(active) >= workers * 2:
                done, active = wait(active, return_when=FIRST_COMPLETED)
                collect_done(done)
            active.add(pool.submit(download_one, client, root, job))
        while active:
            done, active = wait(active, return_when=FIRST_COMPLETED)
            collect_done(done)

    if errors:
        failures = root / "failed_downloads.txt"
        failures.write_text("\n".join(errors) + "\n", encoding="utf-8")
        print(f"{len(errors)} failed. Details: {failures}. Rerun with --download to retry.")
        return 1
    print(f"SUCCESS: downloaded or resumed all selected EPT objects into {root}")
    print("EPT is a spatially indexed collection, not one merged LAZ file.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Download the complete USGS Palm Beach County EPT dataset")
    parser.add_argument("--output", default=r"T:\LiDAR\PalmBeach\EPT", help="Local output directory")
    parser.add_argument("--download", action="store_true", help="Actually download, rather than just check sizes")
    parser.add_argument("--workers", type=int, default=6, help="Parallel S3 transfers (default: 6)")
    parser.add_argument("--max-files", type=int, default=0, help="Optional test limit (0 means ALL)")
    args = parser.parse_args()
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
