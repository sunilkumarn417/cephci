"""switches non-containerized ceph daemon to containerized ceph daemon"""
from utility.log import Log
from ceph.ceph_ansible_utils import CephAnsibleUtility

log = Log(__name__)


def run(**kw):
    config = kw.get("config")
    build = config.get("rhbuild")
    playbook = "switch-from-non-containerized-to-containerized-ceph-daemons.yml"
    log.info(f"Running ceph-ansible playbook: {playbook}")

    ceph_nodes = kw.get("ceph_nodes")
    installer_node = None
    for cnode in ceph_nodes:
        if cnode.role == "installer":
            installer_node = cnode

    ansible = CephAnsibleUtility(installer_node)
    conf = ansible.read_config(ansible.ALL)
    log.info(f"Current all.yml file content:{conf}")

    # Ansible playbook config overrides/modification
    conf.update(config.get("ansi_config", {}))

    # Set containerization to True
    conf.update({"containerized_deployment": True})

    # Overriden or development container images from build
    conf.update(
        [
            ("ceph_docker_registry", config.get("ceph_docker_registry")),
            ("ceph_docker_image", config.get("ceph_docker_image")),
            ("ceph_docker_image_tag", config.get("ceph_docker_image_tag")),
        ]
    )

    # CDN container images
    if conf.get("ceph_repository_type") == "cdn":
        conf.update(ansible.get_cdn_images(monitoring=conf.get("dashboard_enabled")))

    ansible.dump_config(conf, ansible.ALL)
    playbook_config = {
        "extra_vars": {"ireallymeanit": "yes"},
        "verbose": "vvvv"
    }
    rc = ansible.execute_playbook(playbook, build, **playbook_config)

    if rc == 0:
        log.info(f"ceph-ansible-playbook {playbook} successful")
        return 0
    log.error(f"ceph-ansible-playbook {playbook} failed")
    return 1
