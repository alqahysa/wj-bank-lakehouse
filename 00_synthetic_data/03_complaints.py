"""Generate customer complaints and feedback in Arabic and English -> data/complaints.csv.

Declined transactions are far more likely to trigger a complaint than approved ones.
The text carries no labels: sentiment and issue type are left for the LLM to find in Databricks.
"""
import os
import random
from datetime import datetime, timedelta

import pandas as pd

from common import BRANCHES, DATA_DIR, fmt_ts

BRANCH_NAME = {b[0]: b[1] for b in BRANCHES}

# issue -> (Arabic templates, English templates)
TEMPLATES = {
    "card_declined": (
        ["تم رفض بطاقتي في {merchant} رغم وجود رصيد كافٍ في حسابي. موقف محرج جداً.",
         "رُفضت عملية بمبلغ {amount} ريال بدون أي سبب واضح، أرجو حل المشكلة بسرعة.",
         "بطاقة مدى لا تعمل في {merchant} للمرة الثانية هذا الأسبوع."],
        ["My card was declined at {merchant} even though I had enough balance. Very embarrassing.",
         "A payment of {amount} SAR was declined for no clear reason. Please fix this quickly.",
         "My mada card failed at {merchant} for the second time this week."],
    ),
    "fees_charges": (
        ["تم خصم رسوم غير مفهومة من حسابي بعد عملية الشراء، أريد توضيحاً واسترداد المبلغ.",
         "رسوم البطاقة الائتمانية مرتفعة جداً مقارنة بما تم إبلاغي به عند الإصدار.",
         "تم احتساب رسوم سحب نقدي على عملية شراء عادية بمبلغ {amount} ريال."],
        ["I was charged a fee I don't understand after my purchase. I want an explanation and a refund.",
         "The credit card fees are much higher than what I was told when the card was issued.",
         "I was charged a cash-withdrawal fee on a normal purchase of {amount} SAR."],
    ),
    "digital_banking": (
        ["التطبيق يتوقف كل مرة أحاول فيها تأكيد العملية، ورمز التحقق لا يصل.",
         "لا أستطيع تسجيل الدخول إلى التطبيق منذ يومين.",
         "خدمة Apple Pay تعطلت بعد آخر تحديث للتطبيق."],
        ["The app crashes every time I try to confirm a payment, and the OTP never arrives.",
         "I haven't been able to log in to the mobile app for two days.",
         "Apple Pay stopped working after the latest app update."],
    ),
    "branch_service": (
        ["انتظرت أكثر من ساعة في {branch} ولم يتم خدمتي.",
         "موظف الفرع كان غير متعاون ولم يجب على أسئلتي.",
         "الصراف الآلي في الفرع خارج الخدمة منذ أسبوع."],
        ["I waited more than an hour at {branch} and nobody served me.",
         "The branch staff were unhelpful and didn't answer my questions.",
         "The ATM at the branch has been out of service for a week."],
    ),
    "fraud_dispute": (
        ["ظهرت عملية بمبلغ {amount} ريال لا أعرفها في كشف حسابي، أرجو إيقاف البطاقة فوراً.",
         "تم خصم مبلغ من بطاقتي لعملية لم أقم بها في {merchant}، أريد فتح اعتراض."],
        ["There is a transaction of {amount} SAR on my statement that I don't recognise. Please block the card now.",
         "My card was charged at {merchant} for a purchase I never made. I want to raise a dispute."],
    ),
    "neutral": (
        ["تم حل المشكلة لكن استغرق الأمر وقتاً أطول من المتوقع.",
         "أرغب في معرفة موعد استحقاق القسط القادم لعملية التقسيط."],
        ["The issue was resolved, but it took longer than expected.",
         "I'd like to know when my next instalment is due."],
    ),
    "positive": (
        ["شكراً لفريق خدمة العملاء، تم حل مشكلتي بسرعة واحترافية.",
         "تجربة ممتازة مع خدمة التقسيط، العملية كانت سهلة وسريعة.",
         "موظفو {branch} كانوا متعاونين جداً، شكراً لكم."],
        ["Thank you to the customer care team, my issue was solved quickly and professionally.",
         "Great experience with the instalment option, it was quick and easy.",
         "The staff at {branch} were very helpful, thank you."],
    ),
}
SCORE_BY_ISSUE = {"card_declined": (1, 2), "fees_charges": (1, 3), "digital_banking": (1, 3),
                  "branch_service": (1, 2), "fraud_dispute": (1, 2), "neutral": (3, 3), "positive": (4, 5)}
CHANNELS = ["MOBILE_APP", "CALL_CENTER", "BRANCH", "EMAIL"]


def pick_issue(txn, rng):
    if txn["status"] == "DECLINED":
        return "card_declined" if rng.random() < 0.8 else "fraud_dispute"
    return rng.choices(
        ["fees_charges", "digital_banking", "branch_service", "fraud_dispute", "neutral", "positive"],
        weights=[0.2, 0.2, 0.12, 0.08, 0.15, 0.25])[0]


def generate_complaints(approved_rate=0.01, declined_rate=0.30, seed=11):
    rng = random.Random(seed)
    txns = pd.read_csv(os.path.join(DATA_DIR, "historical_transactions.csv"), dtype=str)
    now = datetime.now()
    rows = []
    for txn in txns.to_dict("records"):
        rate = declined_rate if txn["status"] == "DECLINED" else approved_rate
        if rng.random() > rate:
            continue
        issue = pick_issue(txn, rng)
        arabic = rng.random() < 0.6
        options = TEMPLATES[issue][0 if arabic else 1]
        text = rng.choice(options)
        # about 1 in 5 complaints mention a second issue
        if issue not in ("positive", "neutral") and rng.random() < 0.2:
            second = rng.choice(["fees_charges", "digital_banking", "branch_service"])
            text += " " + rng.choice(TEMPLATES[second][0 if arabic else 1])
        text = text.format(merchant=txn["merchant_name"], amount=txn["amount_sar"],
                           branch=BRANCH_NAME[txn["branch_id"]])
        ts = datetime.fromisoformat(txn["txn_timestamp"]) + timedelta(hours=rng.randint(1, 120))
        lo, hi = SCORE_BY_ISSUE[issue]
        rows.append({
            "complaint_id": f"CMP-{len(rows) + 1:06d}",
            "txn_id": txn["txn_id"],
            "customer_id": txn["customer_id"],
            "branch_id": txn["branch_id"],
            "channel": rng.choice(CHANNELS),
            "complaint_text": text,
            "satisfaction_score": rng.randint(lo, hi),
            "complaint_timestamp": fmt_ts(min(ts, now)),
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "complaints.csv"), index=False, encoding="utf-8")
    print(f"complaints: {len(df)} rows")


if __name__ == "__main__":
    generate_complaints()