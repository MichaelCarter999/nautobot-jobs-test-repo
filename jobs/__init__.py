from nautobot.apps.jobs import register_jobs
from .hello_jobs import HelloJobs
from .paramiko_jobs import ParamikoCommandRunner, ParamikoChangeVLAN, ParamikoChangeVLAN_by_Function

register_jobs(
    HelloJobs,
    ParamikoCommandRunner,
    ParamikoChangeVLAN,
    ParamikoChangeVLAN_by_Function,
)
