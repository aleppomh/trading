"""
نظام متكامل للحفاظ على استمرارية التطبيق على Replit
هذا النظام يحل مشكلة الخمول نهائيًا عند إغلاق واجهة Replit

المميزات:
- خادم HTTP منفصل على منفذ مختلف
- مسارات خاصة للتأكد من حالة النظام
- آلية الحفاظ على النشاط المستمر
- تكامل مع خدمات المراقبة الخارجية
"""

import os
import time
import logging
import threading
import random
import socket
import datetime
import requests
import signal
import atexit
import json
import subprocess
from flask import Flask, jsonify, request, render_template_string
from urllib.parse import urljoin

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تكوين النظام
KEEP_ALIVE_PORT = 8080  # منفذ خادم الاستمرارية
PING_INTERVAL = 30      # فاصل زمني للاتصال (ثانية)
CHECK_INTERVAL = 60     # فاصل زمني للتحقق من حالة النظام (ثانية)
RESTART_MINUTES = 60    # إعادة تشغيل النظام بشكل دوري كل 60 دقيقة

# المتغيرات العالمية
_active = False
_started_at = time.time()
_last_activity = time.time()
_ping_count = 0
_restart_count = 0
_error_count = 0
_uptime_monitor_urls = []  # روابط لخدمات المراقبة الخارجية

# إنشاء تطبيق Flask
app = Flask(__name__)

# ضبط مستوى التسجيل لتجنب السجلات الزائدة
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.WARNING)

# الوظائف المساعدة
def get_uptime():
    """الحصول على مدة تشغيل النظام بتنسيق مقروء"""
    uptime_seconds = time.time() - _started_at
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

def get_replit_url():
    """الحصول على رابط التطبيق على Replit"""
    try:
        # محاولة الحصول على الدومين المخصص
        try:
            from custom_domain_config import CUSTOM_DOMAIN
            if CUSTOM_DOMAIN:
                return f"https://{CUSTOM_DOMAIN}"
        except ImportError:
            pass
        
        # استخدام دومين Replit
        if os.environ.get('REPL_SLUG') and os.environ.get('REPL_OWNER'):
            return f"https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co"
        
        # استخدام رابط النشر
        if os.path.exists('/etc/replit/cluster-url'):
            with open('/etc/replit/cluster-url') as f:
                cluster_url = f.read().strip()
                repl_slug = os.environ.get('REPL_SLUG', 'repl')
                return f"https://{repl_slug}.{cluster_url}"
    except:
        pass
    
    # رابط افتراضي
    return "https://design-note-sync-lyvaquny.replit.app"

def perform_system_activity():
    """تنفيذ نشاط على النظام للحفاظ على نشاطه"""
    global _last_activity
    
    try:
        # إنشاء ملف مؤقت
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"keep_alive_{timestamp}_{random.randint(1000,9999)}.tmp"
        
        # كتابة بيانات عشوائية في الملف
        with open(temp_file, "w") as f:
            f.write(f"Keep alive at {datetime.datetime.now()}\n")
            f.write(f"Random: {random.random()}\n")
            f.write(f"Uptime: {get_uptime()}\n")
        
        # قراءة من الملف
        with open(temp_file, "r") as f:
            content = f.read()
            
        # حذف الملف
        try:
            os.remove(temp_file)
        except:
            pass
        
        # إجراء بعض العمليات الحسابية
        result = 0
        for i in range(100):
            result += random.random() * i
            
        # تحديث وقت النشاط الأخير
        _last_activity = time.time()
        
        return True
    except Exception as e:
        logger.error(f"خطأ في نشاط النظام: {e}")
        return False

def ping_main_app():
    """الاتصال بالتطبيق الرئيسي للتأكد من نشاطه"""
    global _ping_count
    
    try:
        # الحصول على رابط التطبيق
        app_url = get_replit_url()
        
        # تحديد المسارات للاتصال
        routes = [
            "ping",
            "signal_status",
            ""  # الصفحة الرئيسية
        ]
        
        # اختيار مسار عشوائي
        route = random.choice(routes)
        ping_url = urljoin(app_url, route)
        
        # إضافة معلمات للتغلب على التخزين المؤقت
        params = {
            "ts": time.time(),
            "r": random.random(),
            "from": "keep_alive"
        }
        
        # تكوين ترويسات الطلب
        headers = {
            "User-Agent": f"KeepAliveSystem/{random.randint(1,100)}",
            "Cache-Control": "no-cache, no-store",
            "Pragma": "no-cache"
        }
        
        # إرسال الطلب
        response = requests.get(
            ping_url,
            params=params,
            headers=headers,
            timeout=30  # زيادة المهلة
        )
        
        # التحقق من نجاح الاتصال
        if response.status_code == 200:
            _ping_count += 1
            logger.info(f"✅ اتصال ناجح بالتطبيق الرئيسي ({route}): {response.status_code}")
            return True
        else:
            logger.warning(f"⚠️ استجابة غير متوقعة من التطبيق: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في الاتصال بالتطبيق الرئيسي: {e}")
        return False

def ping_external_monitors():
    """الاتصال بخدمات المراقبة الخارجية"""
    for url in _uptime_monitor_urls:
        try:
            response = requests.get(
                url, 
                timeout=30,
                headers={"User-Agent": "ReplitAlwaysOn/1.0"}
            )
            logger.info(f"اتصال بخدمة المراقبة الخارجية: {url} ({response.status_code})")
        except Exception as e:
            logger.error(f"خطأ في الاتصال بخدمة المراقبة: {url} - {e}")

def check_signal_system():
    """التحقق من حالة نظام الإشارات وإعادة تشغيله إذا لزم الأمر"""
    try:
        # جلب حالة نظام الإشارات
        app_url = get_replit_url()
        status_url = urljoin(app_url, "signal_status")
        
        response = requests.get(
            status_url, 
            params={"ts": time.time()},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.warning(f"⚠️ استجابة غير متوقعة من نظام الإشارات: {response.status_code}")
            return False
            
        # تحليل الاستجابة
        try:
            status_data = response.json()
            return status_data.get("is_running", False)
        except:
            logger.error("❌ فشل في تحليل استجابة نظام الإشارات")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من نظام الإشارات: {e}")
        return False

def restart_application():
    """إعادة تشغيل التطبيق الرئيسي"""
    global _restart_count
    
    try:
        logger.warning("⚠️ جاري إعادة تشغيل التطبيق...")
        
        # الاتصال بالتطبيق الرئيسي لإعادة تشغيله
        app_url = get_replit_url()
        restart_url = urljoin(app_url, "restart_system")
        
        try:
            response = requests.get(
                restart_url,
                params={"key": "restart_signal_system", "ts": time.time()},
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info("✅ تم إرسال طلب إعادة التشغيل بنجاح")
                _restart_count += 1
                return True
            else:
                logger.warning(f"⚠️ استجابة غير متوقعة من طلب إعادة التشغيل: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ فشل في إرسال طلب إعادة التشغيل: {e}")
        
        # بديل: إعادة تشغيل من خلال مسارات أخرى
        try:
            signal_status_url = urljoin(app_url, "signal_status")
            response = requests.get(
                signal_status_url,
                params={"force_restart": "true", "ts": time.time()},
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info("✅ تم إرسال طلب إعادة التشغيل البديل بنجاح")
                _restart_count += 1
                return True
        except:
            pass
            
        return False
    except Exception as e:
        logger.error(f"❌ خطأ عام في إعادة تشغيل التطبيق: {e}")
        return False

# مسارات التطبيق
@app.route('/')
def index():
    """الصفحة الرئيسية لنظام الاستمرارية"""
    global _last_activity
    _last_activity = time.time()
    
    # جمع معلومات الحالة
    now = datetime.datetime.now()
    uptime = get_uptime()
    last_activity_ago = time.time() - _last_activity
    last_activity_text = f"{int(last_activity_ago // 60)} دقائق و {int(last_activity_ago % 60)} ثواني"
    
    # التحقق من حالة نظام الإشارات
    signal_status = "جاري التحقق..."
    try:
        if check_signal_system():
            signal_status = "✅ نشط"
        else:
            signal_status = "⚠️ غير نشط"
    except:
        signal_status = "❌ خطأ في التحقق"
    
    # قالب الصفحة
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>نظام الاستمرارية المتقدم</title>
        <meta http-equiv="refresh" content="60">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                direction: rtl;
                text-align: center;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1 { color: #333; margin-bottom: 30px; }
            .status {
                background-color: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .info {
                text-align: right;
                margin: 15px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
            .info p { margin: 5px 0; }
            .actions {
                margin: 20px 0;
            }
            button {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                margin: 0 5px;
            }
            button:hover { background-color: #0069d9; }
            .footer {
                margin-top: 30px;
                font-size: 0.8em;
                color: #777;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>نظام الاستمرارية المتقدم</h1>
            
            <div class="status">
                <h2>النظام يعمل</h2>
                <p>هذا النظام يعمل على الحفاظ على استمرارية التطبيق ومنع وضع الخمول</p>
            </div>
            
            <div class="info">
                <h3>معلومات النظام</h3>
                <p><strong>الوقت الحالي:</strong> {{ now }}</p>
                <p><strong>مدة التشغيل:</strong> {{ uptime }}</p>
                <p><strong>آخر نشاط:</strong> منذ {{ last_activity_text }}</p>
                <p><strong>عدد عمليات الاتصال:</strong> {{ ping_count }}</p>
                <p><strong>عدد عمليات إعادة التشغيل:</strong> {{ restart_count }}</p>
                <p><strong>حالة نظام الإشارات:</strong> {{ signal_status }}</p>
            </div>
            
            <div class="actions">
                <button onclick="location.href='/ping'">فحص الاتصال</button>
                <button onclick="location.href='/status'">معلومات مفصلة</button>
                <button onclick="location.href='/restart'">إعادة تشغيل النظام</button>
            </div>
            
            <div class="footer">
                <p>تم التحديث في: {{ now }} - يتم تحديث هذه الصفحة تلقائيًا كل دقيقة</p>
            </div>
        </div>
        
        <script>
            // إعادة تحميل الصفحة كل دقيقة
            setTimeout(function() {
                location.reload();
            }, 60000);
        </script>
    </body>
    </html>
    ''', now=now, uptime=uptime, last_activity_text=last_activity_text, 
        ping_count=_ping_count, restart_count=_restart_count, signal_status=signal_status)

@app.route('/ping')
def ping():
    """مسار للاتصال والتحقق من النشاط"""
    global _last_activity
    _last_activity = time.time()
    
    # تنفيذ نشاط على النظام
    perform_system_activity()
    
    # الاتصال بالتطبيق الرئيسي
    main_app_status = "غير متصل"
    try:
        if ping_main_app():
            main_app_status = "متصل"
    except:
        pass
    
    # إعداد الاستجابة
    response = {
        "status": "ok",
        "time": str(datetime.datetime.now()),
        "uptime": get_uptime(),
        "ping_count": _ping_count,
        "main_app": main_app_status,
        "active": _active
    }
    
    return jsonify(response)

@app.route('/status')
def status():
    """مسار للحصول على حالة النظام المفصلة"""
    global _last_activity
    _last_activity = time.time()
    
    # جمع معلومات النظام
    system_info = {
        "active": _active,
        "started_at": str(datetime.datetime.fromtimestamp(_started_at)),
        "uptime": get_uptime(),
        "uptime_seconds": time.time() - _started_at,
        "last_activity": str(datetime.datetime.fromtimestamp(_last_activity)),
        "inactivity_seconds": time.time() - _last_activity,
        "ping_count": _ping_count,
        "restart_count": _restart_count,
        "error_count": _error_count,
        "hostname": socket.gethostname(),
    }
    
    return jsonify(system_info)

@app.route('/restart')
def restart():
    """مسار لإعادة تشغيل النظام"""
    if restart_application():
        return jsonify({
            "status": "success",
            "message": "تم إرسال طلب إعادة التشغيل بنجاح",
            "time": str(datetime.datetime.now())
        })
    else:
        return jsonify({
            "status": "error",
            "message": "فشل في إعادة تشغيل النظام",
            "time": str(datetime.datetime.now())
        }), 500

# خيوط العمل
def activity_thread():
    """خيط للحفاظ على نشاط النظام"""
    logger.info("🚀 بدء خيط النشاط")
    
    while _active:
        try:
            # تنفيذ نشاط على النظام
            perform_system_activity()
            
            # الانتظار
            time.sleep(PING_INTERVAL + random.uniform(-5, 5))
        except Exception as e:
            logger.error(f"❌ خطأ في خيط النشاط: {e}")
            time.sleep(10)

def ping_thread():
    """خيط للاتصال بالتطبيق الرئيسي بشكل دوري"""
    logger.info("🚀 بدء خيط الاتصال")
    
    while _active:
        try:
            # الاتصال بالتطبيق الرئيسي
            ping_main_app()
            
            # الاتصال بخدمات المراقبة الخارجية (أحيانًا)
            if random.random() < 0.2 and _uptime_monitor_urls:  # 20% من الوقت
                ping_external_monitors()
            
            # الانتظار
            time.sleep(PING_INTERVAL + random.uniform(-5, 5))
        except Exception as e:
            logger.error(f"❌ خطأ في خيط الاتصال: {e}")
            time.sleep(15)

def check_thread():
    """خيط للتحقق من حالة النظام وإعادة تشغيله إذا لزم الأمر"""
    logger.info("🚀 بدء خيط التحقق")
    
    last_restart_time = time.time()
    
    while _active:
        try:
            # التحقق من حالة نظام الإشارات
            is_signal_system_active = check_signal_system()
            
            # إعادة تشغيل النظام إذا كان غير نشط
            if not is_signal_system_active:
                logger.warning("⚠️ نظام الإشارات غير نشط، جاري إعادة تشغيله...")
                restart_application()
                
            # إعادة تشغيل دورية للنظام (كل RESTART_MINUTES دقيقة)
            minutes_since_restart = (time.time() - last_restart_time) / 60
            if minutes_since_restart > RESTART_MINUTES:
                logger.info(f"🔄 إعادة تشغيل دورية بعد {int(minutes_since_restart)} دقيقة")
                if restart_application():
                    last_restart_time = time.time()
            
            # الانتظار
            time.sleep(CHECK_INTERVAL + random.uniform(-10, 10))
        except Exception as e:
            logger.error(f"❌ خطأ في خيط التحقق: {e}")
            time.sleep(30)

def run_server():
    """تشغيل خادم Flask"""
    try:
        app.run(host='0.0.0.0', port=KEEP_ALIVE_PORT, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ فشل في تشغيل خادم Flask: {e}")

# وظائف التحكم العامة
def start(monitor_urls=None):
    """
    بدء نظام الاستمرارية
    
    Args:
        monitor_urls: قائمة روابط خدمات المراقبة الخارجية (اختياري)
    """
    global _active, _started_at, _uptime_monitor_urls
    
    if _active:
        logger.warning("⚠️ نظام الاستمرارية يعمل بالفعل")
        return False
    
    logger.info("🚀 بدء نظام الاستمرارية")
    _active = True
    _started_at = time.time()
    
    # تخزين روابط المراقبة
    if monitor_urls and isinstance(monitor_urls, list):
        _uptime_monitor_urls = monitor_urls
    
    # بدء خادم Flask
    server_thread = threading.Thread(target=run_server, name="ServerThread")
    server_thread.daemon = True
    server_thread.start()
    
    # بدء خيط النشاط
    activity_thread_instance = threading.Thread(target=activity_thread, name="ActivityThread")
    activity_thread_instance.daemon = True
    activity_thread_instance.start()
    
    # بدء خيط الاتصال
    ping_thread_instance = threading.Thread(target=ping_thread, name="PingThread")
    ping_thread_instance.daemon = True
    ping_thread_instance.start()
    
    # بدء خيط التحقق
    check_thread_instance = threading.Thread(target=check_thread, name="CheckThread")
    check_thread_instance.daemon = True
    check_thread_instance.start()
    
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
    
    # إعطاء وقت للخيوط للتوقف
    time.sleep(1)
    
    logger.info("✅ تم إيقاف نظام الاستمرارية")
    return True

def add_uptime_monitor(url):
    """
    إضافة رابط خدمة مراقبة خارجية
    
    Args:
        url: رابط خدمة المراقبة
    """
    global _uptime_monitor_urls
    
    if url and url not in _uptime_monitor_urls:
        _uptime_monitor_urls.append(url)
        logger.info(f"تمت إضافة خدمة المراقبة: {url}")
        return True
    return False

# معالجة إنهاء التطبيق
def cleanup():
    """تنظيف الموارد عند الإغلاق"""
    if _active:
        stop()

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda sig, frame: cleanup())
signal.signal(signal.SIGINT, lambda sig, frame: cleanup())

# روابط مراقبة افتراضية
DEFAULT_MONITOR_URLS = [
    "https://cronitor.link/p/eeb7d60502ac4bf191e2adf0a373b18a/CXhDuj",
    "https://uptime.betterstack.com/api/v1/heartbeat/zp5uNTQCZ3uGrK36VaBFT17r",
    "https://status.instatus.com/heartbeat/9ad1ec74-72c1-438a-a7e7-d40c7e98a56d"
]

# تشغيل نظام الاستمرارية تلقائيًا عند استيراد الملف
if __name__ == "__main__":
    start(DEFAULT_MONITOR_URLS)