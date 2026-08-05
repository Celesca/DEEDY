"""
เทสต์ทะเบียนแหล่งข้อมูล (Phase 3.2 / O2)

จุดประสงค์คือทำให้ข้อจำกัดทางกฎหมาย/จริยธรรม **หยุด pipeline ได้เอง**
ไม่ใช่เป็นแค่ตารางในเอกสารที่คนเขียน collector ตัวถัดไปไม่ได้อ่าน
"""
import pytest

from core.pipeline.sources import (
    SOURCE_REGISTRY,
    USE_ANALYSIS,
    USE_REFERENCE,
    USE_TRAIN,
    SourceNotAllowed,
    assert_collectable,
    assert_use_allowed,
    get_policy,
    registry_report,
)


# ── fail-closed ──

def test_unregistered_domain_is_refused():
    """โดเมนที่ยังไม่ได้อ่าน robots.txt ต้องเก็บไม่ได้ ไม่ใช่ลองดูก่อน"""
    with pytest.raises(SourceNotAllowed, match="ยังไม่ได้ขึ้นทะเบียน"):
        assert_collectable("https://random-site.example/article/1")


def test_unregistered_domain_is_refused_for_use_too():
    with pytest.raises(SourceNotAllowed):
        assert_use_allowed("https://random-site.example/x", USE_ANALYSIS)


# ── นิด้าโพล: ใช้อ้างอิงได้ แต่เทรนไม่ได้ และเก็บอัตโนมัติไม่ได้ ──

NIDA = "https://nidapoll.nida.ac.th/survey_detail?survey_id=689"


def test_nida_poll_cannot_be_crawled():
    """robots.txt บล็อกบอท AI และดึงตรงได้ 403 -> ต้องกรอกมือ"""
    with pytest.raises(SourceNotAllowed, match="manual_entry_only"):
        assert_collectable(NIDA)


def test_nida_poll_allows_reference_use():
    """เอาตัวเลขมาเทียบผลจำลอง (Phase 7) ได้ — นี่คือ use=reference"""
    assert assert_use_allowed(NIDA, USE_REFERENCE).license == "research-only"


def test_nida_poll_forbids_training_use():
    """Content-Signal ระบุ ai-train=no ตรง ๆ"""
    with pytest.raises(SourceNotAllowed, match="train"):
        assert_use_allowed(NIDA, USE_TRAIN)


# ── ข่าวที่เก็บได้ ──

NEWS = "https://www.nationthailand.com/news/politics/40044858"


def test_registered_news_site_is_collectable():
    p = assert_collectable(NEWS)
    assert p.crawl_allowed
    assert p.min_delay_seconds >= 1.0, "ต้องมีการหน่วงเวลา ไม่ยิงรัว"


def test_news_site_also_forbids_training_by_default():
    """ค่าปริยายของทะเบียนคือไม่อนุญาตให้เทรน ต้องระบุเพิ่มเองถ้าจะทำ"""
    with pytest.raises(SourceNotAllowed):
        assert_use_allowed(NEWS, USE_TRAIN)


# ── ความครบถ้วนของทะเบียน ──

def test_every_entry_records_when_robots_was_checked():
    """ต้องอ้างได้ว่าตรวจเมื่อไร ไม่งั้นบอกไม่ได้ว่าตอนเก็บเงื่อนไขเป็นแบบไหน"""
    for p in SOURCE_REGISTRY.values():
        assert p.robots_checked, f"{p.domain} ไม่ได้บันทึกวันที่ตรวจ robots.txt"
        assert p.notes, f"{p.domain} ไม่ได้บันทึกว่าอ่าน robots.txt แล้วเจออะไร"


def test_no_source_allows_training_yet():
    """ยังไม่มีแหล่งไหนที่เคลียร์สิทธิ์การเทรนแล้ว — ถ้าจะมีต้องตั้งใจเพิ่ม"""
    for p in SOURCE_REGISTRY.values():
        assert not p.allows(USE_TRAIN), f"{p.domain} เปิดสิทธิ์เทรนไว้ ตรวจสอบก่อน"


def test_policy_lookup_ignores_scheme_and_path():
    assert get_policy("https://www.nationthailand.com/a/b?c=1") is not None
    assert get_policy("not-a-url") is None


def test_report_is_renderable():
    r = registry_report()
    assert "nidapoll.nida.ac.th" in r and "2026-08-01" in r
