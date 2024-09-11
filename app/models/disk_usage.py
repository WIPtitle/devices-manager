import shutil

from sqlmodel import SQLModel


class DiskUsage(SQLModel):
    total: int
    used: int
    free: int

    def __init__(self, total, used, free):
        super().__init__()
        self.total = total
        self.used = used
        self.free = free

    @classmethod
    def from_path(cls, path):
        total, used, free = shutil.disk_usage(path)
        return cls(total, used, free)
