from ceph.iscsi.gateway import Iscsi_Gateway
from ceph.ceph_admin.orch import Orch
from ceph.utils import get_node_by_id


class ISCSI:

    def __init__(self, ceph_cluster, gateways, **config):
        self.cluster = ceph_cluster
        self.config = config
        self.gateways = []
        self.orch = Orch(cluster=self.cluster, **{})

        for gw in gateways:
            gw_node = get_node_by_id(self.cluster, gw)
            self.gateways.append(Iscsi_Gateway(gw_node))
