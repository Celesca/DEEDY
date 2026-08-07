# Facebook News Comment Query with Crawl4AI

This folder queries Facebook for posts related to a news headline, keyword set,
or canonical news URL and collects the comments that are visible to a
user-controlled Facebook browser session.

The implementation uses [Crawl4AI](https://github.com/unclecode/crawl4ai) with
a persistent Chromium profile. It does **not** accept a Facebook password, copy
raw cookies into source code, solve CAPTCHAs, bypass checkpoints, or access
comments that the logged-in user cannot normally view.

## What it does

1. Opens Facebook post search for a supplied news query.
2. Scrolls the rendered search page and discovers Facebook post permalinks.
3. Opens each post with the same authenticated Crawl4AI profile.
4. Clicks visible “view more comments/replies” controls and scrolls the page.
5. Extracts accessible comment blocks using semantic roles and labels.
6. Appends de-duplicated records to UTF-8 JSONL.

You can also skip Facebook search and crawl one known post URL directly.

## Current limitations

- Facebook changes its React DOM and accessible labels frequently. The
  extractor avoids generated CSS class names, but selectors may still need
  maintenance.
- Search results and comment availability differ by account, language, region,
  privacy setting, moderation state, and Facebook ranking.
- Only comments already visible to the authenticated user are collected.
- “Most relevant” may be Facebook’s default ordering. This script does not
  claim that the collected comments are a complete or representative sample.
- Author display names are omitted unless `--include-author` is explicitly
  supplied.
- The script is a browser collector, not the Facebook Graph API. For a Page or
  dataset you administer, prefer an official Meta API when it provides the
  required fields.

## Requirements

- Python 3.10 or newer
- Chromium installed by Crawl4AI/Playwright
- A Facebook account permitted to view the posts being collected
- Compliance with Facebook’s terms, the source’s privacy restrictions, and
  your research-ethics or institutional requirements

## 1. Install

From this folder:

```bash
cd 1_data-prep/comments-query
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
crawl4ai-setup
crawl4ai-doctor
crwl profiles
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

If Crawl4AI reports a missing browser, install Chromium manually:

```bash
python -m playwright install chromium
```

The dependency range targets Crawl4AI 0.9.x. The implementation uses
`AsyncWebCrawler`, `BrowserConfig`, `CrawlerRunConfig`, a persistent managed
browser, and JavaScript page interaction.

## 2. Create a logged-in profile

Use Crawl4AI’s profile manager:

```bash
crwl profiles
```

Choose **Create new profile**, give it a name such as `facebook-deedy`, and log
in to Facebook manually in the Chromium window. Return to the terminal and
press `q` to save the profile.

Crawl4AI normally stores it at a path similar to:

```text
~/.crawl4ai/profiles/facebook-deedy
```

Do not commit, zip, or share this directory. It contains authentication state.
Do not point the crawler at your everyday Chrome profile while Chrome is open;
use a dedicated Crawl4AI profile.

## 3. Verify authentication

```bash
python facebook_comments.py check-auth \
  --profile ~/.crawl4ai/profiles/facebook-deedy \
  --show-browser
```

The command opens `facebook.com/me`. It returns exit code `0` when the profile
is usable and exit code `2` if Facebook redirects to login or a checkpoint.

After the first successful check, omit `--show-browser` to run headlessly.

## 4. Search posts about a news story

Search using a distinctive Thai headline or keyword combination:

```bash
python facebook_comments.py search \
  --profile ~/.crawl4ai/profiles/facebook-deedy \
  --query "KFC กะเพราไม่แท้" \
  --max-posts 5 \
  --max-comments 100
```

You can use the canonical news URL as the query when Facebook posts are likely
to share that exact link:

```bash
python facebook_comments.py search \
  --profile ~/.crawl4ai/profiles/facebook-deedy \
  --query "https://www.prachachat.net/marketing/news-1957912" \
  --max-posts 10 \
  --output output/kfc_kaphrao_comments.jsonl
```

For a query from `1_data-prep/data/topic.json`, copy the topic or a focused set
of its keywords into `--query`. Short, distinctive queries generally work
better than the complete debate statement.

### Search options

| Option | Default | Purpose |
|---|---:|---|
| `--max-posts` | `5` | Maximum discovered Facebook posts to crawl |
| `--max-comments` | `100` | Maximum extracted comments per post |
| `--search-scroll-rounds` | `6` | Scroll passes on Facebook search |
| `--scroll-rounds` | `8` | Scroll passes on each post |
| `--click-rounds` | `6` | Passes clicking visible comment/reply expansion controls |
| `--locale` | `th-TH` | Browser locale and Facebook label language |
| `--show-browser` | off | Display Chromium for diagnosis |
| `--include-author` | off | Store visible display names; use only when justified |
| `--verbose` | off | Print Crawl4AI logs |

Increasing scroll or click rounds causes more requests and is not guaranteed to
produce a complete comment set. Keep settings conservative.

## 5. Crawl one known Facebook post

If a news article already contains the Facebook source URL, use `post` mode:

```bash
python facebook_comments.py post \
  --profile ~/.crawl4ai/profiles/facebook-deedy \
  --post-url "https://www.facebook.com/kfcth/posts/POST_ID" \
  --max-comments 200 \
  --output output/kfc_post_comments.jsonl
```

Supported URL shapes include Page/user posts, `story.php`, `permalink.php`,
group posts visible to the profile, Facebook videos, and reels.

## Output

The default file is:

```text
output/facebook_comments.jsonl
```

Each line is one comment:

```json
{
  "id": "d92d0a3cc0a4107c530c93b1",
  "record_type": "facebook_comment",
  "query": "KFC กะเพราไม่แท้",
  "post_url": "https://www.facebook.com/kfcth/posts/123",
  "comment_permalink": null,
  "comment_index": 1,
  "comment_text": "กะเพราต้องมีแค่ใบกะเพราจริง ๆ",
  "post_text": "ข้อความของโพสต์ต้นทาง",
  "collected_at": "2026-08-02T08:00:00+00:00",
  "locale": "th-TH",
  "collector": "crawl4ai"
}
```

`id` is a deterministic hash of the canonical post URL and normalized comment
text. Existing IDs are loaded before each run, so repeating the same command
appends only newly visible comments. The file is never overwritten.

When `--include-author` is used, the record can additionally contain
`author_display_name`. The extractor cannot guarantee that every display name
is parsed correctly, so do not use it as a stable user identifier.

## Recommended DEEDY workflow

1. Save each event to a separate output file.
2. Record the exact query, collection time, profile visibility assumptions, and
   CLI settings in the experiment manifest.
3. Preserve raw JSONL under restricted access.
4. Remove or pseudonymize identity fields before annotation or model input.
5. Split scenario-construction evidence and validation comments **before** any
   LLM summarization or labeling.
6. Treat the result as a convenience sample of visible Facebook discussion,
   not as a sample of the Thai population.

## Run tests

The parser and URL normalization tests do not open Facebook:

```bash
python -m unittest discover -s tests -v
```

Check the CLI without opening Facebook:

```bash
python facebook_comments.py --help
python facebook_comments.py search --help
python facebook_comments.py post --help
```

## 8. Analyze scraped comments

Run the deterministic Thai/English analysis pipeline after collecting comments:

```bash
python comment_analysis.py \
  --input output/parameter_all_facebook_comments.jsonl \
  --output-dir output/parameter_analysis \
  --min-high-comments 20
```

The pipeline writes four artifacts:

- `*_annotated.jsonl` — each comment with normalized text, language, sentiment
  score/label, stance, emotion, themes, keywords, and quality flags.
- `*_analysis.json` — machine-readable aggregate counts and per-post metrics.
- `*_report.md` — a human-readable report with sentiment, themes, emotions,
  stance, keywords, and sentiment-by-theme tables.
- `*_high_comment_annotated.jsonl` — comments from posts meeting the selected
  visible-comment threshold.

The baseline is local and deterministic: it does not require an API key or send
comment text to an external model. It preserves suspicious merged DOM blocks in
the annotated file while excluding them from aggregate metrics. Treat the
sentiment and sarcasm labels as screening estimates and manually validate a
sample before publication.

## 9. LLM analysis and clustering

For Thai sarcasm, context, mixed sentiment, and semantic clustering, use the
LLM pipeline instead of the deterministic baseline. It uses an OpenAI-compatible
endpoint (OpenRouter by default), sends comments in batches, validates structured
JSON responses, and asks the model for an executive synthesis.

Set the key in the environment; do not commit it:

```bash
export OPENROUTER_API_KEY="..."
export LLM_MODEL="qwen/qwen3.7-flash"
```

Then run:

```bash
python llm_comment_analysis.py \
  --input output/parameter_all_facebook_comments.jsonl \
  --output-dir output/parameter_analysis_llm \
  --batch-size 20 \
  --max-concurrency 2 \
  --min-high-comments 20
```

The LLM outputs are:

- `*_llm_annotated.jsonl` — model sentiment, score, stance, emotion,
  sarcasm, cluster, confidence, and short rationale per comment.
- `*_llm_analysis.json` — exact aggregate counts, cluster taxonomy, failures,
  and the model synthesis.
- `*_llm_report.md` — executive summary, sentiment/stance/cluster tables,
  sarcasm rate, high-engagement posts, and recommended actions.
- `*_llm_high_comment.jsonl` — classified comments from high-engagement posts.

The prompt treats comment text as untrusted data and never follows instructions
inside comments. Failed batches are reported instead of silently filling in
local-rule labels. Review provider costs, retention, and privacy terms before
sending social comments to an external model.

## Troubleshooting

### Facebook redirects to login or checkpoint

Stop the crawl. Run `crwl profiles`, open the dedicated profile, and complete
the login or review manually. The script intentionally does not automate these
steps.

### No post permalinks are found

- Try a shorter and more distinctive headline.
- Try the canonical news URL as `--query`.
- Add `--show-browser` and confirm that Facebook search results are visible.
- If you already know the Facebook URL, use `post` mode.

### A post is found but no comments are extracted

- Confirm that the browser visibly shows comments.
- Increase `--click-rounds` or `--scroll-rounds` gradually.
- Check whether Facebook changed the accessible `role="article"` structure or
  the Thai/English labels matched in `make_interaction_script()`.
- Comments rendered inside unsupported widgets or hidden by moderation cannot
  be collected by this implementation.

### Chromium profile is locked

Close the profile’s Chromium window and make sure no other crawler process is
using the same profile directory.

### Responsible-use boundary

Do not use this code to evade access controls, scrape private groups without
authorization, defeat rate limits, or build identity profiles. If Facebook or
the relevant Page disallows your collection method, use an approved Meta API,
data export, or another authorized source instead.

## References

- [Crawl4AI installation and quick start](https://github.com/unclecode/crawl4ai#-quick-start)
- [Browser and crawler configuration](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [Identity-based crawling and persistent profiles](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
- [JavaScript page interaction](https://docs.crawl4ai.com/core/page-interaction/)
