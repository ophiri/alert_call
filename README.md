# 🚨 Alert Call - שירות התרעה טלפונית מפיקוד העורף

שירות שמאזין להתרעות פיקוד העורף בזמן אמת ומתקשר אליך לטלפון כשיש התרעה על ירי רקטות.

## 🏗️ איך זה עובד

1. **מאזין** - השירות בודק כל 2 שניות את ה-API של פיקוד העורף (real-time + history fallback)
2. **מזהה** - כשמזוהה התרעה חדשה, השירות מסנן לפי האזורים שהגדרת
3. **מתקשר** - מבצע שיחה טלפונית דרך Twilio
4. **משמיע** - כשעונים לשיחה, מושמעת הודעה קולית בעברית עם שם האזור

## 📋 דרישות מקדימות

### 1. חשבון Twilio
1. הירשם ב-[Twilio](https://www.twilio.com/)
2. קבל **Account SID** ו-**Auth Token** מ-[Console](https://console.twilio.com/)
3. קנה/קבל **מספר טלפון** עם יכולת שיחות יוצאות

### 2. Python 3.11+

## 🚀 התקנה

```bash
# 1. שכפול הפרויקט
git clone https://github.com/YOUR_USERNAME/alert_call.git
cd alert_call

# 2. יצירת סביבה וירטואלית
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. התקנת תלויות
pip install -r requirements.txt

# 4. הגדרת קובץ הגדרות
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/Mac
# ערוך את קובץ .env עם הפרטים שלך
```

## ⚙️ הגדרות

ערוך את קובץ `.env`:

| משתנה | תיאור | דוגמה |
|--------|--------|--------|
| `TWILIO_ACCOUNT_SID` | Account SID מ-Twilio | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Auth Token מ-Twilio | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_PHONE_NUMBER` | מספר Twilio שלך | `+12345678900` |
| `MY_PHONE_NUMBER` | מספר הטלפון שלך | `+972501234567` |
| `MONITORED_AREAS` | אזורים לניטור (ריק = הכל) | `תל אביב,רמת גן` |
| `POLL_INTERVAL_SECONDS` | תדירות בדיקה (שניות) | `2` |
| `ALERT_COOLDOWN_SECONDS` | זמן מינימלי בין שיחות | `60` |

## ▶️ הפעלה

### הפעלה מקומית
```bash
python main.py
```

### בדיקת שיחה
```bash
python test_call.py
```

### פריסה ל-Azure (24/7)
> ⚠️ ה-API של פיקוד העורף נגיש רק מ-IP ישראלי. יש לפרוס באזור `israelcentral`.

```bash
# 1. התחבר ל-Azure
az login

# 2. ערוך את deploy-azure.ps1 עם הפרטים שלך

# 3. הרץ את סקריפט הפריסה
.\deploy-azure.ps1
```

## 🏗️ מבנה הפרויקט

```
alert_call/
├── main.py              # נקודת כניסה - הלולאה הראשית
├── oref_monitor.py      # מודול ניטור התרעות (real-time + history fallback)
├── phone_caller.py      # מודול שיחות טלפון (Twilio)
├── config.py            # הגדרות ומשתני סביבה
├── requirements.txt     # תלויות Python
├── Dockerfile           # בניית Docker image
├── deploy-azure.ps1     # סקריפט פריסה ל-Azure Container Instance
├── test_call.py         # בדיקת שיחה
├── show_alerts.py       # הצגת התרעות היום
├── .env.example         # תבנית להגדרות
├── .env                 # הגדרות אישיות (לא ב-git)
└── .gitignore
```

## 💰 עלויות

- **Twilio**: ~$0.014 לדקת שיחה + ~$1/חודש למספר טלפון
- **Azure Container Instance** (אופציונלי): ~$0.25 CPU + ~$0.003/GB/שעה ≈ כמה דולרים בחודש
- **סה"כ**: כמה דולרים בודדים בחודש עם שימוש רגיל

## ⚠️ הערות חשובות

- **IP ישראלי**: ה-API של פיקוד העורף חוסם גישה מ-IP שאינו ישראלי (403). אם אתה מריץ בענן, השתמש באזור `israelcentral`
- **BOM Response**: ה-API מחזיר BOM (Byte Order Mark) כשאין התרעות - השירות מטפל בזה
- **History Fallback**: בנוסף ל-real-time API, השירות בודק גם את ה-History API כל 30 שניות כגיבוי
- **אמינות**: השירות תלוי בזמינות ה-API של פיקוד העורף ובחיבור אינטרנט
- **לא תחליף**: שירות זה **אינו תחליף** לאפליקציית פיקוד העורף הרשמית!
