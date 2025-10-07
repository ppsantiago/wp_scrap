# app/models/__init__.py
from .domain import Domain, Report, Comment, TrustedContact, ReportPrompt, ReportGenerationLog
from .job import Job, JobStep, JobStatus, JobType

__all__ = [
    "Domain",
    "Report",
    "Comment",
    "TrustedContact",
    "ReportPrompt",
    "ReportGenerationLog",
    "Job",
    "JobStep",
    "JobStatus",
    "JobType",
]
