from typing import Any

import docker
import logging
import time
import threading
from itertools import chain
from functools import lru_cache

from dnslib.proxy import ProxyResolver
from dnslib.server import DNSServer, DNSHandler
from dnslib import DNSRecord, DNSLabel, QTYPE, RR

from docker_resolver.resolv import ResolvConf

logger = logging.getLogger(__name__)

container_hostnames = set()

class HostnameCacheManager(threading.Thread):
    """Manage the cache of container hostnames.

    Listens for container-related events from the Docker daemon and rebuilds the hostname cache.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.client = docker.from_env()
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """Listen for container-related events and update the cache."""
        self.rebuild_cache()

        for event in self.client.events(decode=True):
            if event["Type"] != "container":
              continue
            self.rebuild_cache()

    def rebuild_cache(self) -> None:
        """Rebuild the global container hostname cache."""
        global container_hostnames

        print("Rebuilding container hostname cache...")

        for container in self.client.containers.list():
            # Add the container name and hostname for all containers.
            container_hostnames.add(container.attrs['Name'].strip('/'))
            container_hostnames.add(container.attrs['Config']['Hostname'])

            # Add network aliases if any are configured.
            for network in container.attrs['NetworkSettings']['Networks'].values():
                for alias in network.get('Aliases') or []:
                    container_hostnames.add(alias)

            # If the container is part of a compose project, add its service name and qualified service name.
            labels = container.attrs["Config"]["Labels"]
            if "com.docker.compose.project" in labels:
                project = labels["com.docker.compose.project"]
                service = labels["com.docker.compose.service"]
                container_hostnames.add(f"{project}-{service}")
                container_hostnames.add(service)

        print(f"New container hostnames: {', '.join(sorted(container_hostnames))}")


class LocalContainerResolver(ProxyResolver):
    """Resolve DNS queries for running container hostnames to 127.0.0.1."""

    resolve_conf: ResolvConf

    def __init__(self) -> None:
        self.resolve_conf = ResolvConf("/etc/resolv.conf")
        self.upstream_resolver = upstream = self.resolve_conf.nameserver[0]
        super().__init__(address=self.upstream_resolver, port=53, timeout=5)

    def resolve(self, request: DNSRecord, handler: DNSHandler) -> DNSRecord:
        """Resolve the given DNS request.

        If the request is for the hostname of a container running on the host, return 127.0.0.1.

        Otherwise, send the request to the upstream resolver.
        """
        reply = request.reply()
        for question in request.questions:
            if self.is_container_hostname(question.qname):
                reply.add_answer(*RR.fromZone(f'{question.qname} 60 IN A 127.0.0.1'))
        # If the requested hostname was not for a docker container, send the request upstream.
        return reply if reply.rr else super().resolve(request, handler)

    def is_container_hostname(self, qname: DNSLabel) -> bool:
        """Return True if the given qname matches a running Docker container."""
        qualified_hostname = '.'.join(p.decode() for p in qname.label)
        global container_hostnames
        return qualified_hostname in container_hostnames

if __name__ == "__main__":
    # Start the cache manager for Docker container hostnames
    cache_manager = HostnameCacheManager()
    cache_manager.start()

    # Start the DNS server.
    resolver = LocalContainerResolver()
    dns_server = DNSServer(resolver=resolver, address="0.0.0.0", port=53)
    dns_server.start_thread()
    print("DNS server listening on port 53...")

    try:
        cache_manager.join()
        dns_server.thread.join()
    except KeyboardInterrupt:
        print("Exited.")
