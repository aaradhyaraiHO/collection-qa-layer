from collection_qa.checks import relative_gap, run_deterministic_checks
from collection_qa.models import load_spec


def _codes(issues, code):
    return [issue for issue in issues if issue.code == code]


def test_tiny_price_conflict_and_missing_cancellation_and_disclaimer():
    spec = load_spec("tests/fixtures/tiny.yaml")
    issues = run_deterministic_checks(spec)
    prices = _codes(issues, "price_consistency")
    assert prices
    assert any(issue.severity == "fail" for issue in prices)
    assert relative_gap(99, 140) > 0.10
    cancellation = _codes(issues, "missing_cancellation")
    assert cancellation[0].severity == "fail"
    assert "luxury-fly" in cancellation[0].evidence["missing_ids"]
    disclaimer = _codes(issues, "microbrand_disclaimer")
    assert any(issue.severity == "warn" for issue in disclaimer)
    faqs = _codes(issues, "faq_missing")
    assert any(issue.evidence.get("surface") == "microbrand" for issue in faqs)
    ladder = _codes(issues, "price_ladder")
    by_tier = {issue.evidence.get("tier"): issue.severity for issue in ladder}
    assert by_tier["budget"] == "pass"
    assert by_tier["luxury"] == "pass"
    assert by_tier["mid"] == "warn"
    assert by_tier["premium"] == "warn"


def test_seeded_mara_content_claim_fails_and_prices_are_unknown():
    spec = load_spec("specs/masai-mara.yaml")
    assert spec.provenance == "live_headout"
    assert spec.microbrand is not None
    assert spec.microbrand.not_official_venue_disclaimer is False
    assert all(product.price is None for product in spec.products)
    issues = run_deterministic_checks(spec)
    nakuru = _codes(issues, "assertion:nakuru-on-4-day-plus")
    assert nakuru[0].severity == "fail"
    assert "e-57697" in nakuru[0].evidence["missed_ids"]
    assert "mara-5d-lakes" not in nakuru[0].evidence["missed_ids"]
    ladder = _codes(issues, "price_ladder")
    assert ladder[0].severity == "warn"
    duration = _codes(issues, "duration_consistency")
    assert duration[0].severity == "warn"
    assert duration[0].evidence["product_id"] == "e-57711"
    overload = _codes(issues, "choice_overload")
    assert overload[0].severity == "warn"
    gaps = _codes(issues, "gap:conservancy-night-drive")
    assert gaps[0].severity == "warn"
    assert spec.unknowns


def test_seeded_milford_price_drift_and_no_microbrand():
    spec = load_spec("specs/milford-sound.yaml")
    assert spec.provenance == "live_headout"
    assert spec.microbrand is None
    assert spec.primary_surface.faqs
    issues = run_deterministic_checks(spec)
    prices = _codes(issues, "price_consistency")
    by_product = {issue.evidence.get("product_id"): issue for issue in prices}
    assert by_product["e-29695"].severity == "warn"
    assert by_product["e-18103"].severity == "pass"
    assert "e-37309" not in by_product  # original vs from are different kinds
    assert any(issue.code == "gap:overnight-cruise" and issue.severity == "warn" for issue in issues)
    assert not _codes(issues, "microbrand_disclaimer")
    topics = _codes(issues, "faq_topics")
    assert topics[0].severity == "pass"
    currencies = _codes(issues, "currency_consistency")
    assert currencies[0].severity == "pass"
    assert all(source.fetched_on == "2026-11-26" for source in spec.sources)
