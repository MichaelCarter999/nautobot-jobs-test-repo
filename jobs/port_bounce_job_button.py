from nautobot.apps.jobs import Job, register_jobs, JobButtonReceiver
from netmiko import ConnectHandler

name = "Network Operations"

class PortBouncerButton(JobButtonReceiver):

    """Bounce Ports via Netmiko and Job Button."""
   
    class Meta:
        name = "Bounce Interface ports"
        has_sensitive_variables = False
        description = "Bounce Interface Port"

    def receive_job_button(self, obj):
        self.logger.info("Running job button receiver.", extra={"object": obj})
        if obj.device.primary_ip is None:
            self.logger.fatal("Device does not have a primary IP address set.")
            return

        if obj.device.platform is None:
            self.logger.fatal("Device does not have a platform set.")
            return

        if obj.device.platform.network_driver_mappings.get("netmiko") is None:
            self.logger.fatal("Device mapping for Netmiko is not present, please set.")
            return

        
        # Connect to the device, get some output - comment this out if you are simulating
        net_connect = ConnectHandler(
            device_type=obj.device.platform.network_driver_mappings["netmiko"],
            host=obj.device.primary_ip.host,  # or device.name if your name is an FQDN
            username="admin",
            password="admin",
        )

        # Easy mapping of platform to device command
        COMMAND_MAP = {
            "cisco_nxos": [f"interface {obj}", f"shut", f"no shut"],
            "arista_eos": [f"interface {obj}", f"shut", f"no shut",],
        }

        commands = COMMAND_MAP[obj.device.platform.network_driver_mappings.get("netmiko")]
        self.logger.info(f"This is the command: {commands}")
        net_connect.enable()
        net_connect.send_config_set(commands)
        net_connect.disconnect()

        self.logger.info(f"Successfully bounced port {obj} on {obj.device}!")
 
