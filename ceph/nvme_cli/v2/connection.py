from ceph.nvme_cli.v2.base_cli import BaseCLI


class Connection:

    def __init__(self, base: BaseCLI) -> None:
        self.base = base
        self.name = "connection"

    def list(self, **kwargs):
        return self.run_nvme_cli(self.name, "list", **kwargs)
