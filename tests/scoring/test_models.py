# ABOUTME: Tests for scoring models and rating structures
# ABOUTME: Validates ConditionRating data structure and rating ranges

from app.scoring.models import ConditionRating


def test_condition_rating_stores_all_fields():
    """ConditionRating should store rating, mode, and description"""
    rating = ConditionRating(
        score=7,
        mode="sup",
        description="Decent conditions, get out there!"
    )

    assert rating.score == 7
    assert rating.mode == "sup"
    assert rating.description == "Decent conditions, get out there!"


def test_condition_rating_validates_score_range():
    """ConditionRating score should be 1-10"""
    # Valid scores
    rating = ConditionRating(score=1, mode="sup", description="test")
    assert rating.score == 1

    rating = ConditionRating(score=10, mode="sup", description="test")
    assert rating.score == 10

    # Invalid scores should raise
    try:
        ConditionRating(score=0, mode="sup", description="test")
        assert False, "Should raise ValueError for score < 1"
    except ValueError:
        pass

    try:
        ConditionRating(score=11, mode="sup", description="test")
        assert False, "Should raise ValueError for score > 10"
    except ValueError:
        pass
