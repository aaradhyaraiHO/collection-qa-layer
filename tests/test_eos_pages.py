"""Confirmed EOS pages. Fixtures stand in for a signed-in, read-only browser."""

from pathlib import Path

from collection_qa.eos import (
    KNOWN_MMP_UUIDS,
    classify_eos,
    describe_mmp_link,
    fetch_eos_page,
    opens_search,
    parse_mmp_url,
    prefer_mmp_url,
    read_eos_export,
)

FIXTURES = Path("tests/fixtures/eos")
MILFORD = "https://eos.headout.com/mmp/draft/f5889f6f-0a8a-4b5e-801f-e7544cb4e623/ce-identity"


def test_pasted_mmp_url_is_preferred_over_search():
    uuid, page = parse_mmp_url(MILFORD + "?subStep=ce-summary")
    assert uuid == KNOWN_MMP_UUIDS["3945"]
    assert page == "ce-identity"
    assert prefer_mmp_url(MILFORD, "7324") == MILFORD
    assert prefer_mmp_url("", "7324").endswith("/" + KNOWN_MMP_UUIDS["7324"] + "/ce-identity")
    described = describe_mmp_link(MILFORD)
    assert described["ok"] is True
    assert described["ce_id"] == "3945"
    assert "Read-only" in described["line"]
    assert opens_search("https://eos.headout.com/")
    assert not opens_search(MILFORD)


def test_identity_page_reads_the_sidebar_ce_id():
    document = read_eos_export(str(FIXTURES / "identity.html"))
    document.source = MILFORD
    # source on the file path has no uuid; parse the body.
    assert document.ce_id == "3945"
    assert document.ce_name == "Milford Sound Cruises"
    assert document.market == "Oceania"
    assert document.region == "Asia-Pacific"
    assert "Managed" in document.tags
    assert "New CE" not in document.tags
    assert document.page == "ce-identity"


def test_live_assortment_uses_revenue_and_not_a_price():
    document = read_eos_export(str(FIXTURES / "assortment.html"))
    assert document.live_assortment is True
    assert document.products[0].id == "tg-29695"
    assert document.products[0].revenue == 41959
    assert document.products[0].price is None
    assert classify_eos(document)[0] == "LIVE"
    notes = " ".join(document.notes).lower()
    assert "cancellation" in notes
    assert "pickup" in notes
    assert "export button" in notes


def test_new_ce_with_no_assortment_stays_in_pipeline():
    document = read_eos_export(str(FIXTURES / "new-ce.html"))
    assert document.is_new_ce is True
    assert document.empty_live_assortment is True
    assert document.products == []
    assert classify_eos(document) == ("IN_PIPELINE", "new_ce")


def test_content_status_sets_the_gate_b_flag():
    locked = read_eos_export(str(FIXTURES / "content-locked.html"))
    assert locked.content_locked is True
    assert locked.content_status == "Locked"
    assert locked.ce_id == "7324"
    assert locked.products[0].row_tag == "New"
    assert locked.products[0].variants_ready == "1/1"
    assert classify_eos(locked)[1] == "content_locked"
    opened = read_eos_export(str(FIXTURES / "content-open.html"))
    assert opened.content_locked is False
    assert opened.content_status == "Not started"
    assert opened.products[0].id == "tg-40298"
    assert opened.products[0].row_tag == "New Variant"
    assert opened.products[0].variant_id == "120831"
    assert "original operator" in opened.products[0].highlights[0]


def test_fetch_refuses_search_and_stays_read_only(tmp_path):
    called = {}

    def launcher(profile, url, *, headless, wait_for_enter):
        called["url"] = url
        called["headless"] = headless
        called["wait"] = wait_for_enter
        return "<html>CE identity CE ID 3945</html>"

    try:
        fetch_eos_page("https://eos.headout.com/", profile_dir=tmp_path, launcher=launcher)
    except ValueError as exc:
        assert "draft" in str(exc).lower()
    else:
        raise AssertionError("search URL should be refused")
    assert called == {}
    profile = tmp_path / "profile"
    profile.mkdir()
    html = fetch_eos_page(MILFORD, profile_dir=profile, launcher=launcher)
    assert "CE identity" in html
    assert called["headless"] is True
    assert called["wait"] is False
    assert called["url"] == MILFORD
