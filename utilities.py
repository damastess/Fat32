from kaitaistruct import KaitaiStruct
from pkg_resources import parse_version
from bidict import bidict
import kaitaistruct
from queue import Queue
from datetime import datetime


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception('Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s' % (
        kaitaistruct.__version__))


class LongFileRec(KaitaiStruct):
    def __init__(self, _io, deleted_file=False):
        self._io = _io
        self._offset = self._io.pos()
        self.deleted = deleted_file
        self._read()

    def _read(self):
        self.long_filename = True
        self.sequence_nr = self._io.read_u1() ^ int('0x40', 16)
        # long filename chars 1-5 (unicode, le)
        file_name_chunk1 = self._io.read_bytes(10).decode('ascii', 'ignore')
        # file attribute (must be 0x0F)
        self.attribute_byte = self._io.read_u1()
        # if zero, this is a subcomponent of a long name
        self.sub_flag = self._io.read_u1()
        # checksum of short filename
        self.checksum = self._io.read_u1()
        # long filename chars 6-11 (unicode, le)
        file_name_chunk2 = self._io.read_bytes(12).decode('ascii', 'ignore')
        # must be zero
        self.zero_flag = self._io.read_u2le()
        # long filename chars 12-13 (unicode, le)
        file_name_chunk3 = self._io.read_bytes(4).decode('ascii', 'ignore')
        self.file_name = file_name_chunk1 + file_name_chunk2 + file_name_chunk3

    def __str__(self):
        print(f'Filename: {self.file_name}\n'
              f'Is long: {self.long_filename}\n'
              f'Seq_nr: {self.sequence_nr}\n')


class FileRec(KaitaiStruct):
    def __init__(self, _io, was_deleted=False):
        self._io = _io
        self._offset = self._io.pos()
        self.deleted = was_deleted
        self._read()

    def _read(self):
        self.long_filename = False
        self.file_name = self._io.read_bytes(8)
        self.full_file_name = self.file_name
        self.short_extension = self._io.read_bytes(3)

        self.read_only = bool(self._io.read_bits_int_le(1))
        self.hidden = bool(self._io.read_bits_int_le(1))
        self.is_system_file = bool(self._io.read_bits_int_le(1))
        self.volume_label = bool(self._io.read_bits_int_le(1))
        self.subdirectory = bool(self._io.read_bits_int_le(1))
        self.archive = bool(self._io.read_bits_int_le(1))
        self.device = bool(self._io.read_bits_int_le(1))
        self.reserved_atr = bool(self._io.read_bits_int_le(1))

        # random stuff
        self._io.read_bytes(1)
        # first char of deleted file or misc
        self._io.read_bytes(1)

        # create time hhmmss
        self.created_time_seconds = self._io.read_bits_int_le(5)
        self.created_time_minutes = self._io.read_bits_int_le(6)
        self.created_time_hours = self._io.read_bits_int_le(5)

        # create time yymmdd
        self.created_date_day = self._io.read_bits_int_le(5)
        self.created_date_month = self._io.read_bits_int_le(4)
        self.created_date_year = self._io.read_bits_int_le(7)

        # owner id
        self._io.read_bytes(2)
        # start of file - high two bytes
        high_cluster_nr = self._io.read_u2le()

        # last modified time
        self.last_modified_time_seconds = self._io.read_bits_int_le(5)
        self.last_modified_time_minutes = self._io.read_bits_int_le(6)
        self.last_modified_time_hours = self._io.read_bits_int_le(5)

        # last modified date
        self.last_modified_day = self._io.read_bits_int_le(5)
        self.last_modified_month = self._io.read_bits_int_le(4)
        self.last_modified_year = self._io.read_bits_int_le(7)

        # start of file - low two bytes
        low_cluster_nr = self._io.read_u2le()
        # file size in bytes
        self.file_size = self._io.read_bits_int_le(4)

        self.created_date_time = datetime(
            second=self.created_time_seconds,
            minute=self.created_time_minutes,
            hour=self.created_time_hours,
            day=self.created_date_day,
            month=self.created_date_month,
            year=self.created_date_year + 1980)

        self.last_modified_date_time = datetime(
            second=self.last_modified_time_seconds,
            minute=self.last_modified_time_minutes,
            hour=self.last_modified_time_hours,
            day=self.last_modified_day,
            month=self.last_modified_month,
            year=self.last_modified_year + 1980)

        self.file_first_cluster_nr = high_cluster_nr * 65536 + low_cluster_nr

    def __str__(self):
        # TODO: add sector/byte offset from disc beginning
        return (f'Full filename: {self.full_file_name}\n'
                f'Short filename: {self.file_name}\n'
                f'Short extension: {self.short_extension}\n'
                f'Created: {self.created_date_time}\n'
                f'Last modified: {self.last_modified_date_time}\n'
                f'First file cluster nr: {self.file_first_cluster_nr}\n'
                f'File absolute offset (B): {self._offset}\n'
                f'File size (B): {0 if self.volume_label or self.subdirectory else self.file_size}\n'
                f'Is long: {self.long_filename}\n'
                f'Is deleted: {self.deleted} \n'
                f'Is readOnly: {self.read_only}\n'
                f'Is hidden: {self.hidden}\n'
                f'Is system File: {self.is_system_file}\n'
                f'Is volume Label: {self.volume_label}\n'
                f'Is subdirectory: {self.subdirectory}\n'
                f'Is archive: {self.archive}\n')


class Filesystem:
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

        deleted_file = False
        # TODO: switch to a saner value representation
        if first_byte == int('0xE5', 16) or \
           first_byte == int('0x05', 16):
            # Removed / pending delete entry
            deleted_file = True

        if first_byte == int('0x2E', 16):
            # Dot entry
            return -1
        elif flag_byte == int('0x0F', 16):
            # Long filename
            return LongFileRec(self._io, deleted_file)
        elif first_byte != 0:
            return FileRec(self._io, deleted_file)
        else:
            return None

    def _assemble_long_record(self, long_files, last_record):
        last_record.full_file_name = ''.join(
            str(rec.file_name).strip() for rec in long_files[::-1])
        return last_record

    def _inflate(self):
        self._io.seek(self._filesystem_offset)
        dirs_left = Queue()
        self._files_list = []

        root_dir = True
        while not dirs_left.empty() or root_dir:
            if not root_dir:
                parent_dir = dirs_left.get()
                curr_cluster = parent_dir.file_first_cluster_nr
            else:
                curr_cluster = 2

            long_filename_series = False
            last_long_records = []
            record_offset = 0
            while True:
                # Empty dir found
                if curr_cluster == 0:
                    break

                # Cluster's size is equal to 4096B, first cluster's number
                # is equal to 2
                # TODO: test cluster hopping in more elaborate circumstances
                #       (bigger directories for one)
                # TODO: seek below can be moved to cluster hopping, by default
                #       files will be sequential
                self._io.seek(self._filesystem_offset + (curr_cluster - 2)
                              * self._bytes_per_cluster + record_offset)  # noqa: W503

                record = self._read_record()
                if not record:
                    # Found an entry regarded as an end-of-chain record
                    root_dir = False
                    break
                elif record == -1:
                    # Ignoring current and parent dirs ('.' '..')
                    record_offset += 32
                    continue

                # Not a long filename, but a subdirectory
                if not record.long_filename and \
                   record.subdirectory is True:
                    dirs_left.put(record)

                if not record.long_filename and long_filename_series:
                    record = self._assemble_long_record(
                        last_long_records, record)
                    last_long_records = []
                    long_filename_series = False
                elif record.long_filename:
                    # Another long entry in series
                    last_long_records += [record]
                    long_filename_series = True

                if not long_filename_series:
                    self._files_list += [record]

                # Record size is 32B
                record_offset += 32

                if self._io.pos() % self._bytes_per_cluster == 0:
                    record_offset = 0
                    curr_cluster = self._fat_proxy.get_next_cluster(
                        curr_cluster)
                    if curr_cluster == -1:
                        break

    def getFilesList(self):
        return self._files_list


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
