from app.seed.master_data import DEFAULT_LEVELS
from app.services import scoring as s


def test_normalize_linear_and_reverse():
    assert s.normalize(1) == 0 and s.normalize(5) == 100 and s.normalize(3) == 50
    assert s.normalize(5, reverse=True) == 0 and s.normalize(2, reverse=True) == 75
    assert s.normalize(None) is None


def test_levels_boundaries():
    assert s.level_for(0, DEFAULT_LEVELS) == "Needs Attention"
    assert s.level_for(39.99, DEFAULT_LEVELS) == "Needs Attention"
    assert s.level_for(40, DEFAULT_LEVELS) == "Developing"
    assert s.level_for(60, DEFAULT_LEVELS) == "Balanced"
    assert s.level_for(75, DEFAULT_LEVELS) == "Good"
    assert s.level_for(90, DEFAULT_LEVELS) == "Thriving"
    assert s.level_for(None, DEFAULT_LEVELS) == s.INSUFFICIENT


def test_missing_answers_are_excluded_not_zero():
    items = [s.ItemResult("a", 1, 100), s.ItemResult("b", 1, None), s.ItemResult("c", 1, 50), s.ItemResult("d", 1, None)]
    r = s.score_category("X", items, 75, DEFAULT_LEVELS, 0.5)
    assert r.score == 75 and r.coverage == 0.5 and r.answered == 2


def test_weighted_average():
    items = [s.ItemResult("a", 3, 100), s.ItemResult("b", 1, 0)]
    assert s.score_category("X", items, 75, DEFAULT_LEVELS, 0.5).score == 75


def test_insufficient_coverage_gives_no_score():
    items = [s.ItemResult("a", 1, 100)] + [s.ItemResult(x, 1, None) for x in "bcd"]
    r = s.score_category("X", items, 75, DEFAULT_LEVELS, 0.5)
    assert r.score is None and r.level == s.INSUFFICIENT and r.gap is None


def test_overall_requires_enough_categories():
    res = [s.CategoryResult(str(i), 80, "Good", 1, 4, 4, 75, 0) for i in range(9)]
    assert s.overall_indicator(res, {}, 10) is None
    res.append(s.CategoryResult("z", 20, "Needs Attention", 1, 4, 4, 75, 55))
    assert s.overall_indicator(res, {}, 10) == 74.0


def test_achievable_target_is_incremental():
    assert s.achievable_target(30, 75, 10) == 40
    assert s.achievable_target(70, 75, 10) == 75
    assert s.achievable_target(85, 75, 10) == 85
