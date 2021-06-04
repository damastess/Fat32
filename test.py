# TODO: remove when not needed anymore
# %%
# %%
from kaitai_generated.vfat import Vfat
from kaitai_generated.mbr_partition_table import MbrPartitionTable
from utilities import FATProxy, Filesystem

MBR_SECTOR_SIZE = 512

# mbr_data = MbrPartitionTable.from_file('noobs1gb.img')
mbr_data = MbrPartitionTable.from_file('pen.dd')

for partition in mbr_data.partitions:
    if partition.lba_start != 0:
        partition_offset = MBR_SECTOR_SIZE * partition.lba_start
        io = mbr_data._io
        io.seek(partition_offset)
        vfat_partition = Vfat(io)

        fat_proxy = FATProxy(vfat_partition.fats(partition_offset).records)
        filesystem_offset = partition_offset + vfat_partition.boot_sector.pos_root_dir

        bytes_per_cluster = vfat_partition.boot_sector.bpb.bytes_per_ls * vfat_partition.boot_sector.bpb.ls_per_clus
        files = Filesystem(fat_proxy, filesystem_offset, bytes_per_cluster, io)

        print(f'Is FAT32 {vfat_partition.boot_sector.is_fat32}')
        print(f'OEM Name: {vfat_partition.boot_sector.oem_name}')
        print(f'Sectors per cluster: {vfat_partition.boot_sector.bpb.ls_per_clus}')
        print(f'Bytes per sector: {vfat_partition.boot_sector.bpb.bytes_per_ls}')

        print(f'Partition start offset: {hex(partition_offset)}')
        print(f'FAT offset {hex(partition_offset + vfat_partition.boot_sector.pos_fats)}')
        print(f'FAT size (B): {hex(vfat_partition.boot_sector.size_fat)}')
        print(f'Root dir offset: {hex(filesystem_offset)}')

        for file in files._files_list:
            print(file)
            # for name, value in file.__dict__.items():
            #     print(name, value)
