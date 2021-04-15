# %%

from kaitai_generated.vfat import Vfat
from kaitai_generated.mbr_partition_table import MbrPartitionTable

MBR_SECTOR_SIZE = 512

mbr_data = MbrPartitionTable.from_file('noobs1gb.img')

for partition in mbr_data.partitions:
    if partition.lba_start != 0:
        io = mbr_data._io
        io.seek(MBR_SECTOR_SIZE * partition.lba_start)
        vfat_partition = Vfat(io)
        print(f'Is FAT32 {vfat_partition.boot_sector.is_fat32}')
        print(f'OEM Name: {vfat_partition.boot_sector.oem_name}')

        print(f'FAT position {vfat_partition.boot_sector.pos_fats}')
        print(f'Number of FAT records: {len(vfat_partition.fats)}')

        print(f'Sectors per cluster: {vfat_partition.boot_sector.bpb.ls_per_clus}')
        print(f'List of root-contained directories: {vfat_partition.root_dir.records}')
        print(f'Root dir offset: {vfat_partition.boot_sector.pos_root_dir}')
        print(f'Root dir size: {vfat_partition.boot_sector.size_root_dir}')