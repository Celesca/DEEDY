# บันทึกผลการทดลอง (Experiment Logs)

ไฟล์นี้ใช้บันทึกการตั้งค่า (Config Snapshot) และผลลัพธ์ของแต่ละรอบการจำลอง เพื่อป้องกันข้อมูลสูญหายและรับรองความสามารถในการสร้างผลลัพธ์ซ้ำ (Reproducibility) ตามข้อกำหนดใน Phase 7.4 และ 7.6

## รูปแบบการบันทึก
- **Run ID**: รหัสการทดลอง
- **Date**: วันที่ทดลอง
- **Model**: รุ่น LLM ที่ใช้
- **Seed**: หมายเลข seed
- **Population**: จำนวน Agent
- **Events/Scenario**: เหตุการณ์ที่ใช้
- **Result Summary**: สรุปผลลัพธ์

---

### [ตัวอย่าง] Run ID: SIM-20260808-01
- **Date**: 2026-08-08
- **Model**: qwen2.5-72b-instruct (via OpenRouter)
- **Seed**: 42
- **Population**: 200 (Thai Society Distribution)
- **Scenario**: การเพิ่มค่าเล่าเรียนในมหาวิทยาลัย (Ice Cream case baseline)
- **Result Summary**: ระบบรันสำเร็จ เห็นความแตกต่างระหว่างชั้น private และ public อย่างชัดเจน (Preference Falsification Gap) โดย Agent ที่เป็นผู้ใหญ่จะเลือกเงียบหรือเลี่ยงไปบ่นใน LINE มากกว่าการโพสต์สาธารณะ
