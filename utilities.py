from bidict import bidict


class FATProxy:
    def __init__(self, fat_list):
        self._inflate_fat(fat_list)

    def _inflate_fat(self, fat_list):
        self._fat = bidict()
        for cluster_nr, record in enumerate(fat_list[2:]):
            flags = record.flags
            pointed_cluster_nr = record.ls_nr * 128 + record.record_nr

            if flags >= 7 or (flags == 0 and pointed_cluster_nr == 0):
                # 7 => bad cluster, >=8 => end cluster, 0 && cluster_nr == 0 => empty
                continue

            try:
                if flags != 0:
                    print(f'{cluster_nr}: {flags}')
                self._fat[cluster_nr] = pointed_cluster_nr
            except Exception as e:
                print(f'{cluster_nr} = {pointed_cluster_nr} (referenced by {self._fat.inverse[pointed_cluster_nr]})')

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
