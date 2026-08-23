"""
เทสต์ provenance (Phase 3.3 / O2)

กฎเดียวที่ทั้ง phase ยึด: **ไม่มีที่มา = ไม่รับเข้า**
เทสต์ชุดนี้จึงเน้นว่า "ของที่ไม่ครบต้องพัง" มากกว่า "ของที่ครบต้องผ่าน"
"""
import pytest

from core.pipeline import (
    Document,
    Provenance,
    ProvenanceError,
    compute_content_hash,
    dedupe,
)

OK = dict(
    source_url="https://example.co.th/news/1",
    publisher="ตัวอย่างนิวส์",
    license="public-web",
    collector="news_adapter",
    published_at="2024-03-01T08:00:00+07:00",
)


def _doc(text: str, **over) -> Document:
    return Document(raw_text=text, provenance=Provenance(**{**OK, **over}))


# ── ของที่ไม่ครบต้องพัง ──

@pytest.mark.parametrize("missing", ["source_url", "publisher", "license", "collector"])
def test_missing_required_field_is_rejected(missing):
    bad = {**OK, missing: ""}
    with pytest.raises(ProvenanceError):
        Provenance(**bad)


def test_unknown_license_is_rejected():
    """สิทธิ์ต้องตัดสินก่อนเก็บ ไม่ใช่หลังเก็บ"""
    with pytest.raises(ProvenanceError, match="license"):
        Provenance(**{**OK, "license": "ไม่รู้"})


def test_non_http_url_is_rejected():
    with pytest.raises(ProvenanceError, match="source_url"):
        Provenance(**{**OK, "source_url": "/local/file.txt"})


def test_bad_timestamp_is_rejected():
    with pytest.raises(ProvenanceError, match="published_at"):
        Provenance(**{**OK, "published_at": "1 มีนาคม 2567"})


def test_empty_document_is_rejected():
    with pytest.raises(ProvenanceError):
        _doc("   ")


# ── temporal cutoff (Phase 7.1) ──

def test_document_without_published_at_is_flagged_unusable():
    """ชิ้นที่ไม่รู้วันเผยแพร่ ใช้กัน leakage ไม่ได้ ต้องแยกออกได้"""
    p = Provenance(**{**OK, "published_at": None})
    assert p.usable_for_temporal_cutoff is False
    assert Provenance(**OK).usable_for_temporal_cutoff is True


# ── กันเก็บซ้ำ ──

def test_hash_ignores_layout_but_not_spelling():
    """ข่าวชิ้นเดียวกันที่จัดหน้าต่างกัน = ชิ้นเดียวกัน
    แต่ข้อความที่สะกดต่างกันจริง = คนละชิ้น
    """
    a = compute_content_hash("รัฐบาล ประกาศ  ขึ้นภาษี")
    b = compute_content_hash("รัฐบาล ประกาศ\n\nขึ้นภาษี")
    c = compute_content_hash("รัฐบาลประกาศลดภาษี")
    assert a == b
    assert a != c


def test_dedupe_keeps_first_occurrence():
    d1 = _doc("ข่าวเดียวกัน", publisher="เจ้าแรก")
    d2 = _doc("ข่าวเดียวกัน", publisher="เจ้าที่สอง")
    d3 = _doc("ข่าวคนละเรื่อง")

    out = dedupe([d1, d2, d3])
    assert len(out) == 2
    assert out[0].provenance.publisher == "เจ้าแรก"


def test_doc_id_is_stable_across_runs():
    """รันซ้ำต้องได้ id เดิม ไม่งั้น reproduce ไม่ได้ (Phase 7)"""
    assert _doc("ข้อความทดสอบ").doc_id == _doc("ข้อความทดสอบ").doc_id


# ── ไป-กลับกับดิสก์ ──

def test_roundtrip_preserves_everything():
    d = _doc("รัฐบาลประกาศขึ้นภาษี VAT เป็น 10%")
    back = Document.from_dict(d.to_dict())
    assert back.raw_text == d.raw_text
    assert back.doc_id == d.doc_id
    assert back.provenance.source_url == d.provenance.source_url
    assert back.provenance.collector_version == d.provenance.collector_version


def test_collector_version_is_recorded():
    """ต้องรู้ว่าเก็บด้วยโค้ดเวอร์ชันไหน ไม่งั้นแยกไม่ออกว่าข้อมูลต่างเพราะอะไร"""
    assert _doc("อะไรก็ได้").provenance.collector_version
