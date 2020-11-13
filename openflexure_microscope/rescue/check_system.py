from urllib.error import URLError
from urllib.request import urlopen

import psutil

from .error_sources import WarningSource


def internet_on():
    test_urls = (
        "https://build.openflexure.org",  # Bath server
        "https://openflexure.org",  # GitHub pages
    )
    for url in test_urls:
        try:
            urlopen(url, timeout=10)
            # If any test passes, return True
            return True
        except URLError:
            pass
    # If no test passed, return False
    return False


def main():
    error_sources = []

    # Check internet
    if not internet_on():
        error_sources.append(
            WarningSource(
                "No internet connection detected. Updates may not be available."
            )
        )

    # Check memory
    mem = psutil.virtual_memory()
    total_gb = mem.total / 1e9

    if total_gb <= 1:
        error_sources.append(
            WarningSource(
                (
                    "Less than 1GB total memory available.",
                    "For small scans, or control from another device, this is usually fine.",
                    "\n    More complex usage may require additional resources.",
                )
            )
        )

    # Check disks
    data_partitions = [
        disk
        for disk in psutil.disk_partitions()
        if "rw" in disk.opts and disk.mountpoint != "/boot"
    ]
    for part in data_partitions:
        usage = psutil.disk_usage(part.mountpoint)
        if int(usage.percent) >= 90:
            error_sources.append(
                WarningSource(
                    (
                        f"Disk {part.device}, at {part.mountpoint} is {int(usage.percent)}% full.",
                        "Captures may fail to save soon.",
                    )
                )
            )

    return error_sources
