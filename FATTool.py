# %%

from kaitai_generated.vfat import Vfat
from kaitai_generated.mbr_partition_table import MbrPartitionTable
from utilities import FATProxy

MBR_SECTOR_SIZE = 512

# mbr_data = MbrPartitionTable.from_file('noobs1gb.img')
mbr_data = MbrPartitionTable.from_file('pen.dd')

# %%

for partition in mbr_data.partitions:
    if partition.lba_start != 0:
        io = mbr_data._io
        io.seek(MBR_SECTOR_SIZE * partition.lba_start)
        vfat_partition = Vfat(io)

        # fat_proxy = FATProxy(vfat_partition.fats.records)

        print(f'Is FAT32 {vfat_partition.boot_sector.is_fat32}')
        print(f'OEM Name: {vfat_partition.boot_sector.oem_name}')
        print(f'Sectors per cluster: {vfat_partition.boot_sector.bpb.ls_per_clus}')
        print(f'Bytes per sector: {vfat_partition.boot_sector.bpb.bytes_per_ls}')

        print(f'FAT offset {vfat_partition.boot_sector.pos_fats}')
        print(f'FAT size (B): {vfat_partition.boot_sector.size_fat}')

        # FAT32 treats root like a standard directory - thus below will unfortunately not work
        print(f'List of root-contained directories: {vfat_partition.root_dir.records}')
        # As above always 0 for FAT32
        print(f'Root dir size in sectors: {vfat_partition.boot_sector.ls_per_root_dir}')
        print(f'Root dir size: {vfat_partition.boot_sector.size_root_dir}')
        print(f'Root dir offset: {vfat_partition.boot_sector.pos_root_dir}')
# %%
