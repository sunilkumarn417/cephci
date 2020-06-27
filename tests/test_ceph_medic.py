import logging
import re

logger = logging.getLogger(__name__)
log = logger


def run(ceph_cluster, **kw):
    """
    ceph-mgr restful call for listing osds
    Args:
        ceph_cluster (ceph.ceph.Ceph): ceph cluster object
        kw: test config arguments
    Returns:
        int: non-zero on failure, zero on pass
    """
    ceph_installer = ceph_cluster.get_ceph_object('installer')

    # Install ceph-medic
    ceph_installer.exec_command(cmd="yum install -y ceph-medic", sudo=True)

    # Run ceph-medic check
    _RUN_MEDIC = "ceph-medic --inventory {}/hosts check".format(ceph_installer.ansible_dir)
    out, err = ceph_installer.exec_command(cmd=_RUN_MEDIC, check_ec=False)
    out, err = out.read().decode().strip(), err.read().decode().strip()
    logger.info("Command Response : {} {}".format(out, err))

    try:
        assert re.search(r"\d+\s+passed.*\d+\s+hosts", out, re.MULTILINE)
        return 0
    except AssertionError:
        return 1
