"""
เทสต์ Thai-aware text views (Phase 3.4 / O2)

เคสสำคัญที่สุดคือกลุ่ม "ปีพุทธศักราช" เพราะโค้ดเดิมใน
`app/services/thai_nlp_processor.py` แปลงเลข 4 หลักทุกตัวในช่วง 2400-2600
เป็น ค่า-543 ทำให้ "ราคา 2500 บาท" กลายเป็น "ราคา 1957 บาท"
แล้วส่งผลเพี้ยนนั้นต่อเข้า tokenizer/NER
"""
from core.pipeline import (
    TextViews,
    detect_be_years,
    profile_informality,
    text_with_ce_years,
)


# ── ปีพุทธศักราช: ต้องแยกปีออกจากจำนวน ──

def test_price_is_not_mistaken_for_a_year():
    """เคสที่โค้ดเดิมพัง — "ราคา 2500 บาท" ต้องไม่กลายเป็นปี"""
    (m,) = detect_be_years("ราคา 2500 บาท")
    assert m.confidence < 0.6
    assert not m.is_confident
    assert text_with_ce_years("ราคา 2500 บาท") == "ราคา 2500 บาท"


def test_house_number_is_not_a_year():
    assert text_with_ce_years("บ้านเลขที่ 2555 ถนนสุขุมวิท") == "บ้านเลขที่ 2555 ถนนสุขุมวิท"


def test_salary_is_not_a_year():
    assert text_with_ce_years("เงินเดือน 2450 บาท") == "เงินเดือน 2450 บาท"


def test_real_year_is_detected_with_high_confidence():
    (m,) = detect_be_years("เกิดปี 2540 ที่กรุงเทพ")
    assert m.is_confident
    assert m.be_year == 2540
    assert m.ce_year == 1997


def test_por_sor_prefix_is_detected():
    (m,) = detect_be_years("ประกาศ ณ วันที่ 1 มกราคม พ.ศ. 2566")
    assert m.is_confident
    assert m.ce_year == 2023


def test_conversion_only_touches_confident_mentions():
    """ข้อความที่มีทั้งปีและราคา ต้องแปลงเฉพาะปี"""
    src = "เมื่อปี 2560 ราคาน้ำมันอยู่ที่ 2530 บาทต่อบาร์เรล"
    out = text_with_ce_years(src)
    assert "2017" in out          # 2560 -> ปี
    assert "2530 บาท" in out      # ราคา ไม่แตะ


def test_detection_never_mutates_the_source():
    """หัวใจของ view: ของดิบต้องไม่เปลี่ยน"""
    src = "เมื่อปี 2540 เกิดวิกฤต"
    v = TextViews(raw=src)
    _ = v.year_mentions
    _ = v.normalized
    assert v.raw == src


def test_mention_offsets_point_back_to_raw_text():
    """ต้องย้อนกลับไปหาตำแหน่งในของดิบได้ ไม่งั้นอ้างอิงในรายงานไม่ได้"""
    src = "วิกฤตต้มยำกุ้งเกิดในปี 2540 ครับ"
    (m,) = detect_be_years(src)
    assert src[m.start:m.end] == "2540"


# ── มุมมองอื่น ──

def test_views_are_computed_from_raw_not_each_other():
    v = TextViews(raw="รัฐบาล   ประกาศ\n\nขึ้นภาษี")
    assert "   " not in v.normalized
    assert v.raw == "รัฐบาล   ประกาศ\n\nขึ้นภาษี"


def test_thai_text_is_tokenized_into_words():
    """ภาษาไทยไม่มีช่องว่างระหว่างคำ — ถ้าไม่ตัดคำ view นี้ไร้ประโยชน์"""
    v = TextViews(raw="รัฐบาลประกาศขึ้นภาษี")
    assert len(v.tokens) > 1
    assert "".join(v.tokens).replace(" ", "") == "รัฐบาลประกาศขึ้นภาษี"


def test_thai_ratio_separates_thai_from_english():
    assert TextViews(raw="ข้อความภาษาไทยล้วน").thai_ratio > 0.9
    assert TextViews(raw="pure english text here").thai_ratio == 0.0


# ── ระดับภาษา (O3 / O4) ──

def test_casual_text_scores_more_informal_than_official_text():
    casual = profile_informality("แพงงงง 5555 ทนไม่ไหวแล้วครับ #ของขึ้นราคา")
    formal = profile_informality(
        "ตามที่กระทรวงได้ประกาศระเบียบดังกล่าว ทั้งนี้ จึงเรียนมาเพื่อทราบ"
    )
    assert casual.informality_score > formal.informality_score


def test_informality_signals_are_counted():
    p = profile_informality("แพงงง 5555 ครับ #ภาษี https://a.co/x")
    assert p.repeated_chars >= 1
    assert p.laughs == 1
    assert p.polite_particles == 1
    assert p.hashtags == 1
    assert p.urls == 1


def test_neutral_text_sits_in_the_middle():
    """ไม่มีสัญญาณทั้งสองฝั่ง ต้องไม่เดาไปทางใดทางหนึ่ง"""
    assert profile_informality("วันนี้ฝนตก").informality_score == 0.5


# ── ไปดิสก์ ──

def test_to_dict_skips_expensive_view_by_default():
    d = TextViews(raw="รัฐบาลประกาศขึ้นภาษีเมื่อปี 2560").to_dict()
    assert "pos" not in d
    assert d["tokens"] and d["year_mentions"]
    assert TextViews(raw="ทดสอบ").to_dict(heavy=True)["pos"]
