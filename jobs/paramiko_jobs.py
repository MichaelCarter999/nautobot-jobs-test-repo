import os
import paramiko
import time
from django.conf import settings
from nautobot.apps.jobs import MultiChoiceVar, Job, ObjectVar, register_jobs, StringVar, IntegerVar
from nautobot.dcim.models.locations import Location
from nautobot.dcim.models.devices import Device
from nautobot.dcim.models.device_components import Interface
from nautobot.ipam.models import VLAN
from nautobot.apps.jobs import JobButtonReceiver


name = "Network Operations"


COMMAND_CHOICES = (
    ("show ip interface brief", "show ip int bri"),
    ("show ip route", "show ip route"),
    ("show version", "show version"),
    ("show log", "show log"),
    ("show vlan", "show vlan"),
    ("show ip ospf neighbor", "show ip ospf neighbor"),
)


class ParamikoCommandRunner(Job):
    """Paramiko equivalent of CommandRunner2 - works with Containerlab vEOS"""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    commands = MultiChoiceVar(choices=COMMAND_CHOICES)

    class Meta:
        name = "Paramiko Command Runner"
        description = "Run show commands using raw Paramiko SSH (Containerlab vEOS compatible)"

    def run(self, device_location, device, commands):
        self.logger.info("Device name: %s", device.name)

        if device.primary_ip is None:
            self.logger.fatal("Device does not have a primary IP address set.")
            return

        # Raw Paramiko SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                device.primary_ip.host,
                username="admin",
                password="admin",
                timeout=30
            )
            shell = ssh.invoke_shell()
            time.sleep(1)

            def send_cmd(cmd):
                shell.send(cmd + "\n")
                time.sleep(2)
                output = ""
                while shell.recv_ready():
                    output += shell.recv(65535).decode('utf-8')
                return output.strip()

            # Run commands
            for command in commands:
                self.logger.info(f"Running: {command}")
                output = send_cmd(command)
                self.create_file(f"{device.name}-{command.replace(' ', '_')}.txt", output)
                self.logger.info(f"Output saved for {command}")

        finally:
            ssh.close()


class ParamikoChangeVLAN(Job):
    """Paramiko VLAN change - Containerlab vEOS compatible"""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    interface = ObjectVar(
        model=Interface,
        query_params={"device_id": "$device", "name__ic": "Ethernet"}
    )
    vlan = IntegerVar()

    class Meta:
        name = "Paramiko Change VLAN for Port"
        description = "Change VLAN using raw Paramiko SSH"

    def run(self, device_location, device, interface, vlan):
        self.logger.info(f"Device: {device.name}, Interface: {interface}")

        if device.primary_ip is None:
            self.logger.fatal("Device does not have a primary IP address set.")
            return

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                device.primary_ip.host,
                username="admin",
                password="admin",
                timeout=30
            )
            shell = ssh.invoke_shell()
            time.sleep(1)

            def send_cmd(cmd):
                shell.send(cmd + "\n")
                time.sleep(2)
                output = ""
                while shell.recv_ready():
                    output += shell.recv(65535).decode('utf-8')
                return output.strip()

            # Config workflow
            send_cmd("enable")
            send_cmd("configure terminal")
            time.sleep(1)

            send_cmd(f"interface {interface.name}")
            send_cmd(f"switchport access vlan {vlan}")
            send_cmd("end")
            send_cmd("write memory")

            self.logger.info(f"Configured {interface.name} VLAN {vlan} on {device.name}")

        finally:
            ssh.close()


class ParamikoChangeVLAN_by_Function(Job):
    """Paramiko VLAN change using existing VLAN object"""

    device_location = ObjectVar(model=Location, required=False)
    device = ObjectVar(
        model=Device,
        query_params={"location": "$device_location"},
    )
    interface = ObjectVar(
        model=Interface,
        query_params={"device_id": "$device", "name__ic": "Ethernet"}
    )
    vlan = ObjectVar(model=VLAN)

    class Meta:
        name = "Paramiko Change VLAN by VLAN Object"
        description = "Change VLAN using VLAN object VID"

    def run(self, device_location, device, interface, vlan):
        self.logger.info(f"Device: {device.name}, VLAN: {vlan.name} (VID: {vlan.vid})")

        if device.primary_ip is None:
            self.logger.fatal("Device does not have a primary IP address set.")
            return

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                device.primary_ip.host,
                username="admin",
                password="admin",
                timeout=30
            )
            shell = ssh.invoke_shell()
            time.sleep(1)

            def send_cmd(cmd):
                shell.send(cmd + "\n")
                time.sleep(2)
                output = ""
                while shell.recv_ready():
                    output += shell.recv(65535).decode('utf-8')
                return output.strip()

            # Config workflow
            send_cmd("enable")
            send_cmd("configure terminal")
            time.sleep(1)

            send_cmd(f"interface {interface.name}")
            send_cmd(f"switchport access vlan {vlan.vid}")
            send_cmd("end")
            send_cmd("write memory")

            self.logger.info(f"Configured VLAN {vlan.name} ({vlan.vid}) on {interface.name}")

        finally:
            ssh.close()
