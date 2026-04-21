from nautobot.apps.jobs import register_jobs
from .hello_jobs import HelloJobs
from .paramiko_jobs import ParamikoCommandRunner, ParamikoChangeVLAN, ParamikoChangeVLAN_by_Function
from .paramiko_jobs_v2 import ParamikoShowCommands, ParamikoChangeAccessVLAN, ParamikoChangeAccessVLANByObject
# from .port_bounce_job_button import PortBouncerButton

register_jobs(
    HelloJobs,
    ParamikoCommandRunner,
    ParamikoChangeVLAN,
    ParamikoChangeVLAN_by_Function,
    PortBouncerButton,
    ParamikoShowCommands,
    ParamikoChangeAccessVLAN,
    ParamikoChangeAccessVLANByObject,
    FileUpload,
)
