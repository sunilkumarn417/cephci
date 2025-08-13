from ceph.ceph_admin.common import config_dict_to_string
from utility.log import Log

LOG = Log(__name__)



class BaseCLI:
    """Execute Command class runs NVMe CLI on Gateway Node."""

    BASE_CMD = "ceph nvmeof"
    MTLS_BASE_CMD_ARGS = {
        "client-key": "/root/client.key",
        "client-cert": "/root/client.crt",
        "server-cert": "/root/server.crt",
    }

    def __init__(self, node, shell) -> None:
        """Initialize the Shell.

        Args:
            node: Gateway Node instance (CephNode)
            shell: Cephadm shell instance (orch.shell or cephadm.shell)
        """
        self.node = node
        self.shell = shell

    def run_nvme_cli(self, action, **kwargs):
        LOG.info(f"NVMe CLI command : {self.name} {action}")
        base_cmd_args = kwargs.get("base_cmd_args", {})

        if self.mtls:
            base_cmd_args.update(self.MTLS_BASE_CMD_ARGS)

        cmd_args = kwargs.get("args", {})
        command = " ".join(
            [
                self.BASE_CMD,
                self.__local_mtls_cert_path(),
                self.NVMEOF_CLI_IMAGE,
                config_dict_to_string(base_cmd_args),
                self.name,
                action,
                config_dict_to_string(cmd_args),
            ]
        )
        err, out = self.shell(cmd=command, sudo=True, pretty_print=True)
        LOG.info(f"ERROR - {err or None},\nOUTPUT - {out}")
        return out, err
