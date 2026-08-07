#!/usr/bin/env python3
"""Deterministic Thai/English sentiment and theme analysis for Crawl4AI JSONL.

The collector intentionally stores raw visible comments.  This module creates a
reproducible analysis layer without requiring an API key or sending comment text
to a third party.  It keeps questionable DOM blocks in the annotated JSONL but
excludes them from aggregate metrics.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


TOKEN_RE = re.compile(r"[ก-๙]+|[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

POSITIVE = {
    "อร่อย": 2, "ดี": 1, "ชอบ": 2, "รัก": 2, "คุ้ม": 2, "ผ่าน": 1,
    "เยี่ยม": 2, "สุดยอด": 2, "หอม": 1, "เข้มข้น": 1, "ประทับใจ": 2,
    "สนับสนุน": 1, "เห็นด้วย": 1, "ซื้อซ้ำ": 2, "ถูกใจ": 2, "จริง": 1,
    "delicious": 2, "good": 1, "love": 2, "great": 2, "worth": 2,
}
NEGATIVE = {
    "แพง": -2, "ไม่คุ้ม": -2, "แย่": -2, "ห่วย": -2, "ไม่อร่อย": -2,
    "ดราม่า": -1, "โกหก": -2, "หลอก": -2, "ผิดหวัง": -2, "เกลียด": -2,
    "สงสัย": -1, "เว่อร์": -1, "กะลา": -2, "หยาบ": -2, "ขาดทุน": -1,
    "เจ๊ง": -2, "เศษแก้ว": -3, "บาด": -2, "เลือด": -2, "ปัญหา": -1,
    "เทา": -1, "overpriced": -2, "expensive": -2, "bad": -2,
    "disappointed": -2, "scam": -3, "problem": -1,
}
NEGATION_RE = re.compile(r"(?:ไม่|ไม่ได้|ไม่มี|ไม่ค่อย|หาได้ไม่)\s*$")
INTENSIFIER_RE = re.compile(r"(?:โคตร|มาก|สุดๆ|สุด|อย่างแรง|very|so)\s*$", re.IGNORECASE)

THEMES: dict[str, tuple[str, ...]] = {
    "price_value": ("ราคา", "แพง", "คุ้ม", "บาท", "ถ้วย", "กรัม", "overpriced", "value"),
    "taste_quality": ("อร่อย", "รสชาติ", "รส", "เนื้อ", "หอม", "หวาน", "ชิม", "อร่อยไหม", "delicious"),
    "safety_incident": ("เศษแก้ว", "แก้ว", "บาด", "เลือด", "ปลอดภัย", "อุบัติเหตุ", "เจ็บ", "safety"),
    "consumption_rules": ("ห้ามเคี้ยว", "เคี้ยว", "ถ่ายรูป", "อุณหภูมิ", "ละลาย", "กิน", "ตักคำ"),
    "brand_communication": ("mindset", "กะลา", "สื่อสาร", "ปาก", "พูด", "คำพูด", "ดูถูก", "ทัศนคติ"),
    "ownership_business": ("เจ้าของ", "หุ้น", "ผู้ถือหุ้น", "บริษัท", "เชฟ", "ลงทุน", "ขาดทุน", "รายได้", "กรรมการ"),
    "service_experience": ("พนักงาน", "บริการ", "ร้าน", "คิว", "ต่อแถว", "ลูกค้า", "สยามพารากอน"),
    "comparison": ("แดรี่ควีน", "dq", "ร้านอื่น", "เทียบ", "เปรียบเทียบ", "คู่แข่ง"),
    "humor_sarcasm": ("ฮ่า", "555", "ประชด", "ละคร", "แซะ", "ขำ", "ตลก", "5555"),
}

EMOTION_TERMS: dict[str, tuple[str, ...]] = {
    "joy": ("อร่อย", "ชอบ", "รัก", "ดีใจ", "555", "ฮ่า", "delicious"),
    "anger": ("โกรธ", "โมโห", "ห่วย", "โกหก", "หลอก", "กะลา", "หยาบ"),
    "disappointment": ("แพง", "ไม่คุ้ม", "ผิดหวัง", "แย่", "ไม่อร่อย"),
    "fear_concern": ("เศษแก้ว", "บาด", "เลือด", "ปลอดภัย", "กังวล", "กลัว"),
    "trust": ("เชื่อ", "จริง", "เห็นด้วย", "สนับสนุน"),
    "surprise": ("ไม่คิด", "โห", "ว้าว", "ตกใจ", "จริงเหรอ"),
}

STANCE_SUPPORT = ("อร่อย", "ชอบ", "คุ้ม", "ผ่าน", "สนับสนุน", "เห็นด้วย", "ซื้อซ้ำ", "รัก")
STANCE_CRITIC = ("แพง", "ไม่คุ้ม", "ห้าม", "โกหก", "หลอก", "ผิดหวัง", "แย่", "ดราม่า", "ไม่อร่อย", "สงสัย")
STANCE_QUESTION = ("ไหม", "หรือเปล่า", "ทำไม", "จริงไหม", "จริงเหรอ", "สงสัย", "อย่างไร")

STOPWORDS = {
    "และ", "หรือ", "ที่", "ของ", "ใน", "ให้", "ได้", "เป็น", "ก็", "แล้ว", "มาก",
    "ครับ", "ค่ะ", "นะ", "เลย", "คน", "นี้", "นั้น", "มัน", "ผม", "ฉัน", "เรา",
    "the", "and", "for", "with", "that", "this", "you", "เป็นการ", "จาก",
}

KEYWORD_TERMS = tuple(
    sorted(
        {
            "parameter", "พารามิเตอร์", "เจลาโต้", "ไอติม", "กฤษณ์", "ultra smooth",
            *POSITIVE.keys(), *NEGATIVE.keys(),
            *(term for terms in THEMES.values() for term in terms),
        },
        key=lambda term: (-len(term), term.casefold()),
    )
)
KEYWORD_TERMS = tuple(
    term for term in KEYWORD_TERMS
    if term not in {"ถูกใจ", "ตอบกลับ", "ดูเพิ่มเติม", "แชร์", "แก้ไขแล้ว", "ดูคำแปล"}
)


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = URL_RE.sub(" ", text)
    text = text.replace("\u200b", " ").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text: str) -> str:
    thai = len(re.findall(r"[ก-๙]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if thai and latin:
        return "th-en"
    if thai:
        return "th"
    if latin:
        return "en"
    return "other"


def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def _term_score(text: str, term: str, value: int) -> int:
    lowered = text.casefold()
    start = lowered.find(term.casefold())
    if start < 0:
        return 0
    context = text[max(0, start - 14):start]
    score = value
    if NEGATION_RE.search(context):
        score = -score
    if INTENSIFIER_RE.search(context):
        score = int(math.copysign(abs(score) + 1, score))
    return score


def classify_sentiment(text: str) -> dict[str, Any]:
    scores: dict[str, int] = {}
    for term, value in POSITIVE.items():
        if term.casefold() in text.casefold():
            scores[term] = _term_score(text, term, value)
    for term, value in NEGATIVE.items():
        if term.casefold() in text.casefold():
            scores[term] = _term_score(text, term, value)
    raw = sum(scores.values())
    if raw > 0:
        label = "positive"
    elif raw < 0:
        label = "negative"
    else:
        label = "neutral"
    scale = max(3, sum(abs(value) for value in scores.values()))
    return {
        "label": label,
        "score": raw,
        "normalized_score": round(max(-1.0, min(1.0, raw / scale)), 3),
        "matched_terms": sorted(scores),
        "confidence": round(min(1.0, abs(raw) / 4), 3),
    }


def classify_stance(text: str, sentiment_label: str) -> str:
    support = bool(matched_terms(text, STANCE_SUPPORT))
    critic = bool(matched_terms(text, STANCE_CRITIC))
    question = "?" in text or "？" in text or bool(matched_terms(text, STANCE_QUESTION))
    if question and critic:
        return "critical_question"
    if question and not support:
        return "inquiry"
    if support and critic:
        return "mixed"
    if support:
        return "supportive"
    if critic:
        return "critical"
    return "neutral"


def classify_emotion(text: str, sentiment_label: str) -> str:
    hits = [(emotion, len(matched_terms(text, terms))) for emotion, terms in EMOTION_TERMS.items()]
    hits = [(emotion, count) for emotion, count in hits if count]
    if hits:
        return max(hits, key=lambda pair: pair[1])[0]
    return "neutral"


def classify_themes(text: str) -> list[str]:
    hits = [(theme, len(matched_terms(text, terms))) for theme, terms in THEMES.items()]
    selected = [theme for theme, count in hits if count]
    return selected or ["other"]


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    lowered = text.casefold()
    counts = Counter()
    for term in KEYWORD_TERMS:
        count = lowered.count(term.casefold())
        if count:
            counts[term] = count
    return [token for token, _ in counts.most_common(limit)]


def source_slug(post_url: str) -> str:
    path = urlsplit(post_url).path.strip("/")
    return path.split("/", 1)[0] if path else "unknown"


def quality_flags(text: str) -> list[str]:
    flags: list[str] = []
    if len(text) > 2000:
        flags.append("possible_post_shell_or_merged_dom_block")
    if text.count("http") >= 2:
        flags.append("contains_many_urls")
    if "โพสต์ที่แชร์" in text and len(text) > 1200:
        flags.append("contains_shared_post_boilerplate")
    return flags


def annotate_record(record: dict[str, Any]) -> dict[str, Any] | None:
    text = normalize_text(record.get("comment_text"))
    if not text:
        return None
    sentiment = classify_sentiment(text)
    flags = quality_flags(text)
    result = dict(record)
    result.update(
        {
            "analysis_text": text,
            "analysis_language": detect_language(text),
            "sentiment": sentiment,
            "stance": classify_stance(text, sentiment["label"]),
            "emotion": classify_emotion(text, sentiment["label"]),
            "themes": classify_themes(text),
            "keywords": extract_keywords(text),
            "quality_flags": flags,
            "included_in_aggregate": not bool(flags),
        }
    )
    return result


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    parse_errors = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            if isinstance(value, dict):
                records.append(value)
    return records, parse_errors


def dedupe_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    duplicates = 0
    for record in records:
        key = str(record.get("id") or "")
        if not key:
            key = f"{record.get('post_url')}\0{normalize_text(record.get('comment_text')).casefold()}"
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        output.append(record)
    return output, duplicates


def _pct(count: int, total: int) -> float:
    return round(100 * count / total, 1) if total else 0.0


def _distribution(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    def value_for(record: dict[str, Any]) -> str:
        if field == "sentiment_label":
            return str(record.get("sentiment", {}).get("label") or "unknown")
        return str(record.get(field) or "unknown")

    counts = Counter(value_for(record) for record in records)
    total = len(records)
    return {key: {"count": value, "percent": _pct(value, total)} for key, value in counts.most_common()}


def build_summary(records: list[dict[str, Any]], raw_count: int, parse_errors: int, duplicates: int, min_high: int) -> dict[str, Any]:
    usable = [record for record in records if record.get("included_in_aggregate")]
    excluded = [record for record in records if not record.get("included_in_aggregate")]
    posts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in usable:
        posts[str(record.get("post_url") or "unknown")].append(record)

    post_rows = []
    for post_url, items in sorted(posts.items(), key=lambda pair: len(pair[1]), reverse=True):
        post_rows.append(
            {
                "post_url": post_url,
                "source": source_slug(post_url),
                "visible_comment_count": len(items),
                "sentiment": _distribution(items, "sentiment_label"),
                "themes": dict(Counter(theme for item in items for theme in item.get("themes", []))),
                "high_engagement": len(items) >= min_high,
            }
        )

    theme_counts = Counter(theme for record in usable for theme in record.get("themes", []))
    sentiment_by_theme: dict[str, dict[str, int]] = {}
    for theme in theme_counts:
        sentiment_by_theme[theme] = dict(Counter(record["sentiment"]["label"] for record in usable if theme in record.get("themes", [])))
    keywords = Counter(keyword for record in usable for keyword in record.get("keywords", []))
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(usable, key=lambda item: abs(item["sentiment"]["score"]), reverse=True):
        for theme in record.get("themes", []):
            if len(examples[theme]) < 3:
                examples[theme].append(
                    {
                        "post_url": record.get("post_url"),
                        "sentiment": record["sentiment"]["label"],
                        "stance": record.get("stance"),
                        "text": record["analysis_text"][:280],
                    }
                )

    return {
        "topic": "PARAMETER gelato",
        "method": "Crawl4AI-visible Facebook comments with deterministic lexicon/rule analysis",
        "raw_records": raw_count,
        "unique_records": len(records),
        "included_in_aggregate": len(usable),
        "excluded_quality_records": len(excluded),
        "parse_errors": parse_errors,
        "duplicates_removed": duplicates,
        "posts_analyzed": len(posts),
        "sentiment": _distribution(usable, "sentiment_label"),
        "stance": _distribution(usable, "stance"),
        "emotion": _distribution(usable, "emotion"),
        "language": _distribution(usable, "analysis_language"),
        "themes": {key: {"count": value, "percent": _pct(value, len(usable))} for key, value in theme_counts.most_common()},
        "sentiment_by_theme": sentiment_by_theme,
        "top_keywords": [{"keyword": key, "count": value} for key, value in keywords.most_common(30)],
        "posts": post_rows,
        "representative_comments": dict(examples),
        "limitations": [
            "Counts represent comments visible to the authenticated Crawl4AI profile, not all Facebook comments.",
            "Facebook ranking, moderation, privacy settings, and DOM changes can affect coverage.",
            "Sentiment and sarcasm are rule-based Thai/English estimates; validate a sample manually before publication.",
            "Large merged DOM blocks are preserved but excluded from aggregates when they resemble post text plus comments.",
        ],
    }


def _md_table(rows: list[list[str]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown(summary: dict[str, Any]) -> str:
    def dist_rows(dist: dict[str, dict[str, Any]]) -> list[list[str]]:
        return [[key, str(value["count"]), f"{value['percent']:.1f}%"] for key, value in dist.items()]

    lines = [
        "# PARAMETER Gelato Facebook Comment Analysis",
        "",
        f"Generated from {summary['unique_records']} unique Crawl4AI records; **{summary['included_in_aggregate']}** were included in aggregate metrics.",
        "",
        "## Overview",
        "",
        _md_table(
            [[str(summary[key]) for key in ("raw_records", "unique_records", "included_in_aggregate", "excluded_quality_records", "posts_analyzed")]],
            ["Raw", "Unique", "Analyzed", "Excluded", "Posts"],
        ),
        "",
        "## Sentiment",
        "",
        _md_table(dist_rows(summary["sentiment"]), ["Label", "Count", "Percent"]),
        "",
        "## Stance",
        "",
        _md_table(dist_rows(summary["stance"]), ["Stance", "Count", "Percent"]),
        "",
        "## Emotions",
        "",
        _md_table(dist_rows(summary["emotion"]), ["Emotion", "Count", "Percent"]),
        "",
        "## Themes",
        "",
        _md_table([[key, str(value["count"]), f"{value['percent']:.1f}%"] for key, value in summary["themes"].items()], ["Theme", "Count", "Percent"]),
        "",
        "## Sentiment by theme",
        "",
        _md_table(
            [
                [
                    theme,
                    str(values.get("positive", 0)),
                    str(values.get("neutral", 0)),
                    str(values.get("negative", 0)),
                ]
                for theme, values in summary["sentiment_by_theme"].items()
            ],
            ["Theme", "Positive", "Neutral", "Negative"],
        ),
        "",
        "## Highest-engagement posts",
        "",
        _md_table(
            [[f"[{row['source']}]({row['post_url']})", str(row["visible_comment_count"]), "yes" if row["high_engagement"] else "no"] for row in summary["posts"]],
            ["Source", "Visible comments", "High engagement"],
        ),
        "",
        "## Top keywords",
        "",
        ", ".join(f"`{item['keyword']}` ({item['count']})" for item in summary["top_keywords"][:20]),
        "",
        "## Method and limitations",
        "",
        "- Sentiment, stance, emotion, sarcasm-related themes, and topics use transparent Thai/English lexicons and rules; they are a baseline, not human gold labels.",
        "- Comments resembling a merged Facebook post/DOM block remain in the annotated JSONL but are excluded from aggregate metrics.",
    ]
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def run(input_path: Path, output_dir: Path, min_high: int) -> dict[str, Any]:
    raw, parse_errors = load_jsonl(input_path)
    unique, duplicates = dedupe_records(raw)
    annotated = [result for record in unique if (result := annotate_record(record)) is not None]
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = output_dir / f"{input_path.stem}_annotated.jsonl"
    with annotated_path.open("w", encoding="utf-8") as handle:
        for record in annotated:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = build_summary(annotated, len(raw), parse_errors, duplicates, min_high)
    (output_dir / f"{input_path.stem}_analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / f"{input_path.stem}_report.md").write_text(render_markdown(summary), encoding="utf-8")
    high_posts = {row["post_url"] for row in summary["posts"] if row["high_engagement"]}
    high_path = output_dir / f"{input_path.stem}_high_comment_annotated.jsonl"
    with high_path.open("w", encoding="utf-8") as handle:
        for record in annotated:
            if record.get("included_in_aggregate") and record.get("post_url") in high_posts:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Crawl4AI Facebook comments for PARAMETER gelato.")
    parser.add_argument("--input", type=Path, required=True, help="Input UTF-8 JSONL from facebook_comments.py.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory; defaults beside input.")
    parser.add_argument("--min-high-comments", type=int, default=20, help="Minimum visible comments for high-engagement posts.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.min_high_comments <= 0:
        raise SystemExit("--min-high-comments must be positive")
    if not args.input.exists():
        raise SystemExit(f"Input does not exist: {args.input}")
    output_dir = args.output_dir or args.input.parent / "analysis"
    summary = run(args.input, output_dir, args.min_high_comments)
    print(json.dumps({"posts": summary["posts_analyzed"], "comments": summary["included_in_aggregate"], "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
