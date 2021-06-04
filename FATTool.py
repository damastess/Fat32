from kaitai_generated.mbr_partition_table import MbrPartitionTable
from kaitai_generated.vfat import Vfat
from utilities import FATProxy, Filesystem
import argparse


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest='filename',
        help='file containing the filesystem')
    parser.add_argument(
        dest='sector_nr', type=int,
        help='sector number, relative to the image beginning')
    parser.add_argument(
        '-s', '--size', dest='mbr_sector_size', type=int,
        default=512, help='sector size in bytes')
    args = parser.parse_args()

    return args


def buildMBRDataFromDiscImage(_filename, _start_sector):
    """
    Builder for MBR data and partitions objects.
    :param _filename: disk image filename
    :param _start_sector: input sector
    :return: mbr_data object, main_partition
    """
    mbr_data = MbrPartitionTable.from_file(_filename)
    main_partition = mbr_data.partitions[0]
    for id, partition in enumerate(mbr_data.partitions):
        print("Partition id: " + str(id))
        print(partition)
        if partition.lba_start != 0:
            if _start_sector < partition.lba_start:
                main_partition = mbr_data.partitions[id]
    return mbr_data, main_partition


def analyzeFileSystem(_mbr_sector_size, _mbr_data, _main_partition, _sector_number):
    """
    Analyze file system on disc image in purpose for obtainment files list and cluster (number) which
    contain sector given by user.
    :param _mbr_sector_size: Sector size for MBR
    :param _mbr_data: MBR data object
    :param _main_partition: workspace partition
    :param _sector_number: input sector
    :return: fat_proxy object, files - list of files, searching_cluster
    """
    partition_offset = _mbr_sector_size * _main_partition.lba_start
    io = _mbr_data.getIO()
    io.seek(partition_offset)
    vfat_partition = Vfat(io)

    filesystem_offset = partition_offset + vfat_partition.boot_sector.pos_root_dir
    bytes_per_cluster = vfat_partition.boot_sector.bpb.bytes_per_ls * vfat_partition.boot_sector.bpb.ls_per_clus
    fat_proxy = FATProxy(vfat_partition.fats(partition_offset).records)
    files = Filesystem(fat_proxy, filesystem_offset, bytes_per_cluster, io)

    start_sector_in_bytes = _sector_number * _mbr_sector_size
    sectorpercluster = vfat_partition.boot_sector.bpb.ls_per_clus
    bytespersector = vfat_partition.boot_sector.bpb.bytes_per_ls
    clusters_in_partition = _main_partition.num_sectors // 8

    i = 0
    searching_cluster = -1
    while i < clusters_in_partition:
        i += 1
        if filesystem_offset + sectorpercluster * bytespersector * i > start_sector_in_bytes:
            searching_cluster = 1 + i
            break
    return fat_proxy, files, searching_cluster


def fileFinder(_input_sector_cluster, _files, _fat_proxy):
    """
    The main task is to search for the file.
    :param _input_sector_cluster: Cluster which contain sector given by user
    :param _files: list of files
    :param _fat_proxy: fat32 filesystem proxy
    :return: file - FileRec object with info about searching file
    """
    if _input_sector_cluster == -1:
        print('Error, couldn\'t find cluster for picked sector')
    else:
        start_cluster_of_searching_file = _fat_proxy.get_first_cluster(_input_sector_cluster)
        for file in _files.getFilesList():
            if not file.long_filename and file.file_first_cluster_nr == start_cluster_of_searching_file:
                return file


if __name__ == '__main__':
    args = setup()
    print("======================================================================\n"
          "====================          FAT32 Tool          ====================\n"
          "======================================================================\n")
    print("Input arguments: ")
    print(args.filename, args.mbr_sector_size, args.sector_nr)
    print("=====================Start processing data, please wait...\n")

    mbr_data, main_partition = buildMBRDataFromDiscImage(args.filename, args.sector_nr)

    fat_proxy, files, input_sector_cluster = analyzeFileSystem(args.mbr_sector_size, mbr_data, main_partition, args.sector_nr)

    founded_file = fileFinder(input_sector_cluster, files, fat_proxy)

    if not founded_file:
        print("=====================Error:"
              "Tool couldn't find file with input parameters on given disc image.\n"
              "Validate the given sector and try again.\n")
    else:
        print("=====================Found file:")
        print(founded_file)
