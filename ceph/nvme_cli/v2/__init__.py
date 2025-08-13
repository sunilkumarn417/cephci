from json import loads

from ceph.nvme_cli.v2.connection import Connection
from ceph.nvme_cli.v2.gateway import Gateway
from ceph.nvme_cli.v2.host import Host
from ceph.nvme_cli.v2.listener import Listener
from ceph.nvme_cli.v2.log_level import LogLevel
from ceph.nvme_cli.v2.namespace import Namespace
from ceph.nvme_cli.v2.subsystem import Subsystem
from ceph.nvme_cli.v2.base_cli import BaseCLI
from ceph.nvme_cli.v2.version import Version
from cephci.utils.configs import get_configs, get_registry_credentials


class NVMeGWCLI(BaseCLI):
    def __init__(self, node, shell, **kwargs) -> None:
        """Initialize NVMe Gateway cli

        Args:
            node: Gateway Node instance (CephNode)
            shell: Cephadm shell instance (orch.shell or cephadm.shell)
        """
        super().__init__(node, shell)
        self.node = node
        self.shell = shell
        self._mtls = kwargs.get("mtls", False)
        self.connection = Connection(self)
        self.gateway = Gateway(self)
        self.host = Host(self)
        self.loglevel = LogLevel(self)
        self.listener = Listener(self)
        self.namespace = Namespace(self)
        self.subsystem = Subsystem(self)
        self.version = Version(self)
        self.name = " "

    @property
    def mtls(self):
        return self._mtls

    @mtls.setter
    def mtls(self, value):
        self._mtls = value
        self.setter("mtls", value)

    def fetch_gateway(self):
        """Return Gateway info"""
        gwinfo = {"base_cmd_args": {"format": "json"}}
        _, out = self.gateway.info(**gwinfo)
        out = loads(out)
        return out

    def fetch_gateway_client_name(self):
        """Return Gateway Client name/id."""
        out = self.fetch_gateway()
        return out["name"]

    def fetch_gateway_lb_group_id(self):
        """Return Gateway Load balancing group Id."""
        out = self.fetch_gateway()
        return out["load_balancing_group"]

    def fetch_gateway_hostname(self):
        """Return Gateway load balancing group host name"""
        out = self.fetch_gateway()
        return out["hostname"]

    def get_subsystems(self, **kwargs):
        """Nvme CLI get_subsystems"""
        return self.run_nvme_cli(self.name, "get_subsystems", **kwargs)
