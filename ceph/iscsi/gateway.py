from cli.utilities.containers import Container
from ceph.iscsi.utils import get_iscsi_container


class GWCLI:

    def __init__(self, node):
        self.node = node
        self.iscsi_target = self.IQN_Target(self)
        self.iscsi_container = self.iscsi_container(self.node)
        self.container_id = self.iscsi_container["Names"][0]

    @property
    def iscsi_container(self):
        return get_iscsi_container(self.node)
    
    @staticmethod
    def format_command_options(**kwargs):
        """Construct the iscsi path to define target and its entities.
        
        Args:
            kwargs: command options in Dict

        Returns:
            Str
        """
        cmd_opts = str()
        for k,v in kwargs.items():
            cmd_opts += f" {k}={v}"
        return cmd_opts

    def exec_gw_cli(self, action, path="/",  **kwargs):
        """Execute iSCSI GWCLI command

        Args:
            action: operation to be performed on specific entity
            path: iSCSI command path to manage entities
            kwargs: command options
        """
        cmd = f"{path} {action} {self.format_command_options(**kwargs)}"
        return self.container.exec(
            container=self.container_id,
            interactive=True,
            cmds=kwargs[cmd],
        )

    class IQN_Target:
        path = "/iscsi-targets"

        def __init__(self, parent):
            self.parent = parent
            self.gateways = self.Gateways(self)
            self.hosts = self.Hosts(self)
            self.disks = self.Disks(self)

        def create(self, iqn):
            return self.parent.exec_gw_cli("create", self.path, {"target_iqn": iqn})

        def delete(self, iqn):
            return self.parent.exec_gw_cli("create", self.path, {"target_iqn": iqn})
        
        def discovery_auth(self, **kwargs):
            return self.parent.exec_gw_cli("discovery_auth", self.path, **kwargs)

        class Hosts:
            path = "/iscsi-targets/{IQN}/hosts"
            
            def __init__(self, parent):
                self.parent = parent

            def create(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("create", self.path.format(IQN=iqn), **kwargs)
            
            def delete(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("delete", self.path.format(IQN=iqn), **kwargs)

        class Gateways:
            path = "/iscsi-targets/{IQN}/gateways"

            def __init__(self, parent):
                self.parent = parent

            def create(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("create", self.path.format(IQN=iqn), **kwargs)
            
            def delete(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("delete", self.path.format(IQN=iqn), **kwargs)

        class Disks:
            path = "/iscsi-targets/{IQN}/disks"

            def __init__(self, parent):
                self.parent = parent

            def create(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("create", self.path.format(IQN=iqn), **kwargs)
            
            def delete(self, iqn, **kwargs):
                return self.parent.exec_gw_cli("delete", self.path.format(IQN=iqn), **kwargs)


class Iscsi_Gateway:

    def __init__(self, node):
        """
        iSCSI Gateway node

        Args:
            node: CephNode object
        """
        self.node = node
        self.gwcli = GWCLI(self.node)
