# محور – الشيفرة المصدرية

مجلد التنفيذ لمشروع «محور» وفق تصميم الفصل الرابع (مسودة غير معتمدة بعد).

| المجلد | المحتوى | المكون |
|---|---|---|
| `frontend/` | واجهة React + TypeScript (Vite)، عربية من اليمين إلى اليسار | CMP-01 |
| `backend/app/` | خدمة FastAPI: `routers` و`services` و`models` و`schemas` | CMP-02 إلى CMP-07 |
| `backend/tests/` | اختبارات pytest | — |
| `database/` | `Schema_Script.sql` و`Queries.sql` وبيانات الاختبار الاصطناعية | CMP-07 |

## المتطلبات على الجهاز (Windows)

- Python 3.11 أو أحدث (عند التثبيت فعّل خيار «Add python.exe to PATH»)
- Node.js 20 أو أحدث (يشمل npm)
- PostgreSQL 15 أو أحدث (يشمل الأداة psql وpgAdmin)
- Git
- VS Code، وعند فتح المجلد اقبل تثبيت الإضافات المقترحة

## خطوات الإعداد لأول مرة

افتح الملف `mahwar.code-workspace` بالنقر عليه مرتين (أو من VS Code: **File ← Open Workspace from File**). يحتوي هذا الملف على إعدادات VS Code والإضافات المقترحة وأوامر التشغيل والتصحيح. ثم افتح الطرفية (Terminal) ونفّذ الآتي.

### 1. قاعدة البيانات

```powershell
psql -U postgres
```

داخل psql:

```sql
CREATE USER mahwar WITH PASSWORD 'change_me';
CREATE DATABASE mahwar OWNER mahwar;
\q
```

ثم أنشئ الجداول العشرين:

```powershell
psql -U mahwar -d mahwar -f database/Schema_Script.sql
```

### 2. الخدمة الخلفية

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

عدّل كلمة المرور في `backend/.env` لتطابق ما أنشأته في الخطوة 1، وضع قيمة عشوائية طويلة في `JWT_SECRET`.

### 3. الواجهة

```powershell
cd frontend
npm install
```

## التشغيل اليومي

من قائمة VS Code: **Terminal ← Run Task** ثم اختر **Run all (backend + frontend)**، أو شغّل كل جزء منفردًا:

| المهمة | الأمر |
|---|---|
| الخدمة الخلفية | `cd backend` ثم `.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` |
| الواجهة | `cd frontend` ثم `npm run dev` |
| الاختبارات | `cd backend` ثم `.\.venv\Scripts\python -m pytest` |

افتح المتصفح على `http://localhost:5173`. تعرض الصفحة حالة الاتصال بالخدمة الخلفية وقاعدة البيانات، فإن ظهرت الحالتان «متصل» فالبيئة جاهزة.
وثائق الواجهة البرمجية التي يولدها FastAPI تلقائيًا على `http://localhost:8000/docs`.

للتصحيح (Debug) اختر **Backend: FastAPI (uvicorn)** من لوحة Run and Debug.

## Git

```powershell
git init
git add .
git commit -m "Project skeleton"
```

الملفان `backend/.env` و`node_modules` مستبعدان من Git عبر `.gitignore`.

## ترتيب التنفيذ (الإصدارات)

| الإصدار | المحتوى | المتطلبات |
|---|---|---|
| 1 | المستخدمون والأدوار، المشروعات والمهام وخط الأساس | FR-01، FR-02 |
| 2 | لقطات التقدم، الاعتماديات، الموارد | FR-03، FR-04، FR-05 |
| 3 | لوحة المتابعة | FR-06 |
| 4 | مؤشر الخطر وتحليل الأثر | FR-07، FR-08 |
| 5 | المحاكاة والمقارنة والملخص | FR-09، FR-10، FR-11 |

## قواعد العمل على المستودع

| البند | القاعدة |
|---|---|
| الفروع | `main` للنسخ المستقرة فقط. يعمل كل طالب على فرعه: `salama` و`moaad`، ثم يدمج في `main` عبر Pull Request بعد نجاح الاختبارات. |
| انتظام الرفع | Push مرتين إلى ثلاث مرات أسبوعيًا على الأقل، ولا يُرفع الكود دفعة واحدة في نهاية الفصل. |
| رسائل Commit | رسالة واضحة تبدأ بنوع التغيير: `feat:` لميزة، `fix:` لخطأ، `test:` لاختبار، `docs:` لتوثيق. مثال: `feat: add login endpoint (API-01)`. |
| الأمان | لا تُرفع كلمات المرور أو المفاتيح أبدًا؛ تبقى في `backend/.env` المستبعد عبر `.gitignore`. |
| المساهمة الفردية | يرفع كل طالب من حسابه الخاص حتى تظهر مساهمته في Contributors Insights. |

خطوات العمل اليومية لكل طالب:

```powershell
git checkout salama          # أو moaad
git pull origin main         # جلب آخر نسخة مستقرة
# ... التعديل ...
git add .
git commit -m "feat: ..."
git push origin salama
```
