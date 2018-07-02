import logging
import random

from tests.iscsi.iscsi_utils import IscsiUtils

log = logging


def run(**kw):
    log.info('Running iscsi configuration')
    ceph_nodes = kw.get('ceph_nodes')
    config = kw.get('config')
    no_of_gateways = config.get('no_of_gateways', 2)
    global no_of_luns
    no_of_luns = config.get('no_of_luns', 10)
    image_name = 'test_image' + str(random.randint(10, 999))

    log.info('Preparing ceph cluster')
    iscsi_util = IscsiUtils(ceph_nodes)
    iscsi_util.install_prereq_gw()
    iscsi_util.install_prereq_rhel_client()
    iscsi_util.do_iptables_flush()
    gw_list = iscsi_util.get_gw_list(no_of_gateways)
    gwcli_node = iscsi_util.setup_gw(gw_list)
    iscsi_util.run_gw(gwcli_node, gw_list)

    log.info('Creating iscsi host')
    initiator_node = iscsi_util.get_iscsi_initiator_linux()
    initiator_name = iscsi_util.get_initiatorname(full=True)
    iscsi_util.create_host(gwcli_node, initiator_name)
    iscsi_util.create_luns(
        no_of_luns,
        gwcli_node,
        initiator_name,
        image_name,
        iosize="2g",
        map_to_client=True)

    iscsi_util.write_multipath(initiator_node)
    return 0
