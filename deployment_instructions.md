# تعليمات تنصيب مشروع Elite Trading Signals Pro

## المتطلبات الأساسية

1. خادم VPS أو استضافة تدعم:
   - Python 3.9+ 
   - PostgreSQL 13+
   - إمكانية تشغيل خدمات مستمرة
   - وصول SSH

## خطوات التنصيب

### 1. تجهيز الخادم

```bash
# تحديث حزم النظام
sudo apt update
sudo apt upgrade -y

# تثبيت المتطلبات الأساسية
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx supervisor git

# تثبيت مكتبات النظام المطلوبة
sudo apt install -y libpq-dev python3-dev build-essential libssl-dev libffi-dev
```

### 2. إعداد قاعدة البيانات PostgreSQL

```bash
# الدخول إلى PostgreSQL
sudo -u postgres psql

# إنشاء قاعدة البيانات والمستخدم (داخل psql)
CREATE DATABASE trading_signals_db;
CREATE USER trading_user WITH PASSWORD 'اختر_كلمة_مرور_قوية';
GRANT ALL PRIVILEGES ON DATABASE trading_signals_db TO trading_user;
ALTER ROLE trading_user SET client_encoding TO 'utf8';
ALTER ROLE trading_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE trading_user SET timezone TO 'UTC';
\q
```

### 3. تحضير ملفات المشروع

```bash
# إنشاء مجلد للمشروع
mkdir -p /var/www/trading_elite_pro
cd /var/www/trading_elite_pro

# استخراج ملفات المشروع
unzip /path/to/trading_elite_pro.zip -d .

# إنشاء بيئة Python افتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install --upgrade pip
pip install -r project_requirements.txt
pip install gunicorn
```

### 4. إعداد ملف البيئة

قم بإنشاء ملف `.env` في المجلد الرئيسي للمشروع باستخدام الأمر:

```bash
nano .env
```

ثم قم بإضافة المتغيرات التالية وتعديلها حسب إعداداتك:

```
# معلومات قاعدة البيانات
DATABASE_URL=postgresql://trading_user:كلمة_المرور@localhost:5432/trading_signals_db
PGUSER=trading_user
PGPASSWORD=كلمة_المرور
PGDATABASE=trading_signals_db
PGHOST=localhost
PGPORT=5432

# إعدادات التطبيق
SESSION_SECRET=قم_بتغيير_هذا_النص_إلى_نص_عشوائي_طويل
FLASK_ENV=production

# معلومات بوت تيليجرام (يمكن إضافتها لاحقاً)
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 5. تهيئة قاعدة البيانات

```bash
# بعد تنشيط البيئة الافتراضية (venv)
cd /var/www/trading_elite_pro
source venv/bin/activate

# تهيئة قاعدة البيانات باستخدام Flask-Migrate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. إعداد Supervisor لتشغيل التطبيق

قم بإنشاء ملف تكوين Supervisor:

```bash
sudo nano /etc/supervisor/conf.d/trading_elite_pro.conf
```

أضف المحتوى التالي:

```ini
[program:trading_elite_pro]
directory=/var/www/trading_elite_pro
command=/var/www/trading_elite_pro/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 120 main:app
autostart=true
autorestart=true
stderr_logfile=/var/log/trading_elite_pro/gunicorn.err.log
stdout_logfile=/var/log/trading_elite_pro/gunicorn.out.log
user=www-data
environment=PATH="/var/www/trading_elite_pro/venv/bin",PYTHONPATH="/var/www/trading_elite_pro"

[program:trading_elite_pro_bot]
directory=/var/www/trading_elite_pro
command=/var/www/trading_elite_pro/venv/bin/python bot/telegram_client.py
autostart=true
autorestart=true
stderr_logfile=/var/log/trading_elite_pro/telegram_bot.err.log
stdout_logfile=/var/log/trading_elite_pro/telegram_bot.out.log
user=www-data
environment=PATH="/var/www/trading_elite_pro/venv/bin",PYTHONPATH="/var/www/trading_elite_pro"

[program:trading_elite_pro_always_on]
directory=/var/www/trading_elite_pro
command=/var/www/trading_elite_pro/venv/bin/python always_on.py
autostart=true
autorestart=true
stderr_logfile=/var/log/trading_elite_pro/always_on.err.log
stdout_logfile=/var/log/trading_elite_pro/always_on.out.log
user=www-data
environment=PATH="/var/www/trading_elite_pro/venv/bin",PYTHONPATH="/var/www/trading_elite_pro"
```

إنشاء مجلد السجلات وتطبيق التغييرات:

```bash
sudo mkdir -p /var/log/trading_elite_pro
sudo chown -R www-data:www-data /var/log/trading_elite_pro
sudo supervisorctl reread
sudo supervisorctl update
```

### 7. إعداد Nginx كبروكسي عكسي

```bash
sudo nano /etc/nginx/sites-available/trading_elite_pro
```

أضف المحتوى التالي (قم بتعديل اسم الدومين):

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/trading_elite_pro/static;
        expires 30d;
    }
}
```

تفعيل الموقع وإعادة تشغيل Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/trading_elite_pro /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 8. إعداد HTTPS (اختياري ولكن موصى به)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 9. التحقق من الخدمات

```bash
# التحقق من حالة التطبيق
sudo supervisorctl status trading_elite_pro
sudo supervisorctl status trading_elite_pro_bot
sudo supervisorctl status trading_elite_pro_always_on

# عرض سجلات التطبيق
sudo tail -f /var/log/trading_elite_pro/gunicorn.out.log
sudo tail -f /var/log/trading_elite_pro/telegram_bot.out.log
```

## تحديث المشروع في المستقبل

```bash
# الانتقال إلى مجلد المشروع
cd /var/www/trading_elite_pro

# استخراج ملفات التحديث (بعد تحميلها)
unzip /path/to/trading_elite_pro_update.zip -d temp_update
cp -r temp_update/* .
rm -rf temp_update

# تنشيط البيئة الافتراضية
source venv/bin/activate

# تحديث المتطلبات
pip install -r project_requirements.txt

# تحديث قاعدة البيانات
flask db migrate -m "Update migration"
flask db upgrade

# إعادة تشغيل الخدمات
sudo supervisorctl restart trading_elite_pro
sudo supervisorctl restart trading_elite_pro_bot
sudo supervisorctl restart trading_elite_pro_always_on
```

## ملاحظات هامة

1. احرص على تغيير كلمات المرور وتوكنات API إلى قيم آمنة وفريدة.
2. تأكد من ضبط إعدادات الجدران النارية للسماح بالاتصال على المنافذ 80 و 443.
3. اعمل نسخ احتياطي منتظم لقاعدة البيانات.
4. تأكد من تحديث النظام بشكل دوري للحصول على أحدث تصحيحات الأمان.

## استكشاف الأخطاء وإصلاحها

### مشكلات قاعدة البيانات
- تحقق من اتصال قاعدة البيانات: `psql -U trading_user -h localhost -d trading_signals_db`
- تأكد من صحة بيانات الاتصال في ملف `.env`

### مشكلات بوت تيليجرام
- تحقق من صحة توكن البوت في ملف `.env`
- تأكد من تشغيل خدمة البوت: `sudo supervisorctl status trading_elite_pro_bot`
- راجع سجلات الأخطاء: `sudo tail -f /var/log/trading_elite_pro/telegram_bot.err.log`

### مشكلات تطبيق الويب
- تحقق من تكوين Nginx: `sudo nginx -t`
- تأكد من أن تطبيق Gunicorn يعمل: `sudo supervisorctl status trading_elite_pro`
- راجع سجلات الأخطاء: `sudo tail -f /var/log/trading_elite_pro/gunicorn.err.log`