# USGS Palm Beach County EPT LiDAR

Dataset: **USGS LPC FL PalmBeachCo 2016 LAS 2019**

Public EPT endpoint:
https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_FL_PalmBeachCo_2016_LAS_2019/ept.json

This repository contains documentation and extraction code, not the full LiDAR point cloud. Dataset metadata reports approximately 75.6 billion points, using LASzip encoding and EPSG:3857.

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
