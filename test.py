# TODO: remove when not needed anymore
# %%

from kaitai_generated.vfat import Vfat
from kaitai_generated.mbr_partition_table import MbrPartitionTable
from utilities import FATProxy, Filesystem

MBR_SECTOR_SIZE = 512

# mbr_data = MbrPartitionTable.from_file('noobs1gb.img')
mbr_data = MbrPartitionTable.from_file('pen.dd')

# %%

for partition in mbr_data.partitions:
    if partition.lba_start != 0:
        io = mbr_data._io
        io.seek(MBR_SECTOR_SIZE * partition.lba_start)
        vfat_partition = Vfat(io)

        fat_proxy = FATProxy(vfat_partition.fats(MBR_SECTOR_SIZE * partition.lba_start).records)
        filesystem_offset = partition.lba_start * MBR_SECTOR_SIZE + vfat_partition.boot_sector.pos_root_dir
        bytes_per_cluster = vfat_partition.boot_sector.bpb.bytes_per_ls * vfat_partition.boot_sector.bpb.ls_per_clus
        files = Filesystem(fat_proxy, filesystem_offset, bytes_per_cluster, io)

        # print(f'Is FAT32 {vfat_partition.boot_sector.is_fat32}')
        # print(f'OEM Name: {vfat_partition.boot_sector.oem_name}')
        # print(f'Sectors per cluster: {vfat_partition.boot_sector.bpb.ls_per_clus}')
        # print(f'Bytes per sector: {vfat_partition.boot_sector.bpb.bytes_per_ls}')

        print(f'FAT offset {partition.lba_start * MBR_SECTOR_SIZE + vfat_partition.boot_sector.pos_fats}')
        print(f'FAT size (B): {vfat_partition.boot_sector.size_fat}')

        print(f'Root dir offset: {partition.lba_start * MBR_SECTOR_SIZE + vfat_partition.boot_sector.pos_root_dir}')
