"""
เทสต์ expression filter — ส่วนที่ตัดสินว่า "คิดอย่างไร" กลายเป็น "ทำอะไร" (D10)

เทสต์ชุดนี้คือหลักฐานว่าการย้ายกลไกออกจาก LLM มาเป็นโค้ดแก้ปัญหาได้จริง
ก่อนแก้: LLM ให้ผลต่างระหว่าง fear ต่ำ/สูง แค่ 0.17-0.33 (ถือว่ากลไกไม่ทำงาน)
เกณฑ์ผ่าน Phase 1: ต้องต่างกันเกิน 1.0
"""
import random
from collections import Counter

import pytest

from core import actions as A
from core.expression import (
    ExpressionContext,
    MediaAccess,
    choose_action,
    distribution,
    expected_exposure,
    score_actions,
)

OFFLINE_PERSON = MediaAccess(social_media=False, line=True, tv=True, community=True)
ONLINE_PERSON = MediaAccess(social_media=True, line=True, tv=True, community=False)


def ctx(fear, anger=55, intensity=70, media=OFFLINE_PERSON, stance="opposing", **kw):
    """คนที่ "ไม่เห็นด้วยและโกรธ" คือกรณีหลักที่ filter ต้องจัดการ

    ต้องระบุ stance เพราะ action ฝั่งคัดค้าน (แบน/ม็อบ/ลงชื่อ/ร้องเรียน)
    ถูกกันไว้ให้เฉพาะคนที่ไม่เห็นด้วย — คนที่ยังไม่มีจุดยืนไม่ไปม็อบ
    """
    return ExpressionContext(
        fear=fear, anger=anger, opinion_intensity=intensity, media=media,
        stance=stance, **kw
    )


# ── เกณฑ์ผ่านหลักของ Phase 1 ──

def test_fear_reduces_exposure_beyond_threshold():
    """กลไกหลัก: กลัวมากขึ้น -> กล้าแสดงออกน้อยลง อย่างมีนัยสำคัญ"""
    low = expected_exposure(ctx(15))
    high = expected_exposure(ctx(85))
    assert low - high > 1.0, (
        f"กลไก fear อ่อนเกินไป (ต่างกันแค่ {low - high:.2f}) "
        "ซึ่งเป็นปัญหาเดียวกับตอนฝากไว้กับ LLM"
    )


def test_exposure_decreases_monotonically_with_fear():
    """ต้องลดลงเรื่อยๆ ไม่ใช่กระโดดไปมา"""
    values = [expected_exposure(ctx(f)) for f in (0, 25, 50, 75, 100)]
    assert values == sorted(values, reverse=True), values


def test_action_variety_is_more_than_two():
    """ตอนฝากไว้กับ LLM ได้แค่ 2 แบบจาก 6 — ต้องกระจายกว่านั้น"""
    rng = random.Random(1)
    seen = Counter(choose_action(ctx(50), rng).key for _ in range(300))
    assert len(seen) >= 5, f"พฤติกรรมกระจุกเกินไป: {dict(seen)}"


# ── พฤติกรรมที่ต้องเป็นจริงเชิงสังคม ──

def test_high_fear_favours_silence():
    rng = random.Random(2)
    counts = Counter(choose_action(ctx(90), rng).key for _ in range(300))
    assert counts.most_common(1)[0][0] == A.SILENT_SHIFT.key


def test_no_fear_high_anger_enables_public_action():
    """ไม่กลัวและโกรธมาก ต้องมีโอกาสออกสู่สาธารณะจริง"""
    dist = distribution(ctx(0, anger=95, intensity=95, media=ONLINE_PERSON))
    public = sum(
        p for label, p in dist.items()
        if label in (A.POST_PUBLIC.label_th, A.SHARE_PUBLIC.label_th, A.JOIN_PROTEST.label_th)
    )
    assert public > 0.15, f"คนไม่กลัวควรกล้าออกสาธารณะมากกว่านี้: {dist}"


def test_apathetic_person_mostly_silent():
    """ไม่โกรธ ไม่สนใจ = ไม่ทำอะไร ซึ่งเป็นสภาพของคนส่วนใหญ่ในสังคม"""
    dist = distribution(ctx(10, anger=5, intensity=10, media=ONLINE_PERSON))
    assert dist[A.SILENT_SHIFT.label_th] > 0.5


def test_evasive_speech_appears_when_angry_but_afraid():
    """เลี่ยงบาลี — พฤติกรรมเด่นของคนไทยที่อยากพูดแต่กลัวผลทางกฎหมาย"""
    dist = distribution(ctx(80, anger=90, intensity=90, media=ONLINE_PERSON))
    assert dist.get(A.EVASIVE_POST.label_th, 0) > 0.03
    # ต้องมีโอกาสมากกว่าการโพสต์ตรงๆ ซึ่งเสี่ยงกว่ามาก
    assert dist.get(A.EVASIVE_POST.label_th, 0) > dist.get(A.POST_PUBLIC.label_th, 0)


# ── ข้อจำกัดของช่องทาง ──

def test_no_social_media_never_posts_publicly():
    rng = random.Random(3)
    keys = {choose_action(ctx(10, anger=95, intensity=95), rng).key for _ in range(300)}
    assert A.POST_PUBLIC.key not in keys
    assert A.EVASIVE_POST.key not in keys


def test_offline_actions_available_without_any_media():
    """คนไม่มีทั้งโซเชียลและไลน์ ต้องยังทำอะไรในโลกจริงได้"""
    isolated = MediaAccess(social_media=False, line=False, tv=True, community=False)
    keys = {a.key for a, _ in score_actions(ctx(20, anger=90, intensity=90, media=isolated))}
    assert A.TALK_FAMILY.key in keys
    assert A.SILENT_SHIFT.key in keys
    assert A.SHARE_LINE.key not in keys


# ── ลักษณะทางสังคมไทย ──

def test_deference_and_seniority_suppress_expression():
    """เกรงใจและระบบอาวุโส ต้องลดการแสดงออกได้แม้ไม่กลัวคดี"""
    plain = expected_exposure(ctx(20, deference=10, seniority_pressure=10))
    pressured = expected_exposure(ctx(20, deference=90, seniority_pressure=90))
    assert plain > pressured


# ── ความสามารถในการทำซ้ำ (Phase 6) ──

def test_same_seed_gives_same_sequence():
    c = ctx(50)
    a = [choose_action(c, random.Random(99)).key for _ in range(20)]
    b = [choose_action(c, random.Random(99)).key for _ in range(20)]
    assert a == b


@pytest.mark.parametrize("fear", [0, 50, 100])
def test_silence_always_available(fear):
    keys = {a.key for a, _ in score_actions(ctx(fear, anger=0, intensity=0))}
    assert A.SILENT_SHIFT.key in keys


# ── เกรงใจขึ้นกับ "คู่สนทนา" ไม่ใช่แค่ตัวบุคคล ──

def test_deference_hits_face_to_face_hardest():
    """คนเกรงใจสูง ต้องเงียบต่อหน้าเพื่อนร่วมงานมากกว่าตอนบ่นที่บ้าน

    นี่คือธรรมชาติของเกรงใจไทย — เป็นเรื่องความสัมพันธ์กับคู่สนทนา
    ไม่ใช่คุณสมบัติที่กดทุกอย่างเท่ากัน
    """
    low = distribution(ctx(20, deference=10, seniority_pressure=10))
    high = distribution(ctx(20, deference=95, seniority_pressure=95))

    work_drop = 1 - high[A.TALK_WORK.label_th] / low[A.TALK_WORK.label_th]
    home_drop = 1 - high[A.TALK_FAMILY.label_th] / low[A.TALK_FAMILY.label_th]
    assert work_drop > home_drop, (
        f"เกรงใจควรกดการคุยที่ทำงาน ({work_drop:.2f}) มากกว่าคุยที่บ้าน ({home_drop:.2f})"
    )


def test_deference_barely_affects_evasive_speech():
    """เลี่ยงบาลีไม่ได้เผชิญหน้าใคร เกรงใจจึงแทบไม่กด — จุดนี้ทำให้มันเป็นทางออก"""
    low = distribution(ctx(20, media=ONLINE_PERSON, deference=10, seniority_pressure=10))
    high = distribution(ctx(20, media=ONLINE_PERSON, deference=95, seniority_pressure=95))

    evasive_drop = 1 - high[A.EVASIVE_POST.label_th] / low[A.EVASIVE_POST.label_th]
    work_drop = 1 - high[A.TALK_WORK.label_th] / low[A.TALK_WORK.label_th]
    assert evasive_drop < work_drop


def test_deference_does_not_touch_private_behaviour():
    """เกรงใจไม่ควรห้ามคนแอบเลิกซื้อของ เพราะไม่มีใครรู้"""
    low = distribution(ctx(20, deference=10, seniority_pressure=10))
    high = distribution(ctx(20, deference=95, seniority_pressure=95))
    # สัดส่วนอาจขยับเพราะตัวอื่นหด แต่ต้องไม่ถูกกดลง
    assert high[A.BOYCOTT.label_th] >= low[A.BOYCOTT.label_th] * 0.95


def test_situational_deference_modifies_pressure():
    """สถานการณ์ปรับเกรงใจได้ เช่น เรื่องกระทบที่ทำงานตัวเอง vs ใช้บัญชีนิรนาม"""
    normal = expected_exposure(ctx(20, deference=70, seniority_pressure=70))
    at_work = expected_exposure(
        ctx(20, deference=70, seniority_pressure=70, situational_deference=1.8)
    )
    anonymous = expected_exposure(
        ctx(20, deference=70, seniority_pressure=70, situational_deference=0.1)
    )
    assert anonymous > normal > at_work


def test_legal_fear_applies_to_all_channels():
    """ต่างจากเกรงใจ — กลัวคดีต้องกดแม้แต่ในกลุ่มไลน์ปิด"""
    calm = distribution(ctx(5, deference=0, seniority_pressure=0))
    scared = distribution(ctx(95, deference=0, seniority_pressure=0))
    assert scared[A.SHARE_LINE.label_th] < calm[A.SHARE_LINE.label_th]


# ── จุดยืนต้องผูกกับการกระทำ ──
# ทั้งหมดนี้มาจากบั๊กจริงตอนรันเคส PARAMETER (ร้านเจลาโต้)

def test_supporter_never_boycotts_or_protests():
    """คนที่เห็นด้วยต้องไม่ไปแบนหรือประท้วงสิ่งที่ตัวเองเห็นด้วย"""
    labels = set(distribution(ctx(20, stance="supportive", media=ONLINE_PERSON)))
    for a in (A.BOYCOTT, A.JOIN_PROTEST, A.SIGN_PETITION, A.COMPLAIN_OFFICIAL):
        assert a.label_th not in labels, f"คนที่เห็นด้วยเลือก {a.label_th} ได้"


def test_opposer_never_shows_off_or_defends():
    labels = set(distribution(ctx(20, stance="opposing", media=ONLINE_PERSON)))
    for a in (A.SHOW_OFF, A.DEFEND_PUBLIC):
        assert a.label_th not in labels, f"คนที่ไม่เห็นด้วยเลือก {a.label_th} ได้"


def test_undecided_person_takes_no_side_actions():
    """ยังไม่มีจุดยืน -> ไม่ไปม็อบและไม่ออกมาปกป้องใคร"""
    labels = set(distribution(ctx(20, stance="neutral", media=ONLINE_PERSON)))
    for a in (A.JOIN_PROTEST, A.BOYCOTT, A.DEFEND_PUBLIC, A.SHOW_OFF):
        assert a.label_th not in labels


def test_thai_stance_words_are_understood():
    """LLM อาจตอบเป็นภาษาไทย ต้อง normalize ได้"""
    assert A.normalize_stance("ไม่เห็นด้วย") == "oppose"
    assert A.normalize_stance("Supportive") == "support"
    assert A.normalize_stance("มั่วซั่ว") is None


# ── ซื้ออยู่ดี: ด้านที่ action space เดิมไม่มี ──

def test_critic_can_still_buy():
    """หัวใจของเคส PARAMETER — ด่าอยู่ก็ยังซื้อได้

    ถ้ากัน buy_anyway ไว้ให้เฉพาะคนที่เห็นด้วย ช่องว่างระหว่าง
    "สิ่งที่พูด" กับ "สิ่งที่ทำ" จะหายไปทั้งหมด
    """
    labels = set(distribution(ctx(20, stance="opposing", media=ONLINE_PERSON)))
    assert A.BUY_ANYWAY.label_th in labels


def test_calm_people_buy_more_than_furious_people():
    """คนที่ไม่ได้เดือดร้อนอะไรจะซื้อ ส่วนคนโกรธจัดไปหาทางระบายที่แรงกว่า"""
    calm = distribution(ctx(10, anger=5, intensity=20, media=ONLINE_PERSON))
    furious = distribution(ctx(10, anger=95, intensity=95, media=ONLINE_PERSON))
    assert calm[A.BUY_ANYWAY.label_th] > furious[A.BUY_ANYWAY.label_th]


# ── action ต้องจำกัดตาม scenario ──

def test_scenario_removes_irrelevant_actions():
    """บั๊กจริง: รันเคสร้านไอศกรีมแล้วได้ ไปม็อบ/ถอนเงิน/กักตุน รวม 16%"""
    from core import scenario as S

    sc = S.build("consumer", subject="ร้านเจลาโต้ PARAMETER")
    labels = set(distribution(ctx(20, stance="opposing", media=ONLINE_PERSON,
                                  available=sc.actions)))
    for a in (A.JOIN_PROTEST, A.WITHDRAW_MONEY, A.STOCKPILE, A.SIGN_PETITION):
        assert a.label_th not in labels, f"ดราม่าแบรนด์ไม่ควรมี {a.label_th}"
    assert A.BOYCOTT.label_th in labels
    assert A.BUY_ANYWAY.label_th in labels


def test_silent_is_always_available_even_if_omitted():
    from core import scenario as S

    sc = S.Scenario(key="x", label="x", subject="อะไรสักอย่าง",
                    support_means="เห็นด้วย", oppose_means="ไม่เห็นด้วย",
                    actions=[A.TALK_FAMILY])
    assert A.SILENT_SHIFT in sc.actions


def test_scenario_without_stance_definition_is_rejected():
    """ถ้าไม่นิยามว่าจุดยืนอ้างอิงกับอะไร ตัวเลขที่ได้จะตีความไม่ได้"""
    from core import scenario as S

    with pytest.raises(S.ScenarioError, match="subject"):
        S.Scenario(key="x", label="x", subject="  ",
                   support_means="ก", oppose_means="ข")
