"""Avoid false vendor typo warnings from generic shared suffixes."""
from backend.app.api.claims import get_closest_vendor


def test_vendor_name_warning_requires_a_plausible_typo():
    assert get_closest_vendor("IndiGo Airlines") == (None, 0.0)
    match, similarity = get_closest_vendor("Zomto Food")
    assert match == "Zomato" and similarity >= 0.8
    assert get_closest_vendor("Zomato") == (None, 0.0)
