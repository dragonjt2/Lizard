from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple


@dataclass
class PendingKidnap:
    initiator_id: int
    created_at: datetime
    due_at: Optional[datetime] = None


@dataclass
class BotState:
    guild_timers: Dict[int, Optional[datetime]] = field(default_factory=dict)
    kidnap_immunity: Dict[Tuple[int, int], datetime] = field(default_factory=dict)
    pending_kidnaps: Dict[Tuple[int, int], PendingKidnap] = field(default_factory=dict)


__all__ = ["BotState", "PendingKidnap"]
