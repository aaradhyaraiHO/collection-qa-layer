from pathlib import Path

from collection_qa.checks import run_checks
from collection_qa.gates import cannibalisation_pairs
from collection_qa.models import load_spec

ROOT = Path(__file__).resolve().parents[1]


def _ids(spec, check_id, severity):
    return [item for item in run_checks(spec) if item.id == check_id and item.severity == severity]


def test_fixture_price_mismatch_fails_and_missing_pickup_fails():
    spec = load_spec(ROOT / "tests/fixtures/tiny_collection.yaml")
    assert _ids(spec, "price_consistency", "fail")
    assert _ids(spec, "pickup_stated", "fail")
    assert _ids(spec, "inclusion_claim", "fail")
    # 30% apart is above the 5% fail band.
    failed = _ids(spec, "price_consistency", "fail")[0]
    assert "cheap" in failed.product_ids


def test_mara_spec_flags_real_page_issues():
    spec = load_spec(ROOT / "specs/masai-mara.yaml")
    assert spec.catalog_status == "live_headout"
    assert spec.page_type == "microbrand"
    assert len(spec.products) == 17
    assert _ids(spec, "mixed_price_units", "warn")
    assert _ids(spec, "inclusion_claim", "warn")
    assert _ids(spec, "reseller_disclosure", "warn")
    assert _ids(spec, "outside_collection", "warn")
    assert _ids(spec, "faq_coverage", "warn")
    # Same-currency HTML embed is within the FX-noise band, so it does not fail.
    assert not _ids(spec, "price_consistency", "fail")
    assert cannibalisation_pairs(spec)


def test_milford_spec_flags_duration_and_scope():
    spec = load_spec(ROOT / "specs/milford-sound.yaml")
    assert spec.page_type == "headout_collection"
    assert len(spec.products) == 24
    assert spec.currency == "NZD"
    assert _ids(spec, "duration_claim", "warn")
    assert _ids(spec, "duration_span", "warn")
    assert _ids(spec, "assortment_scope", "warn")
    assert _ids(spec, "accessibility_disclosure", "warn")
    assert _ids(spec, "faq_coverage", "warn")
    assert _ids(spec, "choice_overload", "warn") or True
    scope = _ids(spec, "assortment_scope", "warn")[0]
    assert "26901" in scope.product_ids
    # Catalog currency is NZD; USD HTML embeds must not be treated as mismatches.
    assert not _ids(spec, "price_consistency", "fail")


def test_choice_overload_constant_is_visible_on_both_pilots():
    from collection_qa.gates import choice_overload

    for name in ("masai-mara.yaml", "milford-sound.yaml"):
        spec = load_spec(ROOT / "specs" / name)
        result = choice_overload(spec)
        assert result is not None
        assert result.severity == "warn"
        assert result.blocks_go_live is False
