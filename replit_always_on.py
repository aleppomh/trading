"""
نظام شامل للحفاظ على استمرارية العمل على منصة Replit
هذا النظام مصمم خصيصًا للتغلب على الخمول التلقائي في Replit عند إغلاق الواجهة

يستخدم استراتيجيات متعددة منها:
1. خادم Flask منفصل لتلقي الاتصالات
2. تحفيز حلقات النشاط بانتظام
3. إعادة تشغيل نظام الإشارات عند اكتشاف خمول
4. استدعاء أنظمة المراقبة الخارجية
"""

import os
import sys
import time
import logging
import threading
import random
import socket
import datetime
import requests
import atexit
import json
from urllib.parse import urljoin
from flask import Flask, jsonify, request
import signal

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("replit_always_on")

# تكوين النظام
PING_INTERVAL = 30  # ثانية
SYSTEM_CHECK_INTERVAL = 120  # ثانية
SERVER_PORT = 8080  # منفذ خادم الاستمرارية
INACTIVITY_THRESHOLD = 300  # 5 دقائق

# المتغيرات العامة
_active = False
_last_activity_time = time.time()
_ping_count = 0
_error_count = 0
_uptime_start = time.time()
_external_urls = [
    "https://www.google.com",
    "https://www.bing.com",
    "https://www.yahoo.com",
    "https://www.wikipedia.org"
]

# إنشاء تطبيق Flask للبقاء نشطًا
app = Flask(__name__)

# ضبط مستوى السجلات لتجنب السجلات الزائدة من Flask
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.WARNING)

# وظائف مساعدة
def get_system_info():
    """الحصول على معلومات النظام"""
    system_info = {
        "hostname": socket.gethostname(),
        "current_time": str(datetime.datetime.now()),
        "uptime_seconds": time.time() - _uptime_start,
        "active": _active,
        "ping_count": _ping_count,
        "last_activity": str(datetime.datetime.fromtimestamp(_last_activity_time)),
        "inactivity_seconds": time.time() - _last_activity_time,
    }
    
    try:
        import psutil
        system_info.update({
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        })
    except ImportError:
        pass
    
    return system_info

def get_replit_url():
    """الحصول على رابط Replit الحالي"""
    try:
        # محاولة الحصول على الدومين المخصص أولاً
        try:
            from custom_domain_config import CUSTOM_DOMAIN
            if CUSTOM_DOMAIN and isinstance(CUSTOM_DOMAIN, str) and len(CUSTOM_DOMAIN) > 5:
                logger.info(f"تم استخدام الدومين المخصص: {CUSTOM_DOMAIN}")
                return f"https://{CUSTOM_DOMAIN}"
        except (ImportError, Exception):
            pass  # تجاهل الخطأ واستمر
        
        # استخدام دومين Replit
        repl_slug = os.environ.get('REPL_SLUG')
        repl_owner = os.environ.get('REPL_OWNER')
        
        if repl_slug and repl_owner:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
        
        # استخدام دومين من ملف التكوين
        if os.path.exists('/etc/replit/cluster-url'):
            with open('/etc/replit/cluster-url', 'r') as f:
                cluster_url = f.read().strip()
                repl_slug = os.environ.get('REPL_SLUG', 'repl')
                return f"https://{repl_slug}.{cluster_url}"
    except Exception as e:
        logger.error(f"فشل في الحصول على رابط Replit: {e}")
    
    # استخدام الرابط الحالي إذا كان متاحًا
    current_url = request.url_root if request and request.url_root else None
    if current_url:
        return current_url
        
    # استخدام روابط احتياطية في حالة الفشل
    backup_urls = [
        "https://design-note-sync-lyvaquny.replit.app/",
        "https://f5fb8356-b420-4e32-b2b6-05ac9d1a1c71-00-3blbjrsd87z4d.janeway.replit.dev/",
        os.environ.get('REPLIT_DB_URL', '').split('//')[0] + '//'
    ]
    
    # اختيار رابط احتياطي عشوائي
    for url in backup_urls:
        if url and len(url) > 10:
            return url
    
    # رابط افتراضي نهائي
    return "https://replit.com/"

def perform_system_activity():
    """إجراء نشاط على النظام لإبقائه نشطًا"""
    global _last_activity_time
    
    try:
        # إنشاء ملف مؤقت
        temp_file = f"activity_{int(time.time())}.tmp"
        with open(temp_file, "w") as f:
            f.write(f"Activity at {datetime.datetime.now()}\n")
            f.write(f"Random data: {random.random()}\n")
            f.write(f"System info: {json.dumps(get_system_info())}\n")
        
        # قراءة الملف
        with open(temp_file, "r") as f:
            content = f.read()
        
        # حذف الملف
        os.remove(temp_file)
        
        # إجراء بعض العمليات الحسابية
        results = []
        for i in range(100):
            results.append(random.random() * i)
        avg = sum(results) / len(results)
        
        # نشاط الشبكة
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = "127.0.0.1"
        
        # تحديث وقت النشاط الأخير
        _last_activity_time = time.time()
        
        logger.debug(f"تم تنفيذ نشاط النظام: معدل={avg:.2f}, IP={ip_address}")
        return True
    except Exception as e:
        logger.error(f"فشل في تنفيذ نشاط النظام: {e}")
        return False

def ping_self_routes():
    """إجراء اتصال ذاتي بمسارات التطبيق الرئيسية"""
    global _ping_count, _error_count
    
    try:
        replit_url = get_replit_url()
        
        # قائمة المسارات للاتصال بها
        routes = [
            "",  # الصفحة الرئيسية
            "ping",  # مسار الفحص
            "signal_status",  # حالة الإشارات
        ]
        
        # اختيار مسار عشوائي
        route = random.choice(routes)
        url = urljoin(replit_url, route)
        
        # إضافة معلمات عشوائية
        params = {
            "ts": time.time(),
            "r": random.random(),
            "source": "self_ping"
        }
        
        # تكوين ترويسات HTTP
        headers = {
            "User-Agent": f"ReplicationAlwaysOn/{random.randint(1, 100)}",
            "X-Keep-Alive": "true",
            "Cache-Control": "no-cache, no-store"
        }
        
        # إجراء الاتصال
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            _ping_count += 1
            _error_count = 0
            logger.info(f"✅ نداء اتصال ناجح إلى {route or '/'}: {response.status_code}")
            return True
        else:
            _error_count += 1
            logger.warning(f"⚠️ فشل نداء الاتصال إلى {route or '/'}: {response.status_code}")
            return False
            
    except Exception as e:
        _error_count += 1
        logger.error(f"❌ خطأ في نداء الاتصال الذاتي: {e}")
        return False

def ping_external_sites():
    """الاتصال بمواقع خارجية للحفاظ على اتصال الإنترنت نشطًا"""
    try:
        # اختيار موقع عشوائي
        url = random.choice(_external_urls)
        
        # إجراء الاتصال
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 AlwaysOnSystem/1.0"},
            timeout=10
        )
        
        logger.debug(f"تم الاتصال بـ {url}: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"فشل الاتصال بالمواقع الخارجية: {e}")
        return False

def check_signal_system():
    """التحقق من حالة نظام الإشارات وإعادة تشغيله إذا لزم الأمر"""
    try:
        # استيراد مدير الإشارات
        import signal_manager
        
        # التحقق من حالة النظام
        if not signal_manager.check_signal_system_status():
            logger.warning("⚠️ نظام الإشارات غير نشط، جاري إعادة تشغيله...")
            signal_manager.restart_signal_system()
            logger.info("✅ تم إعادة تشغيل نظام الإشارات")
            
            # بدء توليد إشارة جديدة
            try:
                # استخدام وظيفة توليد الإشارة مباشرة
                from app import generate_new_signal
                with app.app_context():
                    generate_new_signal()
                logger.info("✅ تم طلب توليد إشارة جديدة")
            except Exception as e:
                logger.error(f"❌ فشل طلب توليد إشارة جديدة: {e}")
            
            return True
        else:
            # النظام نشط، التحقق من الإشارات
            try:
                # التحقق من الوقت المنقضي منذ آخر إشارة
                if signal_manager.is_time_to_generate_signal():
                    logger.info("🔄 حان وقت توليد إشارة جديدة...")
                    from app import generate_new_signal
                    with app.app_context():
                        generate_new_signal()
                    logger.info("✅ تم طلب توليد إشارة جديدة")
            except Exception as e:
                logger.error(f"❌ خطأ في التحقق من موعد الإشارة التالية: {e}")
            
            return True
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من نظام الإشارات: {e}")
        return False

# مسارات Flask
@app.route('/')
def home():
    """الصفحة الرئيسية لنظام الاستمرارية"""
    global _last_activity_time
    _last_activity_time = time.time()
    
    uptime_seconds = time.time() - _uptime_start
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(days)} أيام, {int(hours)} ساعات, {int(minutes)} دقائق, {int(seconds)} ثواني"
    
    return f"""
    <html>
    <head>
        <title>نظام الاستمرارية على Replit</title>
        <meta http-equiv="refresh" content="60">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                direction: rtl;
                text-align: center;
                background: #f0f0f0;
                padding: 20px;
                margin: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; }}
            .status {{ 
                padding: 15px; 
                background-color: #d4edda; 
                border-radius: 5px;
                margin: 20px 0;
                text-align: center;
            }}
            .status.error {{ background-color: #f8d7da; }}
            .info {{ 
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                margin: 15px 0;
                text-align: right;
            }}
            .info p {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>نظام الاستمرارية على Replit</h1>
            
            <div class="status">
                <h2>✅ النظام نشط</h2>
                <p>تم تصميم هذا النظام للحفاظ على استمرارية عمل البوت</p>
            </div>
            
            <div class="info">
                <h3>معلومات النظام</h3>
                <p><strong>الوقت الحالي:</strong> {datetime.datetime.now()}</p>
                <p><strong>مدة التشغيل:</strong> {uptime_str}</p>
                <p><strong>عدد الاتصالات:</strong> {_ping_count}</p>
                <p><strong>آخر نشاط:</strong> {datetime.datetime.fromtimestamp(_last_activity_time)}</p>
                <p><strong>حالة النظام:</strong> {"نشط" if _active else "غير نشط"}</p>
            </div>
            
            <p style="margin-top: 30px; font-size: 0.8em; color: #7f8c8d;">
                تحديث تلقائي كل دقيقة. آخر تحديث: {datetime.datetime.now()}
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    """مسار فحص الحالة"""
    global _last_activity_time
    _last_activity_time = time.time()
    
    # تنفيذ نشاط على النظام
    perform_system_activity()
    
    return jsonify({
        "status": "ok",
        "time": str(datetime.datetime.now()),
        "uptime_seconds": time.time() - _uptime_start,
        "active": _active
    })

@app.route('/status')
def status():
    """مسار لعرض معلومات حالة النظام"""
    return jsonify(get_system_info())

# خيوط العمل
def activity_thread():
    """خيط للحفاظ على نشاط النظام"""
    logger.info("🚀 بدء خيط النشاط")
    
    while _active:
        try:
            # التحقق من النشاط مؤخرًا
            inactivity_time = time.time() - _last_activity_time
            if inactivity_time > INACTIVITY_THRESHOLD:
                logger.warning(f"⚠️ النظام غير نشط منذ {inactivity_time:.1f} ثواني، تنفيذ نشاط للتنشيط...")
                perform_system_activity()
            
            # تنفيذ نشاط على النظام
            perform_system_activity()
            
            # الانتظار
            time.sleep(PING_INTERVAL)
        except Exception as e:
            logger.error(f"❌ خطأ في خيط النشاط: {e}")
            time.sleep(10)  # انتظار أقصر في حالة الخطأ

def ping_thread():
    """خيط للاتصالات المنتظمة"""
    logger.info("🚀 بدء خيط الاتصالات")
    
    while _active:
        try:
            # الاتصال بالمسارات الذاتية
            ping_self_routes()
            
            # الاتصال بالمواقع الخارجية (أحيانًا)
            if random.random() < 0.2:  # 20% من الوقت
                ping_external_sites()
            
            # الانتظار
            time.sleep(PING_INTERVAL + random.uniform(-5, 5))
        except Exception as e:
            logger.error(f"❌ خطأ في خيط الاتصالات: {e}")
            time.sleep(10)  # انتظار أقصر في حالة الخطأ

def system_check_thread():
    """خيط للتحقق من حالة النظام دوريًا"""
    logger.info("🚀 بدء خيط التحقق من النظام")
    
    while _active:
        try:
            # التحقق من نظام الإشارات
            check_signal_system()
            
            # الانتظار
            time.sleep(SYSTEM_CHECK_INTERVAL + random.uniform(-10, 10))
        except Exception as e:
            logger.error(f"❌ خطأ في خيط التحقق من النظام: {e}")
            time.sleep(30)  # انتظار أطول في حالة الخطأ

def run_server():
    """تشغيل خادم Flask"""
    try:
        app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)
    except Exception as e:
        logger.error(f"❌ فشل في بدء خادم Flask: {e}")

# وظائف التحكم العامة
def start():
    """بدء نظام الاستمرارية"""
    global _active, _uptime_start
    
    if _active:
        logger.warning("⚠️ نظام الاستمرارية يعمل بالفعل")
        return False
    
    logger.info("🚀 بدء نظام الاستمرارية على Replit")
    _active = True
    _uptime_start = time.time()
    
    # بدء خادم Flask
    server_thread = threading.Thread(target=run_server, name="ServerThread")
    server_thread.daemon = True
    server_thread.start()
    
    # بدء خيط النشاط
    activity_thread_instance = threading.Thread(target=activity_thread, name="ActivityThread")
    activity_thread_instance.daemon = True
    activity_thread_instance.start()
    
    # بدء خيط الاتصالات
    ping_thread_instance = threading.Thread(target=ping_thread, name="PingThread")
    ping_thread_instance.daemon = True
    ping_thread_instance.start()
    
    # بدء خيط التحقق من النظام
    system_thread = threading.Thread(target=system_check_thread, name="SystemCheckThread")
    system_thread.daemon = True
    system_thread.start()
    
    # التحقق من نظام الإشارات فورًا
    check_signal_system()
    
    logger.info("✅ تم بدء نظام الاستمرارية بنجاح")
    return True

def stop():
    """إيقاف نظام الاستمرارية"""
    global _active
    
    if not _active:
        logger.warning("⚠️ نظام الاستمرارية متوقف بالفعل")
        return False
    
    logger.info("🛑 إيقاف نظام الاستمرارية")
    _active = False
    
    # إعطاء مهلة للخيوط للتوقف
    time.sleep(1)
    
    logger.info("✅ تم إيقاف نظام الاستمرارية")
    return True

def get_status():
    """الحصول على حالة النظام"""
    return {
        "active": _active,
        "uptime_seconds": time.time() - _uptime_start,
        "ping_count": _ping_count,
        "error_count": _error_count,
        "last_activity_time": str(datetime.datetime.fromtimestamp(_last_activity_time)),
        "inactivity_seconds": time.time() - _last_activity_time,
    }

# التسجيل للتنظيف عند الإغلاق
def cleanup():
    """تنظيف الموارد عند الإغلاق"""
    if _active:
        stop()

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda sig, frame: cleanup())
signal.signal(signal.SIGINT, lambda sig, frame: cleanup())

# تشغيل نظام الاستمرارية تلقائيًا
if __name__ == "__main__":
    start()