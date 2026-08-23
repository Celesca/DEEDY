"""
เทสต์ความจำภาษาไทย (Phase 2)

เกณฑ์ผ่านหลักมาจาก PLAN.md:
  ใส่ความจำ 3 อัน (ค่าแรงไม่ขึ้น / ไหว้พระแม่ลักษมี / ไข่เจียวแพง)
  ถาม "รัฐบาลขึ้นภาษี เงินไม่พอใช้"
  -> 2 อันแรกต้องเป็นเรื่องเงิน ไม่ใช่เรื่องไหว้พระ

เทสต์กลุ่มนี้ต้องโหลดโมเดล embedding จริง จึงช้ากว่าชุดอื่น
"""
import pytest

from core.memory_stream import MemoryStream

WAGE = "เห็นเพื่อนในทวิตเตอร์บ่นเรื่องค่าแรงขั้นต่ำไม่ขึ้นมาหลายปีแล้ว"
SHRINE = "เพิ่งไปไหว้พระแม่ลักษมีที่เซ็นทรัลเวิลด์มาขอให้ถูกหวย"
EGG = "กินข้าวไข่เจียวปากซอยราคา 50 บาท แพงขึ้นกว่าเดิมเยอะ"
PROBE = "เมื่อปีก่อน รุ่นพี่ที่ทำงานโพสต์วิจารณ์นโยบายกระทรวง แล้วโดนตั้งกรรมการสอบสวน"


@pytest.fixture(autouse=True)
def _clean_client():
    MemoryStream.reset_client()
    yield
    MemoryStream.reset_client()


@pytest.fixture
def mem():
    m = MemoryStream("test_agent")
    m.add_memory(WAGE, importance=7)
    m.add_memory(SHRINE, importance=8)
    m.add_memory(EGG, importance=5)
    return m


# ── เกณฑ์ผ่านหลักของ Phase 2 ──

def test_thai_retrieval_finds_money_not_shrine(mem):
    """คำค้นเรื่องเงิน ต้องไม่ดึงเรื่องไหว้พระขึ้นมาก่อน

    ก่อนแก้ (embedding อังกฤษ) เคสนี้ตกเพราะโมเดลคืนความจำชุดเดิมแทบทุกคำถาม
    """
    got = mem.retrieve_memories("รัฐบาลประกาศขึ้นภาษี เงินไม่พอใช้", n_results=2)
    assert SHRINE not in got, f"ดึงเรื่องไหว้พระมาทั้งที่ถามเรื่องเงิน: {got}"
    assert set(got) == {WAGE, EGG}


def test_retrieval_discriminates_between_topics(mem):
    """คำถามคนละเรื่องต้องได้คำตอบคนละชุด ไม่ใช่ชุดเดิมทุกครั้ง"""
    mem.add_memory(PROBE, importance=9)
    money = set(mem.retrieve_memories("ค่าครองชีพแพงขึ้น", n_results=2))
    legal = set(mem.retrieve_memories("กลัวโดนดำเนินคดีถ้าวิจารณ์รัฐบาล", n_results=2))
    assert money != legal
    assert PROBE in legal


def test_empty_memory_returns_empty():
    assert MemoryStream("nobody").retrieve_memories("อะไรก็ตาม") == []


# ── recency + importance (ไม่ใช่ similarity อย่างเดียว) ──

def test_importance_breaks_ties():
    """เรื่องที่คล้ายกันพอๆ กัน เรื่องที่สำคัญกว่าต้องมาก่อน"""
    m = MemoryStream("agent_importance")
    m.add_memory("ค่าไฟเดือนนี้ขึ้นนิดหน่อย", importance=2)
    m.add_memory("ค่าไฟเดือนนี้ขึ้นจนจ่ายไม่ไหว", importance=10)
    top = m.retrieve_memories("ค่าไฟแพง", n_results=1)
    assert "จ่ายไม่ไหว" in top[0]


def test_high_importance_cannot_hijack_unrelated_query():
    """เรื่องสำคัญมากแต่ไม่เกี่ยวกับคำถาม ต้องไม่แซงเรื่องที่เกี่ยวจริง

    บั๊กจริงที่เจอตอนรัน E2E: ถาม "การเดินทางไปทำงาน" แล้วได้เรื่องรุ่นพี่โดน
    สอบสวน (importance 9) ขึ้นที่ 1 ทั้งที่มีความจำเรื่องรถติดอยู่
    สาเหตุ: cosine ของประโยคไทยกระจุกกันแคบ (0.775-0.807) พอใช้สเกลคงที่
    relevance ของเรื่องที่ถูกต้องเหลือแค่ 0.07 แล้ว importance กลบ
    """
    m = MemoryStream("agent_hijack")
    m.add_memory("รถติดมากตอนเช้า กว่าจะถึงที่ทำงานก็สาย", importance=3)
    m.add_memory(PROBE, importance=9)
    m.add_memory("ลูกเพิ่งสอบติดมหาวิทยาลัย ค่าเทอมหนักมาก", importance=8)

    top = m.retrieve_memories("การเดินทางไปทำงาน", n_results=1)
    assert "รถติด" in top[0], f"เรื่องสำคัญที่ไม่เกี่ยวแซงขึ้นมา: {top}"


def test_recency_prefers_newer_memories():
    """ความจำเก่ามากต้องเลือนกว่าความจำใหม่ เมื่อเนื้อหาใกล้เคียงกัน"""
    m = MemoryStream("agent_recency")
    m.add_memory("ของแพงขึ้นมาก", importance=5, sim_time=0.0)
    m.advance_clock(500)  # ผ่านไปนานมาก
    m.add_memory("ของแพงขึ้นมาก", importance=5, sim_time=500.0)

    scored = m.retrieve_scored("ของแพง", n_results=2)
    assert scored[0].sim_time > scored[1].sim_time
    assert scored[0].recency > scored[1].recency


def test_scored_fields_are_populated(mem):
    scored = mem.retrieve_scored("เงินไม่พอใช้", n_results=1)
    assert scored
    s = scored[0]
    assert 0.0 <= s.relevance <= 1.0
    assert 0.0 <= s.recency <= 1.0
    assert 0.0 <= s.importance <= 1.0
    assert s.total > 0


# ── การเก็บลงดิสก์ ──

def test_memory_persists_across_restart(tmp_path):
    """ปิดโปรแกรมแล้วเปิดใหม่ ความจำต้องยังอยู่"""
    path = str(tmp_path / "chroma")

    m1 = MemoryStream("persist_agent", persist_dir=path)
    m1.add_memory(WAGE, importance=7)
    m1.add_memory(EGG, importance=5)
    assert len(m1) == 2

    MemoryStream.reset_client()  # จำลองการปิดโปรแกรม

    m2 = MemoryStream("persist_agent", persist_dir=path)
    assert len(m2) == 2
    got = m2.retrieve_memories("ของแพง เงินไม่พอ", n_results=2)
    assert WAGE in got or EGG in got


# ── ภาษาไทย ──

def test_thai_normalization_applied():
    """สระซ้ำ/ช่องว่างเกิน ต้องถูกทำให้เป็นมาตรฐานก่อนเก็บ"""
    m = MemoryStream("agent_norm")
    m.add_memory("ของ    แพง   ขึ้นนน", importance=5)
    stored = m.collection.get()["documents"][0]
    assert "    " not in stored


# ── ความปลอดภัยเมื่อรันหลายเธรด ──

def test_concurrent_agents_can_use_memory():
    """เจอจริงตอนรันเคส PARAMETER: broadcast_event_async ยิง agent พร้อมกัน
    30 เธรด แล้วพังหมดด้วย

        Cannot copy out of meta tensor      (โหลด SentenceTransformer ซ้อนกัน)
        Could not connect to tenant default_tenant / 'ephemeral' / bindings
                                            (สร้าง chroma client ซ้อนกัน)

    เทสต์ชุดอื่นรันทีละตัวจึงจับไม่ได้
    """
    import concurrent.futures as cf

    errors = []

    def work(i: int):
        try:
            m = MemoryStream(f"concurrent_{i}")
            m.add_memory(f"ราคาของขึ้นอีกแล้วรอบที่ {i}", importance=5)
            return m.retrieve_memories("ของแพง", n_results=1)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")
            return None

    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(work, range(12)))

    assert not errors, f"พังตอนรันหลายเธรด: {errors[:3]}"
    assert all(r for r in results), "บาง thread ไม่ได้ความจำกลับมา"


def test_warmup_is_idempotent():
    MemoryStream.warmup()
    MemoryStream.warmup()
    m = MemoryStream("after_warmup")
    m.add_memory("ทดสอบหลัง warmup", importance=5)
    assert len(m) == 1
