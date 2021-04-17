from bidict import bidict

class FATProxy:
    def __init__(self, fat_byte_offset, fat_byte_size, io):
        self._io = io
        self._fat_offset = fat_byte_offset
        self._fat_size = fat_byte_size
        self._read()

    def _read(self):
        # parse whole FAT - generate bidicr

        # fat_record_byte_offset = cluster_nr * 32 # ???

        # _pos = self._io.pos()
        # self._io.seek(fat_record_byte_offset)

        # aux = self._io.read_u4le()
        # self._io.seek(_pos)

        self._fat = bidict({123: 456})

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