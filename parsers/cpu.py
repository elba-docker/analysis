import datetime
import sys
from collections import OrderedDict


class CpuEntry:
    """A CPU entry."""

    def __init__(self, user, nice, system, wait, irq, soft, steal, idle, total, guest, guest_n,
                 intrpt, timestamp):
        """Initialize a CpuEntry."""
        self._user = user
        self._nice = nice
        self._system = system
        self._wait = wait
        self._irq = irq
        self._soft = soft
        self._steal = steal
        self._idle = idle
        self._total = total
        self._guest = guest
        self._guest_n = guest_n
        self._intrpt = intrpt
        self._timestamp = timestamp

    def user(self):
        return self._user

    def nice(self):
        return self._nice

    def system(self):
        return self._system

    def wait(self):
        return self._wait

    def irq(self):
        return self._irq

    def soft(self):
        return self._soft

    def steal(self):
        return self._steal

    def idle(self):
        return self._idle

    def total(self):
        return self._total

    def guest(self):
        return self._guest

    def guest_n(self):
        return self._guest_n

    def intrpt(self):
        return self._intrpt

    def time(self):
        return self._timestamp


def main(iterator):
    # List of timestamps and CpuEntry for each CPU.
    # timestamps = []
    cpu_entries = []
    # Process CPU raw file.
    for cpu_line in iterator:
        # Check if it is a comment.
        if cpu_line[0] == '#':
            continue
        cpu_entry_data = cpu_line.split()
        timestamp_str = f"{cpu_entry_data[0]} {cpu_entry_data[1]}"
        timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S.%f")
        for cpu_no in range((len(cpu_entry_data) - 2) // 12):
            if len(cpu_entries) < cpu_no + 1:
                cpu_entries.append(OrderedDict())
            cpu_entries[cpu_no][timestamp] = CpuEntry(
                *cpu_entry_data[cpu_no * 12 + 2:cpu_no * 12 + 14], timestamp)

    return cpu_entries
