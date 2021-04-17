from bidict import bidict

class FATProxy:
    def __init__(self, fat_byte_offset, fat_byte_size, bytes_per_ls, io):
        self._io = io
        self._fat_offset = fat_byte_offset
        self._fat_size = fat_byte_size
        self._bytes_per_ls = bytes_per_ls
        self._read()

    def _read(self):
        # TODO: cleanup
        # Each FAT record is 32 bits
        # bits 0-6:  record_nr relative to FAT sector (128 per sector)
        # bits 7-31: ls_nr, sector number relative to FAT beginning
        # First two records in FAT are unused, enumeration starts from 0 at sector 2
        # byte_offset = self._fat_offset + ls_nr * self._bytes_per_ls + record_nr * 32
        # byte_offset = self._fat_offset + cluster_nr * 32

        _pos = self._io.pos()
        # Navigating to the first viable record
        self._io.seek(self._fat_offset + 2)
        self._fat = bidict()

        for cluster_nr in range(2, self._fat_size // 32):
            record_nr = self._io.read_bits_int_le(7)
            ls_nr = self._io.read_bits_int_le(21)
            flag = self._io.read_bits_int_le(4)

            next_cluster_nr = ls_nr * 128 + record_nr

            if flag >= 7 or (flag == 0 and next_cluster_nr == 0):
                # 7 => bad cluster, >=8 => end cluster, 0 && cluster_nr == 0 => empty
                continue
            
            self._fat[cluster_nr] = next_cluster_nr
        
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