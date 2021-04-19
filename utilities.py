from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from pkg_resources import parse_version
from bidict import bidict
import kaitaistruct
from queue import Queue


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))


class FileRec(KaitaiStruct):
    def __init__(self, _io):
        self._io = _io
        self._read()

    def _read(self):
        # self._io.read_bytes(8)
        _pos = self._io.pos()
        self.first_byte = self._io.read_u1()
        self._io.seek(_pos)

#check
        if self.first_byte == b"\0x40":
            long_dir = True
            name = ""
            last_byte = b"\0x40"
            while long_dir:
                name_first = (KaitaiStream.bytes_terminate(self._io.read_bytes(10), 0, False)).decode(u"UTF-8")
                attribute = self._io.read_bytes(1)
                type = self._io.read_bytes(1)
                checksum = self._io.read_bytes(1)
                name_second = (KaitaiStream.bytes_terminate(self._io.read_bytes(12), 0, False)).decode(u"UTF-8")
                self.fst_clus_lo = self._io.read_bytes(2)
                name_third = (KaitaiStream.bytes_terminate(self._io.read_bytes(4), 0, False)).decode(u"UTF-8")
                name += name_first
                name += name_second
                name += name_third
                next_byte = self._io.read_bytes(1)
                if next_byte != b"\0x40":
                    last_byte = next_byte
                    long_dir = False

        first = last_byte.decode(u"UTF-8")
        self.file_name = first + (KaitaiStream.bytes_terminate(self._io.read_bytes(7), 0, False)).decode(u"UTF-8")
        self.short_extension = self._io.read_bytes(3)

        self.read_only = self._io.read_bits_int_be(1)
        self.hidden = self._io.read_bits_int_be(1)
        self.is_system_file = self._io.read_bits_int_be(1)
        self.volume_label = self._io.read_bits_int_be(1)
        self.subdirectory = self._io.read_bits_int_be(1)
        self.archive = self._io.read_bits_int_be(1)
        self.device = self._io.read_bits_int_be(1)
        self.reserved_atr = self._io.read_bits_int_be(1)

        self._io.read_bytes(2)
        self.high_cluster_nr = self._io.read_u2le()
        self._io.read_bytes(4)
        self.access_rights = self._io.read_bytes(2)
        self.last_modified_time = self._io.read_bytes(2)
        self.last_modified_date = self._io.read_bytes(2)
        self.low_cluster_nr = self._io.read_u2le()
        self.file_size = self._io.read_u4le()
        # TODO: check if cluster_nr reconstruction is done properly
        self.start_file_in_cluster = self.high_cluster_nr * 65536 + self.low_cluster_nr

    def __str__(self):
        print(f'Filename: {self.file_name}\n'
              f'Subdirectory: {self.subdirectory}\n'
              f'Start_file_in_cluster: {self.start_file_in_cluster}\n'
              f'File_size: {self.file_size}\n'
              f'Subdirectory: {self.subdirectory}\n'
              f'Volume_label: {self.volume_label}\n'
              f'high_cluster_nr: {self.high_cluster_nr}\n'
              f'low_cluster_nr: {self.low_cluster_nr}\n')


class Filesystem():
    def __init__(self, fat_proxy, filesystem_offset, bytes_per_cluster, io):
        self._fat_proxy = fat_proxy
        self._filesystem_offset = filesystem_offset
        self._bytes_per_cluster = bytes_per_cluster
        self._io = io

        self._files_list = []
        _pos = self._io.pos()
        self._inflate()
        self._io.seek(_pos)

    def _inflate(self):
        self._io.seek(self._filesystem_offset)
        root_dir = FileRec(self._io)
        dirs_left = Queue(root_dir)
        self._files_list = [root_dir]

        while not dirs_left.empty():
            parent_dir = dirs_left.get()
            curr_cluster = parent_dir.start_file_in_cluster

            record_offset = 0
            while True:
                if self._io.pos() % self._bytes_per_cluster == 0:
                    curr_cluster = self._fat_proxy.get_next_cluster(curr_cluster)
                    if curr_cluster == -1:
                        break

                # Cluster's size is equal to 4096B
                self._io.seek(self._filesystem_offset + curr_cluster * self._bytes_per_cluster + record_offset)
                aux = FileRec(self._io)

                # Found an entry regarded as an end-of-chain record
                # TODO: add other stop-values
                if aux.first_byte == 0:
                    break

                if aux.subdirectory == 1:
                    dirs_left.put(aux)
                self._files_list += [aux]

                # Record size is 32B
                record_offset += 32


class FATProxy:
    def __init__(self, fat_list):
        self._inflate_fat(fat_list)

    def _inflate_fat(self, fat_list):
        self._fat = bidict()
        for cluster_nr, record in enumerate(fat_list[2:]):
            flags = record.flags
            pointed_cluster_nr = record.ls_nr * 128 + record.record_nr

            if pointed_cluster_nr == 0xFFFFFFF or \
               pointed_cluster_nr == 0xFFFFFF8 or \
               (flags == 0 and pointed_cluster_nr == 0) or\
               flags >= 7:
                # 7 => bad cluster, >=8 => end cluster, 0 && cluster_nr == 0 => empty,
                # cluster nr == 0xFFFFFFF => special value
                continue

            self._fat[cluster_nr] = pointed_cluster_nr

    def get_next_cluster(self, cluster_nr):
        try:
            return self._fat[cluster_nr]
        except KeyError:
            return -1

    def get_prev_cluster(self, cluster_nr):
        try:
            return self._fat.inverse[cluster_nr]
        except KeyError:
            return -1

    def get_first_cluster(self, cluster_nr):
        prev_in_chain = self.get_prev_cluster(cluster_nr)
        while prev_in_chain != -1:
            cluster_nr = prev_in_chain
            prev_in_chain = self.get_prev_cluster(cluster_nr)

        return cluster_nr
