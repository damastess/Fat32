from kaitai_generated.mbr_partition_table import MbrPartitionTable
from kaitai_generated.vfat import Vfat
from utilities import FATProxy
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
    args = setup()
    mbr_data = MbrPartitionTable.from_file(args.filename)

    print(args.filename, args.mbr_sector_size, args.sector_nr)

    for partition in mbr_data.partitions:
        if partition.lba_start != 0:
            io = mbr_data._io
            io.seek(args.mbr_sector_size * partition.lba_start)
            vfat_partition = Vfat(io)

            fat_proxy = FATProxy(vfat_partition.fats(args.mbr_sector_size * partition.lba_start).records)
