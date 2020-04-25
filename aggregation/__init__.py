import math
import pytz
import datetime
from typing import *
from collections import namedtuple
from multiprocessing import Pool, cpu_count
from parsers import Container, TestHost, Test

import numpy as np
import pandas as pd

CpuEntry = namedtuple('CpuEntry', 'time, total')


def normalize(l):
    min_value = min(l)
    return [i - min_value for i in l]


local = pytz.timezone("America/New_York")
epoch = datetime.datetime.utcfromtimestamp(0)


def scrub_times(times: List[datetime.datetime]) -> List[float]:
    base_timestamps = [(local.localize(dt, is_dst=None).astimezone(pytz.utc).replace(
                            tzinfo=None) - epoch).total_seconds() * 1E3
                       for dt in times]
    return base_timestamps


def cpu_entries(host: TestHost) -> List[CpuEntry]:
    cpu = host.cpu()
    times = cpu[0].keys()
    timestamps = scrub_times(times)

    # Aggregate CPU totals across all cores
    cpu_entries = [CpuEntry(time=ts, total=sum(int(core[time].total()) for core in cpu))
                   for (time, ts) in zip(times, timestamps)]

    return cpu_entries


def aggregate_cpu(host: TestHost, sampling_period=None) -> None:
    cpu, times = zip(*((entry.total, entry.time) for entry in cpu_entries(host)))
    cpu_df = pd.DataFrame({'cpu': cpu, 'time': times})

    if sampling_period is not None:
        min_time = min(times)
        max_time = max(times)
        sampling_period_ms = sampling_period * 1E3
        sampling_intervals = pd.interval_range(
            start=min_time, end=max_time, freq=sampling_period_ms)
        cpu_df['sampling_intervals'] = pd.cut(
            x=cpu_df['time'], bins=sampling_intervals, include_lowest=True)
        cpu_df = cpu_df.groupby('sampling_intervals').mean()

    return cpu_df


def execute(func, iterable, ordered=False):
    """
    Executes the given function across multiple processes
    """

    with Pool(cpu_count()) as pool:
        if not ordered:
            return list(pool.imap_unordered(func, iterable))
        else:
            return list(pool.imap(func, iterable))


def flatten(lists):
    """
    Singly flattens nested list
    """

    return [item for sublist in lists for item in sublist]


def host_collection_intervals(host: TestHost, moby=True, radvisor=True,
                              first=False) -> Union[Optional[List[Tuple[float, float]]],
                                                    List[List[Tuple[float, float]]]]:
    """
    Gets all collection interval lists for a given host
    """

    interval_lists = [collection_intervals(c, moby=moby, radvisor=radvisor)
                      for c in host.containers()]
    if first:
        if interval_lists:
            return interval_lists[0]
        else:
            return None
    else:
        return interval_lists


def collection_intervals(container: Container, moby=True, radvisor=True) -> List[Tuple[float, float]]:
    """
    Gets all collection intervals for a given container
    """

    intervals = []

    if moby and container.moby:
        intervals.extend(get_intervals(container.moby))

    if radvisor and container.radvisor:
        if intervals:
            print(
                "Warning: container has both radvisor and moby logs. Collection intervals will no longer correspond to PIT")
        intervals.extend(get_intervals(container.radvisor[0]))

    return intervals


def get_intervals(entries: Dict[int, object]) -> List[Tuple[float, float]]:
    """
    Gets timestamp deltas in milliseconds
    """

    reads = [float(read) / 1E6 for read in entries.keys()]
    return list(zip(find_deltas(reads), reads[1:]))


def find_deltas(arr):
    """
    Creates a new array that is the differences between consecutive elements in
    a numeric series. The new array is len(arr) - 1
    """

    return [j-i for i, j in zip(arr[:-1], arr[1:])]
