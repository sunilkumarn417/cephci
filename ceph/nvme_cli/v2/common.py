"""Ceph-NVMeoF gateway module.

- Configure spdk and start spdk.
- Configure nvme-of targets using control.cli.
"""

from json import loads

from ceph.ceph_admin.common import config_dict_to_string
from cli.utilities.configs import get_registry_details
from cli.utilities.containers import Registry
from utility.log import Log

from . import NVMeGWCLI

LOG = Log(__name__)


def find_client_daemon_id(node, port=5500):
    """Find client daemon Id."""
    return NVMeGWCLI(node, port).fetch_gateway_client_name()


def find_gateway_hostname(node, port=5500):
    """Find client daemon Id."""
    return NVMeGWCLI(node, port).fetch_gateway_hostname()
