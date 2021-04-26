# TODO: remove when not needed anymore
# %%
%load_ext autoreload
%autoreload 2

# %%
from kaitai_generated.vfat import Vfat
from kaitai_generated.mbr_partition_table import MbrPartitionTable
from utilities import FATProxy, Filesystem

MBR_SECTOR_SIZE = 512
START_SECTOR = 16693 #6200

# mbr_data = MbrPartitionTable.from_file('noobs1gb.img')
mbr_data = MbrPartitionTable.from_file('pen.dd')
# mbr_data = MbrPartitionTable.from_file('11-carve-fat.dd')

last_part_start = 0
main_partition = mbr_data.partitions[0]
print(mbr_data.partitions)
for id, partition in enumerate(mbr_data.partitions):
    print("fsssss")
    print(partition.lba_start)
    if partition.lba_start != 0:
        print("asfdsfa")
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
print(f'Is FAT32 {vfat_partition.boot_sector.is_fat32}')
print(f'OEM Name: {vfat_partition.boot_sector.oem_name}')
print(f'Sectors per cluster: {vfat_partition.boot_sector.bpb.ls_per_clus}')
print(f'Bytes per sector: {vfat_partition.boot_sector.bpb.bytes_per_ls}')
print(f'Partition start offset: {hex(partition_offset)}')
print(f'FAT offset {hex(partition_offset + vfat_partition.boot_sector.pos_fats)}')
print(f'FAT size (B): {hex(vfat_partition.boot_sector.size_fat)}')
print(f'Root dir offset: {hex(filesystem_offset)}')
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
    print("Error, couldn't find cluster for picked sector")
else:
    start_cluster_of_searching_file = fat_proxy.get_first_cluster(searching_cluster)
    for file in files._files_list:
        if not file.long_filename:
            if file.start_file_in_cluster == start_cluster_of_searching_file:
                print('==================')
                for name, value in file.__dict__.items():
                    print(name, value)
                break