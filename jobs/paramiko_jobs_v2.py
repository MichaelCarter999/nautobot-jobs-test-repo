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
                    self.logger.warning("stderr: %s", error.strip())

                self.create_file(
                    f"{device.name}-{command.replace(' ', '_')}.txt",
                    output.strip(),
                )

        finally:
            ssh.close()


# ------------------------------------------------------
# Job 2: Change VLAN using VLAN ID
# ------------------------------------------------------

class ParamikoChangeAccessVLAN(Job):
    """Change access VLAN on an interface (EOS safe)."""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    interface = ObjectVar(
        model=Interface,
        query_params={"device_id": "$device", "name__ic": "Ethernet"},
    )
    vlan = IntegerVar(description="Access VLAN ID")

    class Meta:
        name = "Paramiko Change Access VLAN"
        description = "Change access VLAN using Paramiko (EOS/cEOS compatible)"

    def run(self, device_location, device, interface, vlan):
        if device.primary_ip is None:
            self.logger.fatal("Device has no primary IP address.")
            return

        host = device.primary_ip.host
        self.logger.info(
            "Configuring %s on %s: access VLAN %s",
            interface.name,
            device.name,
            vlan,
        )

        ssh = open_ssh(host, username="admin", password="admin")

        try:
            shell = ssh.invoke_shell()
            time.sleep(1)

            # Disable paging (CRITICAL for EOS)
            send_shell_cmd(shell, "terminal length 0")

            send_shell_cmd(shell, "enable")
            send_shell_cmd(shell, "configure terminal")
            send_shell_cmd(shell, f"interface {interface.name}")
            send_shell_cmd(shell, f"switchport access vlan {vlan}")
            send_shell_cmd(shell, "end")
            send_shell_cmd(shell, "write memory")

            self.logger.info(
                "Successfully configured %s VLAN %s on %s",
                interface.name,
                vlan,
                device.name,
            )

        finally:
            ssh.close()


# ------------------------------------------------------
# Job 3: Change VLAN using Nautobot VLAN object
# ------------------------------------------------------

class ParamikoChangeAccessVLANByObject(Job):
    """Change access VLAN using a Nautobot VLAN object."""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    interface = ObjectVar(
        model=Interface,
        query_params={"device_id": "$device", "name__ic": "Ethernet"},
    )
    vlan = ObjectVar(model=VLAN)

    class Meta:
        name = "Paramiko Change Access VLAN (VLAN Object)"
        description = "Change access VLAN using Nautobot VLAN object"

    def run(self, device_location, device, interface, vlan):
        if device.primary_ip is None:
            self.logger.fatal("Device has no primary IP address.")
            return

        host = device.primary_ip.host
        self.logger.info(
            "Configuring %s on %s: VLAN %s (%s)",
            interface.name,
            device.name,
            vlan.name,
            vlan.vid,
        )

        ssh = open_ssh(host, username="admin", password="admin")

        try:
            shell = ssh.invoke_shell()
            time.sleep(1)

            send_shell_cmd(shell, "terminal length 0")
            send_shell_cmd(shell, "enable")
            send_shell_cmd(shell, "configure terminal")
            send_shell_cmd(shell, f"interface {interface.name}")
            send_shell_cmd(shell, f"switchport access vlan {vlan.vid}")
            send_shell_cmd(shell, "end")
            send_shell_cmd(shell, "write memory")

            self.logger.info(
                "Successfully configured %s VLAN %s on %s",
                interface.name,
                vlan.vid,
                device.name,
            )

        finally:
            ssh.close()

