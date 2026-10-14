"""Chaos test: disk pressure on the server node.

Fills the root filesystem to a configurable threshold and verifies that the API remains healthy once the space is released. 
Excluded from automated runs: above roughly 85% usage the kubelet begins evicting pods, so the test must be run manually under supervision.
"""
import os
import subprocess

import pytest

from support.waiting import wait_until


@pytest.mark.manual
def test_disk_fill_is_observable_and_cleanable(api):
    target = int(os.getenv("DISK_FILL_TARGET_PCT", "80"))
    path = os.getenv("DISK_FILL_PATH", "/var/tmp/motorsport_fill")
    st = os.statvfs("/")
    total, avail = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
    used_pct = 100 * (total - avail) / total
    if used_pct >= target:
        pytest.skip(f"root filesystem already at {used_pct:.0f}% (target {target}%)")

    try:
        subprocess.run(["fallocate", "-l", str(int(total * target / 100 - (total - avail))), path],
                       check=True)
        st = os.statvfs("/")
        assert 100 * (1 - st.f_bavail / st.f_blocks) >= target - 1
    finally:
        if os.path.exists(path):
            os.remove(path)
    wait_until(api.is_healthy, timeout=60, desc="API healthy after cleanup")