#!/usr/bin/env python3
"""
เทียบโมเดล embedding สำหรับการค้นความจำภาษาไทย (Phase 2 / D4)

ทำไมต้องวัด: ChromaDB ใช้ all-MiniLM-L6-v2 เป็นค่าปริยาย ซึ่งเป็นโมเดลภาษาอังกฤษ
ถ้าใช้กับไทยแล้ว retrieval เพี้ยน agent จะนึกถึงเรื่องที่ไม่เกี่ยวข้องตอนตัดสินใจ
และต้องแก้ให้จบ **ก่อน** สร้างประชากรใน Phase 3 ไม่งั้นต้อง re-index ใหม่ทั้งหมด

วัดด้วยชุดความจำไทยจริง + คำค้นที่รู้คำตอบล่วงหน้า
ตัวชี้วัด: Recall@2, Recall@3, MRR (ยิ่งสูงยิ่งดี)

ใช้:
    python scripts/eval_embeddings_th.py
    python scripts/eval_embeddings_th.py --models a,b
"""
import argparse
import sys
import time
from typing import Dict, List

# ── ชุดทดสอบ: ความจำของ agent คนหนึ่ง ──
MEMORIES = {
    "wage": "เห็นเพื่อนในทวิตเตอร์บ่นเรื่องค่าแรงขั้นต่ำไม่ขึ้นมาหลายปีแล้ว",
    "egg": "กินข้าวไข่เจียวปากซอยราคา 50 บาท แพงขึ้นกว่าเดิมเยอะ",
    "shrine": "เพิ่งไปไหว้พระแม่ลักษมีที่เซ็นทรัลเวิลด์มาขอให้ถูกหวย",
    "probe": "เมื่อปีก่อน รุ่นพี่ที่ทำงานโพสต์วิจารณ์นโยบายกระทรวง แล้วโดนตั้งกรรมการสอบสวน",
    "electric": "บิลค่าไฟเดือนนี้ขึ้นมาอีกเกือบพัน ทั้งที่ใช้เท่าเดิม",
    "tuition": "ลูกเพิ่งสอบติดมหาวิทยาลัย ค่าเทอมกับค่าหอรวมแล้วหนักมาก",
    "flood": "ปีที่แล้วน้ำท่วมบ้านที่ต่างจังหวัด ต้องซ่อมเองทั้งหมด",
    "traffic": "รถติดมากตอนเช้า ต้องออกจากบ้านตีห้าถึงจะทันเข้างาน",
}

# คำค้น -> ความจำที่ "ควรจะ" ถูกดึงขึ้นมา (เรียงตามความเกี่ยวข้อง)
QUERIES = [
    ("รัฐบาลประกาศขึ้นภาษีมูลค่าเพิ่ม เงินไม่พอใช้", ["wage", "egg", "electric", "tuition"]),
    ("อยากวิจารณ์รัฐบาลแต่กลัวโดนดำเนินคดี", ["probe"]),
    ("ค่าครองชีพแพงขึ้นทุกอย่าง", ["egg", "electric", "wage", "tuition"]),
    ("ภาระค่าใช้จ่ายเรื่องลูกเรียนหนังสือ", ["tuition"]),
    ("ปัญหาการเดินทางไปทำงาน", ["traffic"]),
]

DEFAULT_MODELS = [
    "chroma-default",  # all-MiniLM-L6-v2 (อังกฤษ) — ของเดิม ใช้เป็นฐานเปรียบเทียบ
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
]


def embed_with_chroma_default(texts: List[str]) -> List[List[float]]:
    from chromadb.utils import embedding_functions

    fn = embedding_functions.DefaultEmbeddingFunction()
    return fn(texts)


def embed_with_st(model_name: str, texts: List[str], is_query: bool = False):
    from sentence_transformers import SentenceTransformer

    if not hasattr(embed_with_st, "_cache"):
        embed_with_st._cache = {}
    if model_name not in embed_with_st._cache:
        embed_with_st._cache[model_name] = SentenceTransformer(model_name)
    model = embed_with_st._cache[model_name]

    # โมเดลตระกูล e5 ต้องใส่ prefix ไม่งั้นคุณภาพตกอย่างมีนัยสำคัญ
    if "e5" in model_name.lower():
        prefix = "query: " if is_query else "passage: "
        texts = [prefix + t for t in texts]

    return model.encode(texts, normalize_embeddings=True).tolist()


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def evaluate(model_name: str) -> Dict[str, float]:
    keys = list(MEMORIES.keys())
    docs = [MEMORIES[k] for k in keys]

    t0 = time.time()
    if model_name == "chroma-default":
        doc_vecs = embed_with_chroma_default(docs)
        query_vecs = embed_with_chroma_default([q for q, _ in QUERIES])
    else:
        doc_vecs = embed_with_st(model_name, docs, is_query=False)
        query_vecs = embed_with_st(model_name, [q for q, _ in QUERIES], is_query=True)
    elapsed = time.time() - t0

    r2 = r3 = mrr = 0.0
    details = []
    for (query, gold), qv in zip(QUERIES, query_vecs):
        ranked = sorted(
            zip(keys, (cosine(qv, dv) for dv in doc_vecs)),
            key=lambda kv: -kv[1],
        )
        order = [k for k, _ in ranked]

        hit2 = len(set(order[:2]) & set(gold)) / min(2, len(gold))
        hit3 = len(set(order[:3]) & set(gold)) / min(3, len(gold))
        rank = next((i + 1 for i, k in enumerate(order) if k in gold), None)
        r2 += hit2
        r3 += hit3
        mrr += 1 / rank if rank else 0.0
        details.append((query, order[:3], gold))

    n = len(QUERIES)
    return {
        "recall@2": r2 / n,
        "recall@3": r3 / n,
        "mrr": mrr / n,
        "seconds": elapsed,
        "details": details,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="รายชื่อโมเดลคั่นด้วย comma")
    ap.add_argument("--verbose", action="store_true", help="แสดงลำดับผลค้นของทุกคำค้น")
    args = ap.parse_args()

    models = args.models.split(",") if args.models else DEFAULT_MODELS
    results = {}

    for m in models:
        print(f"กำลังทดสอบ {m} ...", flush=True)
        try:
            results[m] = evaluate(m)
        except Exception as e:  # noqa: BLE001
            print(f"  ล้มเหลว: {str(e)[:160]}")

    print("\n" + "=" * 84)
    print(f"{'model':<52}{'R@2':>8}{'R@3':>8}{'MRR':>8}{'วินาที':>8}")
    print("=" * 84)
    for m, r in sorted(results.items(), key=lambda kv: -kv[1]["mrr"]):
        print(f"{m:<52}{r['recall@2']:>8.2f}{r['recall@3']:>8.2f}{r['mrr']:>8.2f}{r['seconds']:>8.1f}")

    print("\n" + "=" * 84)
    print("เกณฑ์ผ่าน Phase 2: คำค้น 'รัฐบาลขึ้นภาษี เงินไม่พอใช้'")
    print("ต้องได้เรื่องเงิน 2 อันแรก และห้ามได้ 'ไหว้พระแม่ลักษมี'")
    print("=" * 84)
    for m, r in results.items():
        query, top3, gold = r["details"][0]
        ok = "shrine" not in top3[:2] and len(set(top3[:2]) & set(gold)) == 2
        print(f"\n{'✅' if ok else '❌'} {m}")
        print(f"   ได้: {' > '.join(MEMORIES[k][:26] for k in top3)}")

    if args.verbose:
        for m, r in results.items():
            print(f"\n──── {m} ────")
            for query, top3, gold in r["details"]:
                mark = "✅" if top3[0] in gold else "❌"
                print(f"  {mark} {query}")
                for k in top3:
                    print(f"       {'*' if k in gold else ' '} {MEMORIES[k][:60]}")


if __name__ == "__main__":
    sys.exit(main())
