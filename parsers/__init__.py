
import os
import weakref
import itertools
import re
from collections import namedtuple
from dataclasses import dataclass
from typing import *

import parsers.nbench
import parsers.radvisor
import parsers.moby
import parsers.config
import parsers.cpu
import parsers.disk
import parsers.memory
import parsers.milliscope
from parsers.extract import extract_all, get_unique_name, get_all_files


MilliscopePaths = namedtuple('MilliscopePaths', 'connect recvfrom sendto')
CollectlPaths = namedtuple('CollectlPaths', 'memory cpu disk')
ContainerPaths = namedtuple('ContainerPaths', 'moby radvisor nbench')
Container = namedtuple('Container', 'moby radvisor nbench id')


# Weak referenceable
class WeakRefList(list):
    pass

# Weak referenceable


class WeakRefDict(dict):
    pass


@dataclass
class TestHost:
    # Ids
    id: str
    kind: str
    test_id: str
    replica_id: str
    # Path tuples
    container_paths: ContainerPaths
    milliscope_paths: MilliscopePaths
    collectl_paths: CollectlPaths
    # Cached weakrefs to values
    milliscope_connect = None
    milliscope_recvfrom = None
    milliscope_sendto = None
    collectl_memory = None
    collectl_cpu = None
    collectl_disk = None
    containers_ref = None

    def containers(self) -> List[Container]:
        if self.container_paths:
            if not self.containers_ref or not self.containers_ref():
                parsed = parse_containers(self.container_paths)
                if parsed:
                    self.containers_ref = weakref.ref(parsed)
                return parsed
            else:
                return self.containers_ref()
        else:
            return []

    def connect(self):
        if not self.milliscope_connect or not self.milliscope_connect():
            parsed = parse_milliscope_connect(self.milliscope_paths.connect)
            if parsed:
                self.milliscope_connect = weakref.ref(parsed)
            return parsed
        else:
            return self.milliscope_connect()

    def recvfrom(self):
        if not self.milliscope_recvfrom or not self.milliscope_recvfrom():
            parsed = parse_milliscope_recvfrom(self.milliscope_paths.recvfrom)
            if parsed:
                self.milliscope_recvfrom = weakref.ref(parsed)
            return parsed
        else:
            return self.milliscope_connect()

    def sendto(self):
        if not self.milliscope_sendto or not self.milliscope_sendto():
            parsed = parse_milliscope_sendto(self.milliscope_paths.sendto)
            if parsed:
                self.milliscope_sendto = weakref.ref(parsed)
            return parsed
        else:
            return self.milliscope_connect()

    def cpu(self):
        if not self.collectl_cpu or not self.collectl_cpu():
            parsed = WeakRefList(parse_collectl_cpu(self.collectl_paths.cpu))
            if parsed:
                self.collectl_cpu = weakref.ref(parsed)
            return parsed
        else:
            return self.collectl_cpu()

    def memory(self):
        if not self.collectl_memory or not self.collectl_memory():
            parsed = WeakRefList(parse_collectl_memory(self.collectl_paths.memory))
            if parsed:
                self.collectl_memory = weakref.ref(parsed)
            return parsed
        else:
            return self.collectl_cpu()

    def disk(self):
        if not self.collectl_disk or not self.collectl_disk():
            parsed = WeakRefList(parse_collectl_disk(self.collectl_paths.disk))
            if parsed:
                self.collectl_disk = weakref.ref(parsed)
            return parsed
        else:
            return self.collectl_cpu()


@dataclass
class TestReplica:
    id: str
    test_id: str
    hosts: Dict[str, TestHost]
    # Paths
    config_path: str
    # Cached weakrefs to values
    config_sh = None

    def config(self) -> Optional[Dict[str, Union[int, str]]]:
        if not self.config_sh or not self.config_sh():
            parsed = WeakRefDict(parse_config(self.config_path))
            if parsed:
                self.config_sh = weakref.ref(parsed)
            return parsed
        else:
            return self.config_sh()

    def single(self) -> Optional[TestHost]:
        return next(iter(self.hosts.values()))


@dataclass
class Test:
    id: str
    replicas: List[TestReplica]


SINGLE_HOST_TEST_PREFIXES = ["d", "i"]
HOST_KIND_REGEX = re.compile(r"^log-([^-]+)-")
CONTAINER_ID_REGEX = re.compile(r"^([^_]+)(?:_[^_]+)?$")


def archive_name(path):
    """
    Gets the name of a .tar.gz file without the extension
    """

    return os.path.basename(path).split('.')[0]


def main(root, working_dir="./working") -> Dict[str, Test]:
    """
    Extracts and parses all archives in the given directory into lazy loadable parsed test classes
    """

    # Extract all archives
    archives = extract_all(root, working_dir=working_dir)

    test_dict = {}
    for test_archive in archives:
        test_id = archive_name(test_archive)
        extracted_path = os.path.join(working_dir, get_unique_name(test_archive))
        test_dict[test_id] = parse_test(test_id, extracted_path)
    return test_dict


def parse_test(test_id, test_root) -> Test:
    """
    Parses a test into a lazy-loaded Test object
    """

    replicas = []
    results_path = os.path.join(test_root, "results")
    all_archives = get_all_files(results_path, ext=".tar.gz", deep=False)
    for replica_archive in all_archives:
        extracted_path = os.path.join(results_path, get_unique_name(replica_archive))
        replica_id = archive_name(extracted_path)
        # Parse the test replica
        replica_result = parse_replica(test_id, replica_id, extracted_path)
        # Sometimes replicas can be lists (if the given archive contains many replicas)
        if isinstance(replica_result, list):
            replicas.extend(replica_result)
        else:
            replicas.append(replica_result)
    return Test(id=test_id, replicas=replicas)


def parse_replica(test_id, replica_id, replica_root) -> Union[TestReplica, List[TestReplica]]:
    """
    Parses a single or multiple replicas into lazy-loaded TestReplica object(s)
    """

    config_path = os.path.join(replica_root, "conf", "config.sh")
    if not os.path.exists(config_path):
        config_path = None

    all_archives = get_all_files(replica_root, ext=".tar.gz", deep=False)
    hosts = {}
    for host_archive in all_archives:
        extracted_path = os.path.join(replica_root, get_unique_name(host_archive))
        host_id = archive_name(extracted_path)
        host = parse_host(test_id, replica_id, host_id, extracted_path)
        if host.kind in hosts:
            hosts[host.id] = host
        else:
            hosts[host.kind] = host
    if any(test_id.startswith(f"{i}-") for i in SINGLE_HOST_TEST_PREFIXES):
        # Single-host test, so each host is actually a replica
        return [TestReplica(test_id=test_id, id=f"{replica_id}-{host.id}",
                            hosts={"host": host}, config_path=config_path)
                for host in hosts.values()]
    else:
        # Multiple-host
        return TestReplica(test_id=test_id, id=replica_id, hosts=hosts, config_path=config_path)


def parse_host(test_id, replica_id, host_id, host_root):
    """
    Parses a single host into a lazy-loaded TestHost
    """

    connect_path = try_path(host_root, "milliscope", "spec_connect.csv")
    recvfrom_path = try_path(host_root, "milliscope", "spec_recvfrom.csv")
    sendto_path = try_path(host_root, "milliscope", "spec_sendto.csv")
    milliscope_paths = MilliscopePaths(
        connect=connect_path, recvfrom=recvfrom_path, sendto=sendto_path)

    cpu_path = try_ext_in_path(".cpu", host_root, "collectl")
    disk_path = try_ext_in_path(".dsk", host_root, "collectl")
    memory_path = try_ext_in_path(".tab", host_root, "collectl")
    collectl_paths = CollectlPaths(cpu=cpu_path, disk=disk_path, memory=memory_path)

    radvisor_paths = sorted(try_all_in_path(".log", host_root, "radvisor"))
    moby_paths = sorted(try_all_in_path(".log", host_root, "moby"))
    nbench_paths = sorted(try_all_in_path(".log", host_root, "nbench"))
    containers = [ContainerPaths(moby=moby, radvisor=radvisor, nbench=nbench)
                  for (moby, radvisor, nbench)
                  in itertools.zip_longest(moby_paths, radvisor_paths, nbench_paths)]

    host_match = re.search(HOST_KIND_REGEX, host_id)
    host_kind = host_match.group(1) if host_match else host_id

    return TestHost(id=host_id, kind=host_kind, test_id=test_id, replica_id=replica_id,
                    container_paths=containers, collectl_paths=collectl_paths,
                    milliscope_paths=milliscope_paths)


def try_all_in_path(ext, *segments):
    """
    Gets all files matching the extension in the folder path built from the given segments if the
    folder exists
    """

    constructed_dir_path = os.path.join(*segments)
    if not os.path.exists(constructed_dir_path):
        return []

    return get_all_files(constructed_dir_path, ext=ext, deep=True)


def try_ext_in_path(ext, *segments):
    """
    Gets the first file matching the extension in the folder path built from the given segments if
    the folder exists and a file exists, else None
    """

    constructed_dir_path = os.path.join(*segments)
    if not os.path.exists(constructed_dir_path):
        return None

    files = get_all_files(constructed_dir_path, ext=ext, deep=True)
    if files:
        return files[0]
    else:
        return None


def try_path(*segments):
    """
    Gets the path built from the given segments if it exists, else None
    """

    constructed_path = os.path.join(*segments)
    if not os.path.exists(constructed_path):
        return None
    else:
        return constructed_path

# ? ================
# ? Parser functions
# ? ================


def parse_containers(container_paths: List[ContainerPaths]) -> List[Container]:
    containers = WeakRefList()
    for paths in container_paths:
        moby = parse_moby(paths.moby)
        radvisor = parse_radvisor(paths.radvisor)
        nbench = parse_nbench(paths.nbench)
        # Determine container Id
        container_id = None
        for path in [paths.moby, paths.radvisor, paths.nbench]:
            if path:
                basename = os.path.basename(path)
                without_ext = os.path.splitext(basename)[0]
                match_obj = re.search(CONTAINER_ID_REGEX, without_ext)
                if match_obj:
                    container_id = match_obj.group(1)

        containers.append(Container(moby=moby, radvisor=radvisor, nbench=nbench, id=container_id))
    return containers


def parse_nbench(nbench_path):
    if nbench_path is None:
        return None
    try:
        with open(nbench_path, 'r') as file:
            return nbench.main(iter(file))
    except OSError:
        return None


def parse_radvisor(radvisor_path):
    if radvisor_path is None:
        return None
    try:
        with open(radvisor_path, 'r') as file:
            return radvisor.main(iter(file))
    except OSError:
        return None


def parse_moby(moby_path):
    if moby_path is None:
        return None
    try:
        with open(moby_path, 'r') as file:
            return moby.main(iter(file))
    except OSError:
        return None


def parse_config(config_path: Optional[str]):
    if config_path is None:
        return None
    try:
        with open(config_path, 'r') as file:
            return config.main(iter(file))
    except OSError:
        return None


def parse_milliscope_connect(connect_path: Optional[str]):
    if connect_path is None:
        return None
    try:
        with open(connect_path, 'r') as file:
            return milliscope.spec_connect(iter(file))
    except OSError:
        return None


def parse_milliscope_recvfrom(recvfrom_path: Optional[str]):
    if recvfrom_path is None:
        return None
    try:
        with open(recvfrom_path, 'r') as file:
            return milliscope.main(iter(file))
    except OSError:
        return None


def parse_milliscope_sendto(sendto_path: Optional[str]):
    if sendto_path is None:
        return None
    try:
        with open(sendto_path, 'r') as file:
            return milliscope.main(iter(file))
    except OSError:
        return None


def parse_collectl_cpu(cpu_path: Optional[str]):
    if cpu_path is None:
        return None
    try:
        with open(cpu_path, 'r') as file:
            return cpu.main(iter(file))
    except OSError:
        return None


def parse_collectl_memory(memory_path: Optional[str]):
    if memory_path is None:
        return None
    try:
        with open(memory_path, 'r') as file:
            return memory.main(iter(file))
    except OSError:
        return None


def parse_collectl_disk(disk_path: Optional[str]):
    if disk_path is None:
        return None
    try:
        with open(disk_path, 'r') as file:
            return disk.main(iter(file))
    except OSError:
        return None
