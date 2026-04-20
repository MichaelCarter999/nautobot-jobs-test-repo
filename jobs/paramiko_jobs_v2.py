"""
Paramiko-based Jobs for Arista EOS / cEOS (Containerlab-safe)

- Show commands use exec_command() (no paging, no hangs)
- Config commands use invoke_shell() with terminal length 0
"""

import time
import paramiko

from nautobot.apps.jobs import (
    Job,
    ObjectVar,
    MultiChoiceVar,
    IntegerVar,
    register_jobs,
)
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import VLAN
from nautobot.dcim.models.locations import Location


name = "Network Operations"


COMMAND_CHOICES = (
    ("show ip interface brief", "show ip interface brief"),
    ("show ip route", "show ip route"),
    ("show version", "show version"),
    ("show vlan brief", "show vlan brief"),
    ("show interfaces status", "show interfaces status"),
)


# ------------------------------------------------------
# Utility helpers
# ------------------------------------------------------

def open_ssh(host, username, password, timeout=15):
    """Open and return a Paramiko SSH client."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=timeout,
    )
    return ssh


def send_shell_cmd(shell, cmd, wait=0.3):
    """Send a command to an interactive shell and return output."""
    shell.send(cmd + "\n")
    time.sleep(wait)

    output = ""
    while shell.recv_ready():
        output += shell.recv(65535).decode("utf-8")

    return output.strip()


# ------------------------------------------------------
# Job 1: Run SHOW commands (safe + fast)
# ------------------------------------------------------

class ParamikoShowCommands(Job):
    """Run show commands on EOS using Paramiko exec_command()."""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    commands = MultiChoiceVar(choices=COMMAND_CHOICES)

    class Meta:
        name = "Paramiko Show Commands (EOS Safe)"
        description = "Run show commands on EOS/cEOS using Paramiko exec_command()"

    def run(self, device_location, device, commands):
        if device.primary_ip is None:
            self.logger.fatal("Device has no primary IP address.")
            return

        host = device.primary_ip.host
        self.logger.info("Connecting to %s (%s)", device.name, host)

        ssh = open_ssh(host, username="admin", password="admin")

        try:
            for command in commands:
                self.logger.info("Running: %s", command)

                stdin, stdout, stderr = ssh.exec_command(
                    command,
                    timeout=10,
                )

                output = stdout.read().decode("utf-8")
                error = stderr.read().decode("utf-8")

                if error:
