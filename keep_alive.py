from flask import Flask, jsonify, request
from threading import Thread
import logging
import time
import datetime
import os
import random
import requests
import socket
import sys

# ضبط مستوى التسجيل لتجنب السجلات الزائدة
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# تهيئة تطبيق Flask للاستمرار في الحياة
keep_alive_app = Flask(__name__)

# احصل على رابط Replit الخاص بك ديناميكيًا
def get_replit_url():
    """الحصول على رابط Replit بشكل ديناميكي"""
    try:
        # محاولة الحصول على الدومين المخصص أولاً (إذا تم تكوينه)
        from custom_domain_config import CUSTOM_DOMAIN
        if CUSTOM_DOMAIN:
            return f"https://{CUSTOM_DOMAIN}/"
    except (ImportError, AttributeError):
        pass
    
    try:
        # هذا الملف متاح فقط عند النشر على Replit
        repl_slug = os.environ.get('REPL_SLUG', 'repl')
        with open('/etc/replit/cluster-url', 'r') as f:
            cluster_url = f.read().strip()
        return f"https://{repl_slug}.{cluster_url}/"
    except Exception as e:
        # استخدام رابط احتياطي في حالة الفشل
        backup_url = "https://f5fb8356-b420-4e32-b2b6-05ac9d1a1c71.id.repl.co/"
        logger.warning(f"لم نتمكن من الحصول على رابط Replit ({e})، جاري استخدام الرابط الاحتياطي: {backup_url}")
        return backup_url

# المتغيرات العالمية لتتبع الحالة
start_time = time.time()
last_ping_time = time.time()
last_activity_time = time.time()
ping_count = 0
external_ping_count = 0
status_checks = []  # سجل آخر 10 عمليات تحقق

# حفظ آخر 10 محاولات اتصال
def log_status_check(source, status, details=None):
    global status_checks
    status_checks.append({
        "time": datetime.datetime.now().strftime('%H:%M:%S'),
        "source": source,
        "status": status,
        "details": details
    })
    if len(status_checks) > 10:
        status_checks = status_checks[-10:]

@keep_alive_app.route('/')
def home():
    """صفحة بسيطة لتأكيد أن الخادم يعمل مع معلومات تفصيلية"""
    global ping_count
    ping_count += 1
    log_status_check("web_visit", "success", request.remote_addr)
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_uptime = time.time() - start_time
    last_activity = time.time() - last_activity_time
    
    uptime_text = f"{int(total_uptime // 3600)} ساعات, {int((total_uptime % 3600) // 60)} دقائق, {int(total_uptime % 60)} ثواني"
    last_activity_text = f"{int(last_activity // 60)} دقائق, {int(last_activity % 60)} ثواني"
    
    # الحصول على معلومات النظام
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
    except:
        hostname = "غير متاح"
        ip_address = "غير متاح"
    
    # آخر 10 عمليات تحقق من الحالة
    status_log_html = """
    <div class="card">
        <h3>سجل آخر عمليات التحقق</h3>
        <table style="width: 100%; text-align: right;">
            <tr>
                <th>الوقت</th>
                <th>المصدر</th>
                <th>الحالة</th>
                <th>التفاصيل</th>
            </tr>
    """
    
    for check in reversed(status_checks):
        status_class = "success" if check["status"] == "success" else "error"
        status_log_html += f"""
            <tr>
                <td>{check["time"]}</td>
                <td>{check["source"]}</td>
                <td class="{status_class}">{check["status"]}</td>
                <td>{check.get("details", "")}</td>
            </tr>
        """
    
    status_log_html += """
        </table>
    </div>
    """
    
    return f"""
    <html>
    <head>
        <title>نظام إشارات التداول - لوحة الحالة</title>
        <meta http-equiv="refresh" content="60">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                text-align: center; 
                margin: 0; 
                padding: 20px;
                direction: rtl; 
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            .status {{ 
                padding: 20px; 
                background-color: #d4edda; 
                border-radius: 10px; 
                margin: 20px 0; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .card {{ 
                background-color: #fff; 
                padding: 15px 20px; 
                border-radius: 10px; 
                margin: 15px 0; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: right;
            }}
            h1, h2, h3 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; }}
            table, th, td {{ border: 1px solid #ddd; padding: 8px; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .warning {{ color: orange; }}
            .footer {{ 
                margin-top: 30px; 
                font-size: 0.8em; 
                color: #777; 
            }}
            code {{
                background: #f0f0f0;
                padding: 2px 6px;
                border-radius: 3px;
            }}
            a {{ color: #0066cc; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                body {{ padding: 10px; }}
                .card {{ padding: 10px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>نظام إشارات التداول</h1>
            
            <div class="status">
                <h2>✅ البوت نشط ويعمل!</h2>
                <p>حساب Replit المرقى مفعل ✅</p>
            </div>
            
            <div class="card">
                <h3>معلومات النظام</h3>
                <p><strong>الوقت الحالي:</strong> {current_time}</p>
                <p><strong>مدة التشغيل:</strong> {uptime_text}</p>
                <p><strong>آخر نشاط:</strong> منذ {last_activity_text}</p>
                <p><strong>اسم المضيف:</strong> {hostname}</p>
                <p><strong>عنوان IP:</strong> {ip_address}</p>
            </div>
            
            <div class="card">
                <h3>إحصائيات الاتصال</h3>
                <p><strong>عدد مرات التحقق من الواجهة:</strong> {ping_count}</p>
                <p><strong>عدد الاتصالات الخارجية:</strong> {external_ping_count}</p>
            </div>
            
            {status_log_html}
            
            <div class="footer">
                <p>هذه الصفحة تحدث تلقائيًا كل دقيقة. آخر تحديث: {current_time}</p>
                <p>© {datetime.datetime.now().year} نظام إشارات التداول - جميع الحقوق محفوظة</p>
            </div>
        </div>
        
        <script>
            // إعادة تحميل الصفحة كل دقيقة
            setTimeout(function() {{
                location.reload();
            }}, 60000);
        </script>
    </body>
    </html>
    """

@keep_alive_app.route('/ping')
def ping():
    """مسار مخصص لمراقبة الحالة (عام)"""
    global last_ping_time, external_ping_count, last_activity_time
    last_ping_time = time.time()
    last_activity_time = time.time()
    external_ping_count += 1
    
    # تسجيل معلومات عن مصدر الاتصال
    source_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    log_status_check("ping_request", "success", f"{source_ip}")
    
    # إجراء نشاط بسيط لمنع الخمول
    perform_active_task()
    
    return jsonify({
        "status": "ok",
        "message": "Bot is alive and running",
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "uptime_seconds": int(time.time() - start_time)
    })

def perform_active_task():
    """
    تنفيذ مهمة نشطة بسيطة لمنع وضع الخمول
    """
    # إنشاء ملف مؤقت
    temp_file = f"temp_{int(time.time())}.txt"
    try:
        # كتابة بيانات عشوائية إلى الملف
        with open(temp_file, "w") as f:
            f.write(f"Keep alive task at {datetime.datetime.now()}\n")
            f.write(f"Random data: {random.random()}\n")
        
        # قراءة الملف
        with open(temp_file, "r") as f:
            content = f.read()
        
        # حذف الملف
        os.remove(temp_file)
        
        # تنفيذ بعض العمليات الحسابية
        result = 0
        for i in range(100):
            result += i * random.random()
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Error in active task: {e}")
        return {"success": False}

# دالة للاتصال الذاتي بالتطبيق بشكل دوري
def self_ping():
    """دالة لإجراء اتصال ذاتي بالتطبيق بشكل دوري"""
    # تمديد الانتظار الأولي (5-10 ثواني) لتجنب التداخل مع بدء النظام
    time.sleep(random.uniform(5, 10))
    
    while True:
        try:
            url = get_replit_url()
            ping_url = f"{url}ping?ts={int(time.time())}&r={random.random()}&source=internal"
            
            headers = {
                'User-Agent': 'InternalPingService/1.0',
                'Cache-Control': 'no-cache'
            }
            
            response = requests.get(ping_url, headers=headers, timeout=15)
            if response.status_code == 200:
                logger.info(f"Self-ping successful: {response.status_code}")
            else:
                logger.warning(f"Self-ping received non-200 response: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Self-ping failed: {e}")
        
        # انتظار 5 دقائق قبل الاتصال التالي - فترة طويلة لأن الحساب مرقى
        time.sleep(300 + random.uniform(-30, 30))

def run():
    """تشغيل الخادم على المنفذ 8080"""
    keep_alive_app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    """تشغيل خادم البقاء نشطًا في خيط منفصل"""
    # خيط لتشغيل خادم Flask للبقاء نشطًا
    server_thread = Thread(target=run, name="keep_alive_server")
    server_thread.daemon = True
    server_thread.start()
    
    # خيط للاتصال الذاتي
    ping_thread = Thread(target=self_ping, name="self_ping")
    ping_thread.daemon = True
    ping_thread.start()
    
    logger.info("تم بدء نظام البقاء نشطًا بنجاح")