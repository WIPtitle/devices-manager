import shutil

from sqlmodel import SQLModel


class DiskUsage(SQLModel):
    total: int
    used: int
    free: int

    @classmethod
    def from_path(cls, path):
        total, used, free = shutil.disk_usage(path)
        return cls(total=total, used=used, free=free)
