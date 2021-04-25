from kaitaistruct import KaitaiStruct, KaitaiStream  # , BytesIO
from pkg_resources import parse_version
from bidict import bidict
import kaitaistruct
from queue import Queue


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))


def read_unicode_chars(char_nr, _io):
    # TODO: implement proper unicode parsing (ucs-2)
    return _io.read_bytes(char_nr)
    # return (KaitaiStream.bytes_terminate(_io.read_bytes(char_nr), 0, False)).decode(u'UTF-16')


class LongFileRec(KaitaiStruct):
    def __init__(self, _io):
        self._io = _io
        self._read()

    def _read(self):
        self.long_filename = True
        self.sequence_nr = self._io.read_u1() ^ int('0x40', 16)
        file_name_chunk1 = read_unicode_chars(10, self._io)  # long filename chars 1-5 (unicode, le)
        self.attribute_byte = self._io.read_u1()  # file attribute (must be 0x0F)
        self.sub_flag = self._io.read_u1()  # if zero, this is a subcomponent of a long name
        self.checksum = self._io.read_u1()  # checksum of short filename
        file_name_chunk2 = read_unicode_chars(12, self._io)  # long filename chars 6-11 (unicode, le)
        self.zero_flag = self._io.read_u2le()  # must be zero
        file_name_chunk3 = read_unicode_chars(4, self._io)  # long filename chars 12-13 (unicode, le)
        self.file_name = file_name_chunk1 + file_name_chunk2 + file_name_chunk3


class FileRec(KaitaiStruct):
    def __init__(self, _io):
        self._io = _io
        self._read()

    def _read(self):
        self.long_filename = False
        # self.file_name = (KaitaiStream.bytes_terminate(self._io.read_bytes(8), 0, False)).decode(u"UTF-8")
        self.file_name = self._io.read_bytes(8)
        self.short_extension = self._io.read_bytes(3)

        self.read_only = self._io.read_bits_int_le(1)
        self.hidden = self._io.read_bits_int_le(1)
        self.is_system_file = self._io.read_bits_int_le(1)
        self.volume_label = self._io.read_bits_int_le(1)
        self.subdirectory = self._io.read_bits_int_le(1)
        self.archive = self._io.read_bits_int_le(1)
        self.device = self._io.read_bits_int_le(1)
        self.reserved_atr = self._io.read_bits_int_le(1)

        self._io.read_bytes(1)  # random stuff
        self._io.read_bytes(1)  # first char of deleted file
        self._io.read_bytes(2)  # create time hhmmss
        self._io.read_bytes(2)  # create time yymmdd
        self._io.read_bytes(2)  # owner id
        high_cluster_nr = self._io.read_u2le()  # start of file - high two bytes
        self._io.read_bytes(2)  # last modified time
        self._io.read_bytes(2)  # last modified date
        low_cluster_nr = self._io.read_u2le()  # start of file - low two bytes
        self._io.read_bytes(4)  # filesize in bytes

        self.start_file_in_cluster = high_cluster_nr * 65536 + low_cluster_nr
        # print(f'===== {self.high_cluster_nr} {self.low_cluster_nr} {self.start_file_in_cluster}')

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

    def _read_record(self):
        _pos = self._io.pos()
        first_byte = self._io.read_u1()
        self._io.seek(_pos + 11)
        flag_byte = self._io.read_u1()
        self._io.seek(_pos)

        # Long filename check
        if first_byte & int('0x40', 16) and flag_byte == int('0x0F', 16):
            return LongFileRec(self._io)
        elif first_byte != 0:
            return FileRec(self._io)
        else:
            return None

    def _inflate(self):
        self._io.seek(self._filesystem_offset)
        dirs_left = Queue()
        self._files_list = []

        # Dirty workaround
        root_dir = True
        while not dirs_left.empty() or root_dir:
            if not root_dir:
                parent_dir = dirs_left.get()
                curr_cluster = parent_dir.start_file_in_cluster
            else:
                curr_cluster = 2

            long_filename_series = False
            last_long_records = []
            record_offset = 0
            while True:
                # Empty dir found
                if curr_cluster == 0:
                    break

                # Cluster's size is equal to 4096B, first cluster's number is equal to 2
                # TODO: seek below can be moved to cluster hopping, by default files will be sequential
                self._io.seek(self._filesystem_offset + (curr_cluster - 2) * self._bytes_per_cluster + record_offset)

                record = self._read_record()
                # print(f'record found, type: {type(record).__name__}')
                # Found an entry regarded as an end-of-chain record
                if not record:
                    # print('===-=-=-=-=-=-=-=-=-=-=-=====')
                    root_dir = False
                    break

                # Not a long filename, but a subdirectory
                if not record.long_filename and record.subdirectory == 1:
                    dirs_left.put(record)
                # TODO: store only assembled final files (join long filenames)
                self._files_list += [record]

                # First short entry after long series
                if not record.long_filename and long_filename_series:
                    # TODO: assemble last long records into one record here
                    last_long_records = []
                    long_filename_series = False
                # Another long entry in series
                elif record.long_filename:
                    last_long_records += [record]
                    long_filename_series = True

                # Record size is 32B
                record_offset += 32

                if self._io.pos() % self._bytes_per_cluster == 0:
                    curr_cluster = self._fat_proxy.get_next_cluster(curr_cluster)
                    print('====== [ CLUSTER JUMPED ] ======')
                    if curr_cluster == -1:
                        print('====== [ END OF CLUSTER CHAIN ] ======')
                        break


class FATProxy:
    def __init__(self, fat_list):
        self._inflate_fat(fat_list)

    def _inflate_fat(self, fat_list):
        self._fat = bidict()
        for cluster_nr, record in enumerate(fat_list[2:]):
            # First 2 clusters are omitted
            cluster_nr += 2
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
