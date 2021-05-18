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


if __name__ == '__main__':
    # TODO: print partition table info
    # TODO: refactor code below
    args = setup()
    print("===================================================================================")
    print("Arguments: ")
    print(args.filename, args.mbr_sector_size, args.sector_nr)
    mbr_data = MbrPartitionTable.from_file(args.filename)
    MBR_SECTOR_SIZE = args.mbr_sector_size
    START_SECTOR = args.sector_nr

    last_part_start = 0
    main_partition = mbr_data.partitions[0]
    for id, partition in enumerate(mbr_data.partitions):
        if partition.lba_start != 0:
            if START_SECTOR < partition.lba_start:
                main_partition = mbr_data.partitions[id]
            last_part_start = partition.lba_start

    partition_offset = MBR_SECTOR_SIZE * main_partition.lba_start
    io = mbr_data._io
    io.seek(partition_offset)
    vfat_partition = Vfat(io)
    fat_proxy = FATProxy(vfat_partition.fats(partition_offset).records)
    filesystem_offset = partition_offset + vfat_partition.boot_sector.pos_root_dir
    bytes_per_cluster = vfat_partition.boot_sector.bpb.bytes_per_ls * vfat_partition.boot_sector.bpb.ls_per_clus
    files = Filesystem(fat_proxy, filesystem_offset, bytes_per_cluster, io)

    start_sector_in_bytes = START_SECTOR * MBR_SECTOR_SIZE
    searching_cluster = -1
    sectorpercluster = vfat_partition.boot_sector.bpb.ls_per_clus
    bytespersector = vfat_partition.boot_sector.bpb.bytes_per_ls
    clusters_in_partition = main_partition.num_sectors // 8
    i = 0
    while i < clusters_in_partition:
        i += 1
        if filesystem_offset + sectorpercluster * bytespersector * i > start_sector_in_bytes:
            searching_cluster = 1 + i
            break

    if searching_cluster == -1:
        print('Error, couldn\'t find cluster for picked sector')
    else:
        start_cluster_of_searching_file = fat_proxy.get_first_cluster(searching_cluster)

        for file in files._files_list:
            if not file.long_filename and  \
               file.start_file_in_cluster == start_cluster_of_searching_file:
                print('==================')
                print(file)
                break
