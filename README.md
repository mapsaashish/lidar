# USGS Palm Beach County EPT LiDAR

Dataset: **USGS LPC FL PalmBeachCo 2016 LAS 2019**

Public EPT endpoint:
https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ept.json

This repository contains documentation and extraction code, not the full LiDAR point cloud. Dataset metadata reports approximately 75.6 billion points, using LASzip encoding and EPSG:3857.

## Download the complete EPT dataset to Windows (no admin rights)

This mirrors **all EPT objects** (including ept.json, ept-data, ept-hierarchy, ept-sources). It is **not** the original USGS raw LAZ survey-tile layout.

Install Python if necessary, then in Windows CMD:

    python -m venv T:\lidar_env
    T:\lidar_env\Scripts\python.exe -m pip install boto3

Download or clone this repository. From the repository root, preview the total object count, download size and remaining disk space:

    T:\lidar_env\Scripts\python.exe scripts\download_full_palmbeach_ept.py

Test a small number of files:

    T:\lidar_env\Scripts\python.exe scripts\download_full_palmbeach_ept.py --download --max-files 5

Download the **entire public EPT project** to T:\LiDAR\PalmBeach\EPT:

    T:\lidar_env\Scripts\python.exe scripts\download_full_palmbeach_ept.py --download

Interrupted transfers retain *.part files; rerun exactly the same full command to resume. Re-running checks file sizes and skips matching completed downloads. The script uses unsigned S3 access, so there is no AWS account or Requester Pays requirement. Free disk space must exceed the remaining download size plus 1 GiB.

If you already have AWS CLI installed, the equivalent is:

    aws s3 sync s3://usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ T:\LiDAR\PalmBeach\EPT\ --no-sign-request --region us-west-2

**Important:** EPT LAZ files are spatial octree tiles, not the original survey LAZ files. For original raw LAZ source tiles, use the separately hosted USGS original downloads or the Requester Pays AWS bucket. Do not add downloaded point cloud data to Git.

## Extract an area of interest to LAZ

Install PDAL using Conda:

```cmd
conda create -n lidar -c conda-forge pdal
conda activate lidar
```

Run from this repository in Windows CMD, using **EPSG:3857 coordinates in metres**:

```cmd
python scripts\extract_ept.py --xmin XMIN --ymin YMIN --xmax XMAX --ymax YMAX --output "T:\LiDAR\PalmBeach\subset.laz"
```

All bounds must be specified. The script downloads the full-resolution EPT points intersecting the rectangular extent and writes a compressed LAZ. A rectangle may include points outside the county boundary. For an entire county, process smaller areas separately and clip to an authoritative county polygon. Check disk capacity before extracting large areas.

## Inspect the remote dataset

```cmd
aws s3 ls s3://usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ --no-sign-request
```

Do not sync the entire EPT folder unless you intend to store the entire indexed dataset locally. Original survey metadata may be separate from EPT.

## References

* [AWS Open Data USGS LiDAR](https://registry.opendata.aws/usgs-lidar/)
* [EPT metadata](https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ept.json)
