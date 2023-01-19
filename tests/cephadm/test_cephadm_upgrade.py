"""
Test module that verifies the Upgrade of Ceph Storage via the cephadm CLI.

"""

from ceph.ceph_admin.orch import Orch
from ceph.rados.rados_bench import RadosBench
from ceph.utils import is_legacy_container_present, get_cdn_container_image
from utility.log import Log
from utility.utils import fetch_build_artifacts

log = Log(__name__)


class UpgradeFailure(Exception):
    pass


def run(ceph_cluster, **kwargs) -> int:
    """
    Upgrade the cluster to latest version and verify the status

    Args:
        ceph_cluster: Ceph cluster object
        kwargs:     Key/value pairs of configuration information to be used in the test.

    Returns:
        int - 0 when the execution is successful else 1 (for failure).

    Example:
        - test:
            name: Upgrade cluster
            desc: Upgrade to latest version
            config:
                command: start
                service: upgrade
                base_cmd_args:
                    verbose: true

    Since image are part of main config, no need of any args here.
    """
    log.info("Upgrade Ceph cluster...")
    config = kwargs["config"]
    config["overrides"] = kwargs.get("test_data", {}).get("custom-config")
    rhcs_version = config.pop("rhcs_version")
    release = config.pop("release")
    use_cdn = False

    orch = Orch(cluster=ceph_cluster, **config)

    client = ceph_cluster.get_nodes(role="client")[0]
    clients = ceph_cluster.get_nodes(role="client")
    executor = None

    # ToDo: Switch between the supported IO providers
    if config.get("benchmark"):
        executor = RadosBench(mon_node=client, clients=clients)

    try:
        # Initiate thread pool to run rados bench
        if executor:
            executor.run(config=config["benchmark"])
        # Fetch Build
        installer = ceph_cluster.get_nodes(role="installer")[0]
        if release and isinstance(rhcs_version, float):
            (base_url, registry, image, tag) = fetch_build_artifacts(
                release,
                rhcs_version,
                config["rhbuild"].split("-", 1)[-1]
            )
            container_image = f"{registry}/{image}:{tag}"
            base_url = f"{base_url}/" if not base_url.endswith("/") else base_url
            orch.set_tool_repo(repo=f"{base_url}compose/Tools/x86_64/os/")
        elif release == "cdn" or config["build_type"] == "released":
            container_image = None
            orch.set_cdn_tool_repo(rhcs_version)
            use_cdn = True
        else:
            # Set repo to newer RPMs and image
            orch.set_tool_repo()
            container_image = config["container_image"]

        # Install cephadm
        orch.install()

        # Check service versions vs available and target containers
        if use_cdn:
            get_cdn_container_image(installer)
        orch.upgrade_check(image=container_image)

        # work around for upgrading from 5.1 and 5.2 to 5.1 and 5.2 latest
        base_cmd = "sudo cephadm shell -- ceph"
        ceph_version, err = installer.exec_command(cmd=f"{base_cmd} version")
        if ceph_version.startswith("ceph version 16.2."):
            installer.exec_command(
                cmd=f"{base_cmd} config set mgr mgr/cephadm/no_five_one_rgw true --force"
            )
            installer.exec_command(cmd=f"{base_cmd} orch upgrade stop")

        # Start Upgrade
        config.update({"args": {"image": None}})
        orch.start_upgrade(config)

        # Monitor upgrade status, till completion
        orch.monitor_upgrade_status()

        if config.get("verify_cephadm_containers") and is_legacy_container_present(
            ceph_cluster
        ):
            log.info(
                "Checking cluster status to ensure that the legacy services are not being inferred"
            )
            if orch.cluster.check_health(
                rhbuild=config.get("rhbuild"), client=orch.installer
            ):
                raise UpgradeFailure("Cluster is in HEALTH_ERR state after upgrade")

        if config.get("verify_cluster_health"):
            if orch.cluster.check_health(
                rhbuild=config.get("rhbuild"), client=orch.installer
            ):
                raise UpgradeFailure("Cluster is in HEALTH_ERR state")
    except BaseException as be:  # noqa
        log.error(be, exc_info=True)
        return 1
    finally:
        if executor:
            executor.teardown()

        # Get cluster state
        orch.get_cluster_state(
            [
                "ceph status",
                "ceph versions",
                "ceph orch ps -f yaml",
                "ceph orch ls -f yaml",
                "ceph orch upgrade status",
                "ceph mgr dump",  # https://bugzilla.redhat.com/show_bug.cgi?id=2033165#c2
                "ceph mon stat",
            ]
        )

    return 0
