import json
import re
import string


def clean_text(text: str) -> str:
    r"""
    Cleans text by retaining only:
    - Thai characters (\u0e00-\u0e7f)
    - English letters (a-zA-Z)
    - Digits (0-9)
    - Standard ASCII punctuation / markdown symbols (!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~)
    - Whitespace (spaces, newlines, tabs)

    Strips emojis, non-Latin foreign scripts (Chinese, Japanese, Arabic, etc.), and control characters.
    """
    if not isinstance(text, str):
        return text

    # Build pattern matching any character NOT in the allowed set
    allowed_pattern = re.compile(
        r"[^\u0e00-\u0e7fa-zA-Z0-9" + re.escape(string.punctuation) + r"\s]"
    )
    return allowed_pattern.sub("", text)


def load_jsonl_records(input_file: str):
    """
    Reads a JSONL file line-by-line, with stream fallback for concatenated JSON objects.
    """
    records = []

    with open(input_file, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    # Try parsing line-by-line first
    lines = content.splitlines()
    line_by_line_success = True
    temp_records = []

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            record = json.loads(line_str, strict=False)
            temp_records.append(record)
        except json.JSONDecodeError:
            line_by_line_success = False
            break

    if line_by_line_success and temp_records:
        return temp_records

    # Fallback to stream decoding if line-by-line parsing encountered concatenated JSON objects
    decoder = json.JSONDecoder(strict=False)
    pos = 0
    length = len(content)

    while pos < length:
        start_idx = content.find('{"topic"', pos)
        if start_idx == -1:
            start_idx = content.find('{', pos)
            if start_idx == -1:
                break
        try:
            obj, end_idx = decoder.raw_decode(content, start_idx)
            if isinstance(obj, dict) and "topic" in obj:
                records.append(obj)
            pos = end_idx
        except json.JSONDecodeError:
            pos = start_idx + 1

    return records


def clean_scraped_content(input_file: str, output_file: str):
    print(f"Reading and parsing {input_file}...")
    records = load_jsonl_records(input_file)
    print(f"Loaded {len(records)} records from JSONL.")

    cleaned_records = []
    for record in records:
        # Clean topic
        if "topic" in record:
            record["topic"] = clean_text(record["topic"])

        # Clean title and markdown content in scraped_data
        if "scraped_data" in record and isinstance(record["scraped_data"], list):
            for item in record["scraped_data"]:
                if isinstance(item, dict):
                    if "title" in item:
                        item["title"] = clean_text(item["title"])
                    if "content" in item:
                        item["content"] = clean_text(item["content"])

        cleaned_records.append(record)

    print(f"Writing cleaned data to {output_file}...")
    with open(output_file, "w", encoding="utf-8-sig") as f:
        for record in cleaned_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Completed text cleaning for {len(cleaned_records)} records!")


if __name__ == "__main__":
    input_path = "./data/scraped_content.jsonl"
    output_path = "./data/scraped_content_cleaned.jsonl"
    clean_scraped_content(input_path, output_path)