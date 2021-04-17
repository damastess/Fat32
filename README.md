# Fat32

This is a student implementation of a tool used to return metadata information about the file that contains selected disc sector.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install required packages:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python FATTool.py [-h] [-s] __filename__ __sector_nr__
```

## What it does

* Reads partition table (only MBR with standard partition type is supported)

* Checks if partition containing selected sector is formatted according to FAT32,
  then reads partition info recreating file allocation table as a two way list

* Calculates cluster number containing the selected sector, retrieves first file
  sector and traverses directory tree finding a corresponding file metadata