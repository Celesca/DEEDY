# PARAMETER Gelato — LLM Facebook Comment Report

Model: `qwen/qwen3.7-flash`. Classified comments: **219**. This report uses LLM labels, not the deterministic fallback.

## Executive summary

การวิเคราะห์ข้อมูลโซเชียลมีเดียชี้ให้เห็นว่ากระแสความสนใจต่อแบรนด์ PARAMETER Gelato มีแนวโน้มเชิงลบเป็นหลัก โดยกลุ่มผู้ใช้งานแสดงความกังวลและผิดหวังสูงที่สุด สาเหตุสำคัญมาจากความไม่ชัดเจนในโครงสร้างความเป็นเจ้าของ การสื่อสารที่สร้างภาพลักษณ์ขัดกับข้อเท็จจริง รวมถึงประเด็นความปลอดภัยและราคาที่ไม่สอดคล้องกับมูลค่าที่ได้รับ แม้จะมีเสียงชมเชยด้านรสชาติและประสบการณ์บริการบ้าง แต่ยังคงถูกบดบังด้วยกระแสวิพากษ์วิจารณ์และการใช้ภาษาประชดประชันอย่างกว้างขวาง

## Sentiment

| Label | Count | Percent |
| --- | ---: | ---: |
| negative | 101 | 46.1% |
| neutral | 86 | 39.3% |
| positive | 32 | 14.6% |

## Stance

| Stance | Count | Percent |
| --- | ---: | ---: |
| critical | 98 | 44.7% |
| neutral | 58 | 26.5% |
| inquiry | 31 | 14.2% |
| supportive | 28 | 12.8% |
| mixed | 4 | 1.8% |

## LLM clusters

| Cluster | Count | Percent |
| --- | ---: | ---: |
| brand_communication | 68 | 31.1% |
| general_reaction | 62 | 28.3% |
| ownership_business | 40 | 18.3% |
| comparison | 12 | 5.5% |
| safety_incident | 12 | 5.5% |
| taste_quality | 12 | 5.5% |
| price_value | 7 | 3.2% |
| service_experience | 3 | 1.4% |
| consumption_rules | 3 | 1.4% |

## Emotions and sarcasm

Sarcasm/irony detected: **42 (19.2%)**.

| Emotion | Count | Percent |
| --- | ---: | ---: |
| neutral | 81 | 22.2% |
| concern | 51 | 14.0% |
| anger | 50 | 13.7% |
| disappointment | 48 | 13.2% |
| humor | 46 | 12.6% |
| surprise | 41 | 11.2% |
| trust | 24 | 6.6% |
| joy | 24 | 6.6% |

## High-engagement posts

- [thestandardwealth](https://www.facebook.com/thestandardwealth/posts/pfbid0qn8vkPMGYtnj6sg5mqgyn9yYhYU4JbcwEpihhYXpdS7cX3Q35CC2ibswy3g6nRqNl) — 60 classified comments
- [bangkokbiznews](https://www.facebook.com/bangkokbiznews/posts/pfbid0M3bF9g6TdVUurHhiehGAGXEEAv7WTrM3YkVkgaiLjnTzah2iwvM3P212GLjhKntcl) — 48 classified comments
- [CheckBait](https://www.facebook.com/CheckBait/posts/pfbid035UXjoNPk5ajNxEV5Mr9CjXinRdrpgbrL88dUtxuQ55LiaLZ6fpXHAZNmLVTT9fJql) — 43 classified comments
- [thansettakij](https://www.facebook.com/thansettakij/posts/pfbid0NhhMTFuESJzeWz5S2Q3zdcRjkkVPjbqRbKcaXS3vbptWxQHQXvFguPtJroXtDtFKl) — 32 classified comments
- [PrachachatOnline](https://www.facebook.com/PrachachatOnline/posts/pfbid02JBNZ3zVKDk9fvdn2yYn5Z29Zx5EFpqt4LbxhkvBkXZSPf3pJggcr3QwTRqfhKuqTl) — 22 classified comments

## Model synthesis

### Positive drivers
- รสชาติและเนื้อสัมผัสผ่านเกณฑ์มาตรฐาน
- ประสบการณ์บริการแบบขำขันสร้างความบันเทิง
- การยืนยันข้อมูลจากแหล่งทางการเพิ่มความน่าเชื่อถือ
- ความนิยมต่อเนื่องแม้มีกระแสวิพากษ์

### Negative drivers
- ความคลุมเครือเรื่องโครงสร้างผู้ถือหุ้นและบทบาทเจ้าของ
- การสื่อสารแบรนด์ที่ดูโอ้อวดหรือขาดความจริงใจ
- ราคาที่สูงเมื่อเทียบกับปริมาณและความคุ้มค่า
- ประเด็นสิ่งแปลกปลอมเศษแก้วในผลิตภัณฑ์
- การเปรียบเทียบกับคู่แข่งที่ได้เปรียบกว่าด้านมาตรฐาน
- การใช้ภาษาหรือทัศนคติที่กระตุ้นอารมณ์โกรธ

### Polarization axes
- ตัวตนเจ้าของธุรกิจ versus ภาพลักษณ์เชฟมืออาชีพ
- ราคาพรีเมียม versus ความคาดหวังผู้บริโภคทั่วไป
- กระแสไวรัล versus คุณภาพและความปลอดภัยจริง
- การอ้างสิทธิ์ระดับโลก versus ข้อเท็จจริงทางธุรกิจ

### Sarcasm patterns
- การยกย่องเกินจริงเพื่อเสียดสีการอ้างอันดับโลก
- การเปรียบเทียบย้อนแย้งโดยชมคู่แข่งไปพร้อมกัน
- การตั้งคำถามเชิงประชดเกี่ยวกับสถานะพนักงาน versus เจ้าของ
- การเสนอแนะเชิงล้อเลียนให้ย้ายฐานการผลิตไปยังประเทศต้นตำรับ
- การใช้คำขำขันลดทอนความน่าเชื่อถือของการสื่อสารแบรนด์

### Recommended actions
- ออกแถลงการณ์ชี้แจงโครงสร้างบริษัทและบทบาทผู้บริหารอย่างโปร่งใส
- ตรวจสอบกระบวนการผลิตและตอบโต้กรณีเศษแก้วทันทีเพื่อฟื้นฟูความเชื่อมั่น
- ทบทวนกลยุทธ์ราคาหรือเพิ่มคุณค่าที่จับต้องได้ให้สอดคล้องกับจุดขาย
- ฝึกอบรมทีมสื่อสารและพนักงานหน้าร้านเรื่องการจัดการวิกฤตและน้ำเสียงที่เหมาะสม
- ติดตามและแก้ไขข่าวลือโครงสร้างหุ้นอย่างรวดเร็วเพื่อป้องกันความเสียหายระยะยาว

### Caveats
- ข้อมูลมาจากการจัดประเภทโดยโมเดล LLM จำนวน 219 รายการ ซึ่งอาจมีความคลาดเคลื่อนบ้าง
- ตัวอย่างความคิดเห็นเป็นชุดย่อยและไม่ครอบคลุมทุกแพลตฟอร์ม
- สัดส่วนเชิงลบสูงอาจได้รับอิทธิพลจากเพจข่าวที่มีอัตราการมีส่วนร่วมสูง
- การตรวจจับภาษาประชดอาจพลาดบริบทหรือระดับความรุนแรงที่แท้จริง
- ผลการวิเคราะห์สะท้อนช่วงเวลาเฉพาะและอาจเปลี่ยนแปลงตามพัฒนาการของกระแส
