from enum import IntEnum, Enum

class TaskStatus(IntEnum):
    ACTIVE = 0
    COMPLETED = 1

class TaskImportance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"