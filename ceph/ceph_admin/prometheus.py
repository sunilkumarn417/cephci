"""Module to deploy Prometheus service and individual daemon(s)."""
from typing import Dict

from .apply import ApplyMixin
from .helper import set_custom_monitoring_svc_image
from .orch import Orch


class Prometheus(ApplyMixin, Orch):
    SERVICE_NAME = "prometheus"

    def apply(self, config: Dict) -> None:
        """
        Deploy the Prometheus service using the provided configuration.

        Args:
            config: Key/value pairs provided by the test case to create the service.

        Example
            config:
                command: apply
                service: prometheus
                base_cmd_args:          # arguments to ceph orch
                    concise: true
                    verbose: true
                    input_file: <name of spec>
                args:
                    placement:
                        label: prometheus    # either label or node.
                        nodes:
                            - node1
                        limit: 3    # no of daemons
                        sep: " "    # separator to be used for placements
                    dry-run: true
                    unmanaged: true
        """
        if config.get("custom_image", None):
            # In case of custom image,
            # set prometheus container image before deploying prometheus service
            set_custom_monitoring_svc_image(
                self, self.SERVICE_NAME, config.get("custom_image")
            )

        super().apply(config=config)
