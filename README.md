# What is this?

This repo contains a crude implementation of a tool created as a part
of an assignment during computer forensics course, extracting file
metadata based on the user-provided sector contained by the file.
Currently (possibly ever) only FAT32 partition format, along with
basic (no extended partitions) MBR partition table format is supported.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install required packages:

```bash
pip install -r requirements.txt
```

## Usage

To use this tool, follow these steps:

```bash
python FATTool.py [-h] [-s] filename sector_nr
```

where:
* `-h` - display help

* `-s` - sector size (512 by default)

Example:
```bash
python FATTool.py -s 512 image.dd 6200
```

## What it does

* Reads partition table (only MBR with standard partition type is supported)

* Checks if partition containing selected sector is formatted according to FAT32,
  then reads partition info recreating file allocation table as a two way list

* Calculates cluster number containing the selected sector, retrieves first file
  sector and traverses directory tree finding a corresponding file metadata