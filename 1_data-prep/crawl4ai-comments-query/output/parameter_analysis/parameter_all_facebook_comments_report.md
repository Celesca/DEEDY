# PARAMETER Gelato Facebook Comment Analysis

Generated from 219 unique Crawl4AI records; **213** were included in aggregate metrics.

## Overview

| Raw | Unique | Analyzed | Excluded | Posts |
| --- | --- | --- | --- | --- |
| 219 | 219 | 213 | 6 | 7 |

## Sentiment

| Label | Count | Percent |
| --- | --- | --- |
| neutral | 99 | 46.5% |
| positive | 89 | 41.8% |
| negative | 25 | 11.7% |

## Stance

| Stance | Count | Percent |
| --- | --- | --- |
| neutral | 151 | 70.9% |
| supportive | 28 | 13.1% |
| inquiry | 20 | 9.4% |
| critical_question | 6 | 2.8% |
| critical | 6 | 2.8% |
| mixed | 2 | 0.9% |

## Emotions

| Emotion | Count | Percent |
| --- | --- | --- |
| neutral | 146 | 68.5% |
| joy | 33 | 15.5% |
| fear_concern | 11 | 5.2% |
| trust | 10 | 4.7% |
| disappointment | 7 | 3.3% |
| anger | 4 | 1.9% |
| surprise | 2 | 0.9% |

## Themes

| Theme | Count | Percent |
| --- | --- | --- |
| other | 99 | 46.5% |
| ownership_business | 37 | 17.4% |
| service_experience | 31 | 14.6% |
| taste_quality | 24 | 11.3% |
| brand_communication | 19 | 8.9% |
| price_value | 18 | 8.5% |
| humor_sarcasm | 18 | 8.5% |
| consumption_rules | 17 | 8.0% |
| safety_incident | 15 | 7.0% |
| comparison | 6 | 2.8% |

## Sentiment by theme

| Theme | Positive | Neutral | Negative |
| --- | --- | --- | --- |
| consumption_rules | 8 | 8 | 1 |
| price_value | 8 | 3 | 7 |
| taste_quality | 17 | 3 | 4 |
| comparison | 5 | 1 | 0 |
| humor_sarcasm | 6 | 12 | 0 |
| other | 36 | 58 | 5 |
| service_experience | 13 | 12 | 6 |
| ownership_business | 19 | 16 | 2 |
| brand_communication | 10 | 4 | 5 |
| safety_incident | 1 | 3 | 11 |

## Highest-engagement posts

| Source | Visible comments | High engagement |
| --- | --- | --- |
| [thestandardwealth](https://www.facebook.com/thestandardwealth/posts/pfbid0qn8vkPMGYtnj6sg5mqgyn9yYhYU4JbcwEpihhYXpdS7cX3Q35CC2ibswy3g6nRqNl) | 59 | yes |
| [bangkokbiznews](https://www.facebook.com/bangkokbiznews/posts/pfbid0M3bF9g6TdVUurHhiehGAGXEEAv7WTrM3YkVkgaiLjnTzah2iwvM3P212GLjhKntcl) | 47 | yes |
| [CheckBait](https://www.facebook.com/CheckBait/posts/pfbid035UXjoNPk5ajNxEV5Mr9CjXinRdrpgbrL88dUtxuQ55LiaLZ6fpXHAZNmLVTT9fJql) | 42 | yes |
| [thansettakij](https://www.facebook.com/thansettakij/posts/pfbid0NhhMTFuESJzeWz5S2Q3zdcRjkkVPjbqRbKcaXS3vbptWxQHQXvFguPtJroXtDtFKl) | 31 | yes |
| [PrachachatOnline](https://www.facebook.com/PrachachatOnline/posts/pfbid02JBNZ3zVKDk9fvdn2yYn5Z29Zx5EFpqt4LbxhkvBkXZSPf3pJggcr3QwTRqfhKuqTl) | 21 | yes |
| [ThairathMoney](https://www.facebook.com/ThairathMoney/posts/pfbid02w7xxJ8diuPXN6gVXNkR8Faza9vbBBpPETVanxUiKcRDppKsj1m85PM3JkwmBTE2Xl) | 12 | no |
| [parameterthailand](https://www.facebook.com/parameterthailand/posts/pfbid02tUgmMBjN2CpXp6Y5sHfbYXtQFQseTgSsavbE8va1ohzfstdg2qjhDFXzn5StMsjl) | 1 | no |

## Top keywords

`ดี` (25), `อร่อย` (19), `จริง` (18), `เจ้าของ` (16), `กิน` (15), `ร้าน` (15), `เจลาโต้` (12), `ไอติม` (12), `555` (11), `เศษแก้ว` (11), `แก้ว` (11), `เชฟ` (10), `พูด` (9), `หุ้น` (9), `ลูกค้า` (9), `ราคา` (8), `ปาก` (8), `ชอบ` (8), `บริษัท` (7), `parameter` (7)

## Method and limitations

- Sentiment, stance, emotion, sarcasm-related themes, and topics use transparent Thai/English lexicons and rules; they are a baseline, not human gold labels.
- Comments resembling a merged Facebook post/DOM block remain in the annotated JSONL but are excluded from aggregate metrics.
- Counts represent comments visible to the authenticated Crawl4AI profile, not all Facebook comments.
- Facebook ranking, moderation, privacy settings, and DOM changes can affect coverage.
- Sentiment and sarcasm are rule-based Thai/English estimates; validate a sample manually before publication.
- Large merged DOM blocks are preserved but excluded from aggregates when they resemble post text plus comments.
