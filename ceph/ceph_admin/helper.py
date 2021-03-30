"""
Contains helper functions that can used across the module.
"""
import logging

LOG = logging.getLogger()


def get_cluster_state(cls, commands=[]):
    """
    fetch cluster state using commands provided along
    with the default set of commands

    - ceph status
    - ceph orch ls -f json-pretty
    - ceph orch ps -f json-pretty
    - ceph health detail -f yaml

    Args:
        cls: ceph.ceph_admin instance with shell access
        commands: list of commands

    """
    __CLUSTER_STATE_COMMANDS = [
        "ceph status",
        "ceph orch ls -f yaml",
        "ceph orch ps -f json-pretty",
        "ceph health detail -f yaml",
    ]

    __CLUSTER_STATE_COMMANDS.extend(commands)

    for cmd in __CLUSTER_STATE_COMMANDS:
        out, err = cls.shell(args=[cmd])
        LOG.info("STDOUT:\n %s" % out)
        LOG.error("STDERR:\n %s" % err)


def set_custom_monitoring_svc_image(cls, svc, image):
    """
    Set custom monitoring image for services,
     - grafana
     - prometheus
     - alertmanager
     - node-exporter

    Args:
        cls: cephadm instance
        svc: monitoring service name
        image: custom image
    """
    monitoring = {
        "prometheus": "mgr/cephadm/container_image_prometheus",
        "alertmanager": "mgr/cephadm/container_image_alertmanager",
        "grafana": "mgr/cephadm/container_image_grafana",
        "node-exporter": "mgr/cephadm/container_image_node_exporter",
    }

    cls.shell(args=["ceph", "config", "set", "mgr", monitoring[svc], image])
