"""Ceph Ansible Upgrade Test module

Playbooks:
- rolling update to newer version
- Ceph-adm adoption (>= RHCS 5.x ).
"""
from ceph.utils import (
    get_ceph_versions,
    get_node_by_id,
    get_public_network,
    is_legacy_container_present,
    set_container_info,
    translate_to_ip,
)
from ceph.ceph_ansible_utils import CephAnsibleUtility
from utility.utils import Log, get_latest_container_image_tag

LOG = Log(__name__)


def run(ceph_cluster, **kw):
    ceph_installer = ceph_cluster.get_ceph_object("installer")
    ansible = CephAnsibleUtility(ceph_installer)
    LOG.info("Running ceph ansible Upgrade test...")

    config = kw.get("config")
    ansi_config = config.get("ansi_config")

    ceph_nodes = kw.get("ceph_nodes")
    test_data = kw.get("test_data")
    prev_install_version = test_data["install_version"]
    skip_version_compare = config.get("skip_version_compare")
    containerized = ansi_config.get("containerized_deployment")
    build = config.get("build", config.get("rhbuild"))
    LOG.info(f"Build for upgrade: {build}")

    ubuntu_repo = config.get("ubuntu_repo")
    hotfix_repo = config.get("hotfix_repo")
    cloud_type = config.get("cloud-type", "openstack")
    base_url = config.get("base_url")
    installer_url = config.get("installer_url")
    ansi_config["public_network"] = get_public_network(ceph_nodes)

    ceph_cluster.ansible_config = ansi_config
    ceph_cluster.custom_config = test_data.get("custom-config")
    ceph_cluster.custom_config_file = test_data.get("custom-config-file")
    ceph_cluster.use_cdn = config.get("use_cdn") or config.get("build_type") == "released"

    ansi_config.update(
        set_container_info(ceph_cluster, config, ceph_cluster.use_cdn, containerized)
    )

    # Translate RGW node to ip address for Multisite
    rgw_pull_host = ansi_config.get("rgw_pullhost")
    if rgw_pull_host:
        ceph_cluster.ansible_config["rgw_pullhost"] = translate_to_ip(
            kw["ceph_cluster_dict"], ceph_cluster.name, rgw_pull_host
        )

    if config.get("skip_setup") is True:
        LOG.info("Skipping setup of ceph cluster")
        return 0

    # set pre-upgrade install version
    test_data["install_version"] = build
    LOG.info("Previous install version: {}".format(prev_install_version))

    # retrieve pre-upgrade versions and initialize container counts
    pre_upgrade_versions = get_ceph_versions(ceph_cluster.get_nodes(), containerized)
    pre_upgrade_container_counts = {}

    # setup packages based on build
    ceph_cluster.setup_packages(
        base_url, hotfix_repo, installer_url, ubuntu_repo, build, cloud_type
    )

    # backup existing hosts file and ansible config
    ceph_installer.exec_command(cmd=f"cp {ansible.work_dir}/hosts /tmp/hosts")
    ceph_installer.exec_command(
        cmd=f"cp {ansible.work_dir}/group_vars/all.yml /tmp/all.yml"
    )

    # update ceph-ansible
    ceph_installer.install_ceph_ansible(build, upgrade=True)

    # Update CDN images
    if ceph_cluster.use_cdn:
        ansi_config.update(
            ansible.get_cdn_images(monitoring=ansi_config.get("dashboard_enabled"))
        )

    # restore hosts file
    ceph_installer.exec_command(
        sudo=True, cmd=f"cp /tmp/hosts {ansible.work_dir}/hosts"
    )

    # If upgrading from version 2 update hosts file with mgrs
    if prev_install_version.startswith("2") and build.startswith("3"):
        collocate_mons_with_mgrs(ceph_cluster, ansible.work_dir)

    # configure fetch directory path
    if ansi_config.get("fetch_directory") is None:
        ansi_config["fetch_directory"] = "~/fetch/"

    # set the docker image tag if necessary
    if containerized and ansi_config.get("docker-insecure-registry"):
        ansi_config["ceph_docker_image_tag"] = get_latest_container_image_tag(
            build
        )

    ansible.dump_config(ansi_config, ansible.ALL)

    # retrieve container count if containerized
    if containerized:
        pre_upgrade_container_counts = get_container_counts(ceph_cluster)

    # configure insecure registry if necessary
    if config.get("docker-insecure-registry"):
        ceph_cluster.setup_insecure_registry()

    # Execute rolling update playbook
    playbook = "rolling_update.yml"
    playbook_cfg = {
        "verbose": "vvvv"
    }
    extra_vars = {"ireallymeanit": "yes"}
    extra_args = {}

    jewel_minor_update = build.startswith("2")
    if jewel_minor_update:
        extra_vars["jewel_minor_update"] = "true"
        LOG.info("Upgrade is jewel_minor_update.")

    if config.get("ansi_cli_args"):
        extra_args.update(config["ansi_cli_args"])

    if build.startswith("5.1"):
        extra_vars["qe_testing"] = "true"

    if config.get("limit"):
        short_names = []
        for node in config["limit"]:
            short_name = get_node_by_id(ceph_cluster, node).shortname
            short_names.append(short_name)
        extra_args["limit"] = ','.join(short_names)

    playbook_cfg.update({"extra_vars": extra_vars, "extra_args": extra_args})
    rc = ansible.execute_playbook(playbook, build, **playbook_cfg)
    if rc != 0:
        LOG.error(f"Failed during upgrade (rc = {rc})")
        return rc

    # set build to new version
    LOG.info(f"Setting install_version to {build}")
    test_data["install_version"] = build
    ceph_cluster.rhcs_version = build

    # check if all mon's and osd's are in correct state
    num_osds = ceph_cluster.ceph_demon_stat["osd"]
    num_mons = ceph_cluster.ceph_demon_stat["mon"]
    test_data["ceph-ansible"] = {
        "num-osds": num_osds,
        "num-mons": num_mons,
        "rhbuild": build,
    }

    # compare pre and post upgrade versions
    if skip_version_compare:
        LOG.warning("Skipping version comparison.")
    else:
        if not jewel_minor_update:
            post_upgrade_versions = get_ceph_versions(ceph_nodes, containerized)
            version_compare_fail = compare_ceph_versions(
                pre_upgrade_versions, post_upgrade_versions
            )
            if version_compare_fail:
                return version_compare_fail

    # compare pre and post upgrade container counts
    if containerized:
        post_upgrade_container_counts = get_container_counts(ceph_cluster)
        container_count_fail = compare_container_counts(
            pre_upgrade_container_counts,
            post_upgrade_container_counts,
            prev_install_version,
        )
        if container_count_fail:
            return container_count_fail

    client = ceph_cluster.get_ceph_object("mon")
    cluster_name = ansi_config.get("cluster")
    if build.startswith("5"):
        # Execute Ceph-adm adopt playbook
        playbook_cfg = {"extra_vars": {"ireallymeanit": "yes"}, "verbose": "vvvv"}
        rc = ansible.execute_playbook("cephadm-adopt.yml", build, **playbook_cfg)
        if rc != 0:
            LOG.error(f"Failed during cephadm adopt (rc = {rc})")
            return rc

        LOG.info("The value for parameter build is {}".format(build))
        if build.startswith("5.1"):
            installer = ceph_cluster.get_nodes(role="installer")[0]
            base_cmd = "sudo cephadm shell -- ceph"
            config_cmd = f"{base_cmd} config set mgr mgr/cephadm/yes_i_know true"
            installer.exec_command(cmd=config_cmd)
            mgr_cmd = f"{base_cmd} mgr fail"
            installer.exec_command(cmd=mgr_cmd)

        client = ceph_cluster.get_nodes("mon")[0]
        if config.get("verify_cephadm_containers") and is_legacy_container_present(
            ceph_cluster
        ):
            LOG.info(
                "Checking cluster status to ensure that the legacy services are not being inferred"
            )
            rc = ceph_cluster.check_health(
                build,
                cluster_name=cluster_name,
                client=client,
                timeout=config.get("timeout", 300),
            )
            if rc != 0:
                LOG.error("Ceph health not OK after adopting cluster to use cephadm")
                return rc

    return ceph_cluster.check_health(
        build,
        cluster_name=cluster_name,
        client=client,
        timeout=config.get("timeout", 300),
    )


def compare_ceph_versions(pre_upgrade_versions, post_upgrade_versions):
    """
    Compare pre-upgrade and post-upgrade ceph versions on all non-installer nodes.

    Args:
        pre_upgrade_versions(dict): pre-upgrade ceph versions.
        post_upgrade_versions(dict): post-upgrade ceph versions.

    Returns: 1 if any non-installer version is the same post-upgrade, 0 if versions change.

    """
    for name, version in pre_upgrade_versions.items():
        # skipping node-exporter version check as it not supported
        if name == "node-exporter":
            continue

        # for handling rgw container names during 3.x 'some-rgw' but in 4.x 'some-rgw-rgw0'
        if version.startswith("ceph version 12") and "rgw" in name:
            for rgw_name in post_upgrade_versions.keys():
                if "rgw" in rgw_name and rgw_name.startswith(name):
                    if post_upgrade_versions[rgw_name] == version:
                        LOG.error("Pre upgrade version matches post upgrade version")
                        LOG.error("{}: {} matches".format(name, version))
                        return 1
                    break
            continue

        if "installer" not in name and post_upgrade_versions[name] == version:
            LOG.error("Pre upgrade version matches post upgrade version")
            LOG.error("{}: {} matches".format(name, version))
            return 1
    return 0


def get_container_counts(ceph_cluster):
    """
    Get container counts on all non-installer nodes in the cluster.

    Args:
        ceph_cluster(ceph.ceph.Ceph): ceph cluster to check container counts on.

    Returns:
        dict: container counts for the cluster.

    """
    container_counts = {}
    for node in ceph_cluster.get_nodes(ignore="installer"):
        distro_info = node.distro_info
        distro_ver = distro_info["VERSION_ID"]
        if distro_ver.startswith("8"):
            out, rc = node.exec_command(
                sudo=True, cmd="podman ps | grep $(hostname) | wc -l"
            )
            # In ceph 4.2 onwards ceph-crash as new container got added
            # so decreasing that count to pass compare_container_count function
            crash, rc = node.exec_command(
                sudo=True, cmd="podman ps |grep ceph-crash| wc -l"
            )
        else:
            out, rc = node.exec_command(
                sudo=True, cmd="docker ps | grep $(hostname) | wc -l"
            )
            crash, rc = node.exec_command(
                sudo=True, cmd="docker ps |grep ceph-crash| wc -l"
            )
        count = int(out.rstrip())
        crash_count = int(crash.rstrip())
        count -= crash_count
        LOG.info("{} has {} containers running".format(node.shortname, count))
        container_counts.update({node.shortname: count})
    return container_counts


def compare_container_counts(
    pre_upgrade_counts, post_upgrade_counts, prev_install_version
):
    """
    Compare pre-upgrade and post-upgrade container counts.

    Args:
        pre_upgrade_counts: pre-upgrade container counts.
        post_upgrade_counts: post-upgrade container counts.
        prev_install_version: ceph version pre-upgrade containers were running.
            Skip comparison if this is a jewel version.

    Returns: 1 if a container count mismatch exists, 0 if counts are correct.

    """
    LOG.info("Pre upgrade container counts: {}".format(pre_upgrade_counts))
    LOG.info("Post upgrade container counts: {}".format(post_upgrade_counts))

    for node, count in post_upgrade_counts.items():
        if prev_install_version.startswith("2"):
            # subtract 1 since mgr containers are now collocated on mons
            if "-mon" in node:
                count -= 1
        if pre_upgrade_counts[node] != count:
            LOG.error("Mismatched container count post upgrade")
            return 1
    return 0


def collocate_mons_with_mgrs(ceph_cluster, ansible_dir):
    """
    Configure the hosts file to reflect that mon nodes will be collocated with mgr daemons.

    Args:
        ceph_cluster: cluster to configure mon nodes on.
        ansible_dir: directory of ceph-ansible installation.

    Returns: None

    """
    LOG.info("Adding mons as mgrs in hosts file")
    mon_nodes = [node for node in ceph_cluster.get_nodes(role="mon")]
    ceph_installer = ceph_cluster.get_nodes(role="installer")[0]
    mgr_block = "\n[mgrs]\n"
    for node in mon_nodes:
        mgr_block += node.shortname + " monitor_interface=" + node.eth_interface + "\n"

    host_file = ceph_installer.remote_file(
        sudo=True, file_name="{}/hosts".format(ansible_dir), file_mode="a"
    )
    host_file.write(mgr_block)
    host_file.flush()

    host_file = ceph_installer.remote_file(
        sudo=True, file_name="{}/hosts".format(ansible_dir), file_mode="r"
    )
    host_contents = ""
    with host_file:
        for line in host_file:
            host_contents += line
    host_file.flush()
    LOG.info("Hosts file: \n{}".format(host_contents))
