# ABOUTME: Data models for condition ratings and recommendations
# ABOUTME: Provides structured representation of scores and foil setups

from dataclasses import dataclass


@dataclass
class ConditionRating:
    """Rating for current conditions"""
    score: int  # 1-10
    mode: str   # "sup" or "parawing"
    description: str  # Snarky description from LLM

    def __post_init__(self):
        if not 1 <= self.score <= 10:
            raise ValueError(f"Score must be 1-10, got {self.score}")
