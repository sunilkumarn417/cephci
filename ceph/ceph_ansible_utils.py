"""Ceph-Ansible utility.

- read config
- execute playbook

"""
import yaml

from utility.log import Log
from ceph.ceph_admin.common import config_dict_to_string

log = Log(__name__)


class CephAnsibleSetupFailure(Exception):
    pass


class CephAnsibleUtility:
    """Ceph-Ansible utility."""

    ALL = "group_vars/all.yml"
    ALL_SAMPLE = f"{ALL}.sample"
    INFRA_PLAYBOOK_DIR = "infrastructure-playbooks"

    def __init__(
        self,
        ansible_node,
        ansible_dir="/usr/share/ceph-ansible",
        inventory="hosts"
    ):
        """Initialise utility with ansible node and directory

        Args:
            ansible_node: ansible node object
            ansible_dir: Ansible working directory
        """
        self.work_dir = ansible_dir
        self.ansible_node = ansible_node
        self.inventory = inventory

    @staticmethod
    def extra_vars(evars):
        return " ".join([f"-e '{k}={v}' " for k, v in evars.items()])

    @staticmethod
    def extra_args(args):
        return config_dict_to_string(args)

    def read_config(self, conf_file):
        """Read data from any conf file under group_vars

        Args:
            conf_file: name of conf file
        Returns:
            data content of conf in dict
        """
        out, _ = self.ansible_node.exec_command(
            sudo=True,
            cmd=f"cat {self.work_dir}/{conf_file}",
        )
        return yaml.safe_load(out)

    def dump_config(self, content, conf_file):
        """Dump the configuration to config file

        Args:
            content: config content in Dict
            conf_file: config file name
        """
        conf_yaml_file = yaml.dump(content)
        log.info(f"Updated {conf_file} with file content :\n{conf_yaml_file}")
        destination_file = self.ansible_node.remote_file(
            sudo=True,
            file_name=f"{self.work_dir}/{conf_file}",
            file_mode="w",
        )
        destination_file.write(conf_yaml_file)
        destination_file.flush()

    def get_cdn_images(self, config=ALL_SAMPLE, monitoring=False):
        """Fetches container image information from all.yml.sample.

        Returns:
            return all container images in Dict
            Ceph: docker_registry, docker_image, docker_image_tag
            Monitoring:  Grafana, prometheus, alert-manager, node-exporter
        """
        sample = self.read_config(config)
        conf = dict()
        conf.update(
            {
                "ceph_docker_registry": sample.get("ceph_docker_registry"),
                "ceph_docker_image": sample.get("ceph_docker_image"),
                "ceph_docker_image_tag": sample.get("ceph_docker_image_tag"),
            }
        )
        if monitoring:
            conf.update(
                {
                    "node_exporter_container_image": sample.get("node_exporter_container_image"),
                    "grafana_container_image": sample.get("grafana_container_image"),
                    "prometheus_container_image": sample.get("prometheus_container_image"),
                    "alertmanager_container_image": sample.get("alertmanager_container_image"),
                }
            )
        return conf

    def get_all_paths(self, dirs):
        """Get all posix paths from specific directories.

        Args:
            dirs: directories
        Returns:
            list of PosixPaths
        """
        paths = list()
        for _dir in dirs:
            cmd = f"ls -1 {self.work_dir}/{f'{_dir}/' if _dir else ''}*.yml"
            out, _ = self.ansible_node.exec_command(cmd=cmd, check_ec=False)
            paths.extend([i for i in out.split("\n") if i])
        return paths

    def playbook_exists(self, playbook):
        """Check if playbook exists."""
        for yml in self.get_all_paths([None, self.INFRA_PLAYBOOK_DIR]):
            if playbook in yml:
                return yml
        raise CephAnsibleSetupFailure(f"{playbook} not found...")

    def check_luminous(self, build, playbook):
        """Check for luminous infrastructure playbooks.

        if luminous, please copy the playbook to ansible work-dir
        else, return.

        Args:
            build: RHCS Build version
            playbook: Playbook Pathlib.PosixPath file path
        """
        if build.startswith("3") or build.startswith("2"):
            self.ansible_node.exec_command(
                cmd=f"cp {playbook} {self.work_dir}/",
                sudo=True,
            )
            return playbook.split("/", 1)[-1]
        return playbook

    def execute_playbook(self, playbook, build, **config):
        """Execute playbook.

        Args:cmd
            playbook: playbook to be executed.
            build: RHCS build version
            config: playbook command options

        ::config:
            extra_vars: {"ireallymeanit": "yes"},
            extra_args: {"list-tags": True},

        Returns:
            return code
        """
        playbook = self.playbook_exists(playbook)
        playbook = self.check_luminous(build, playbook)

        playbook_cmd = list(
            [
                f"cd {self.work_dir};"
                f"ansible-playbook -i {self.inventory} {playbook}",
                self.extra_vars(config.get("extra_vars", {})),
                self.extra_args(config.get("extra_args", {}))
            ]
        )

        if config.get("verbose"):
            playbook_cmd.append(f"-{config['verbose']}")

        log.info(f"[Started] Ceph-ansible playbook execution: {playbook}")
        return self.ansible_node.exec_command(
            cmd=" ".join(playbook_cmd),
            long_running=True
        )
