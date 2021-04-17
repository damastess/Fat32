from bidict import bidict

class FATProxy:
    def __init__(self, fat_byte_offset, fat_byte_size, bytes_per_ls, io):
        self._io = io
        self._fat_offset = fat_byte_offset
        self._fat_size = fat_byte_size
        self._bytes_per_ls = bytes_per_ls
        self._read()

    def _read(self):
        # Each FAT record is 32 bits
        # bits 0-6:  record_nr relative to FAT sector (128 per sector)
        # bits 7-31: ls_nr, sector number relative to FAT beginning
        _pos = self._io.pos()
        aux = {}

        # cluster_nr = ls_nr * 128 + record_nr
        # byte_offset = self._fat_offset + cluster_nr * 32
        # byte_offset = self._fat_offset + ls_nr * self._bytes_per_ls + record_nr * 32

        # Only parsing dangling records, for efficiency sake
        records_left = set()    # TODO: add first cluster nr (should be 2 - check)
        while records_left:
            # self._io.seek(fat_record_byte_offset)
            # aux = self._io.read_u4le()
            # TODO: ignore values considered as BAD CLUSTER (0x0FFFFFF7),
            #       and END CLUSTER (>=0x0FFFFFF8)
            # TODO: when seeking check if not moving out of fat_size, just in case
            pass

        self._fat = bidict(aux)
        self._io.seek(_pos)

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