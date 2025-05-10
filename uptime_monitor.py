"""
نظام مراقبة الاستمرارية
هذا النظام يعمل بالتزامن مع replit_always_on.py و keep_replit_alive.py للتأكد من عدم دخول البوت في وضع الخمول على منصة Replit

يوفر آليات إضافية للحفاظ على استمرارية التطبيق:
1. يتحقق من سجلات النظام ويكتشف فترات الخمول
2. يستخدم تقنية مختلفة للاتصال بخدمة Replit
3. يقدم معلومات تشخيصية متقدمة
4. يمكن تكوينه للعمل مع خدمات مراقبة خارجية مثل UptimeRobot
"""

import os
import sys
import time
import logging
import threading
import random
import json
import requests
import subprocess
import platform
import datetime
import signal
from urllib.parse import urlparse
import atexit

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("uptime_monitor")

# ضبط مستوى السجلات لتجنب السجلات الزائدة
requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.WARNING)

# الثوابت والإعدادات
CHECK_INTERVAL = 60  # فحص كل دقيقة
ACTIVITY_INTERVAL = 120  # إجراء نشاط كل دقيقتين
MONITOR_SERVICES = [
    "https://uptime-kuma.io",  # يمكن استبدالها بخدمة مراقبة حقيقية
    "https://uptime.repl.dev/ping"  # خدمة Replit للمراقبة
]

# المتغيرات العامة
is_running = False
last_check_time = time.time()
last_activity_time = time.time()
startup_time = time.time()
uptime_check_thread = None
active_threads = []

def get_app_url():
    """الحصول على عنوان URL للتطبيق الحالي"""
    try:
        # محاولة الحصول على المعلومات من متغيرات البيئة الخاصة بـ Replit
        repl_slug = os.environ.get('REPL_SLUG')
        repl_owner = os.environ.get('REPL_OWNER')
        
        if repl_slug and repl_owner:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
        
        # محاولة استخراج المعلومات من REPLIT_DB_URL
        db_url = os.environ.get('REPLIT_DB_URL', '')
        if db_url:
            parsed = urlparse(db_url)
            if parsed.netloc:
                parts = parsed.netloc.split('.')
                if len(parts) >= 4:  # تنسيق نموذجي
                    return f"https://{parts[0]}.{parts[1]}.repl.co"
        
        # محاولة الحصول على المعلومات من ملف التكوين
        if os.path.exists('.replit'):
            with open('.replit', 'r') as f:
                content = f.read()
                if 'run=' in content:
                    return "https://" + repl_slug + "." + repl_owner + ".repl.co"
    
    except Exception as e:
        logger.error(f"فشل في الحصول على عنوان URL للتطبيق: {e}")
    
    # إذا وصلنا إلى هنا، فلنعد القيمة الافتراضية
    return "https://replit.com"

def get_system_stats():
    """الحصول على إحصاءات النظام الأساسية"""
    stats = {
        "timestamp": datetime.datetime.now().isoformat(),
        "uptime_seconds": time.time() - startup_time,
        "platform": platform.platform(),
        "python_version": sys.version,
        "cpu_count": os.cpu_count(),
        "threads": threading.active_count(),
        "active_custom_threads": len(active_threads)
    }
    
    # محاولة إضافة استخدام الذاكرة إذا كان ذلك ممكنًا
    try:
        import psutil
        stats["memory_percent"] = psutil.virtual_memory().percent
        stats["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    except:
        pass
        
    return stats

def perform_system_activity():
    """إجراء نشاط على النظام لإبقائه نشطًا"""
    global last_activity_time
    
    try:
        # إنشاء ملف مؤقت
        temp_file = f"uptime_activity_{int(time.time())}.tmp"
        with open(temp_file, "w") as f:
            f.write(f"Activity at {datetime.datetime.now()}\n")
            f.write(f"Random: {random.random()}\n")
            
        # قراءة الملف ثم حذفه
        with open(temp_file, "r") as f:
            content = f.read()
        os.remove(temp_file)
        
        # الاتصال بخدمة Replit نفسها
        try:
            r = requests.get("https://replit.com/~", timeout=5)
            logger.debug(f"Replit status: {r.status_code}")
        except:
            pass
            
        # تغيير الوقت الحالي في ملف مؤقت آخر
        with open("last_activity.txt", "w") as f:
            f.write(str(time.time()))
            
        last_activity_time = time.time()
        logger.debug("تم إجراء نشاط على النظام")
        return True
    except Exception as e:
        logger.error(f"فشل في إجراء نشاط على النظام: {e}")
        return False

def check_signal_system():
    """التحقق من حالة نظام الإشارات واستعادته إذا لزم الأمر"""
    try:
        # استيراد مدير الإشارات
        import signal_manager
        
        # التحقق من حالة نظام الإشارات
        if hasattr(signal_manager, 'check_signal_system_status'):
            if not signal_manager.check_signal_system_status():
                logger.warning("❌ نظام الإشارات متوقف! جاري إعادة تشغيله...")
                if hasattr(signal_manager, 'restart_signal_system'):
                    signal_manager.restart_signal_system()
                    logger.info("✅ تم إعادة تشغيل نظام الإشارات")
                    return True
        return False
    except Exception as e:
        logger.error(f"فشل في التحقق من نظام الإشارات: {e}")
        return False

def check_always_on_systems():
    """التحقق من حالة أنظمة الاستمرارية الأخرى"""
    try:
        # التحقق من نظام keep_replit_alive.py
        try:
            import keep_replit_alive
            if hasattr(keep_replit_alive, 'get_status'):
                status = keep_replit_alive.get_status()
                logger.info(f"حالة keep_replit_alive: {status}")
        except:
            pass
            
        # التحقق من نظام replit_always_on.py
        try:
            import replit_always_on
            if hasattr(replit_always_on, 'get_status'):
                status = replit_always_on.get_status()
                logger.info(f"حالة replit_always_on: {status}")
        except:
            pass
            
        # التحقق من نظام always_on.py
        try:
            import always_on
            if hasattr(always_on, 'get_status'):
                status = always_on.get_status()
                logger.info(f"حالة always_on: {status}")
        except:
            pass
            
        return True
    except Exception as e:
        logger.error(f"فشل في التحقق من أنظمة الاستمرارية: {e}")
        return False

def ping_monitors():
    """الاتصال بخدمات المراقبة الخارجية"""
    for url in MONITOR_SERVICES:
        try:
            resp = requests.get(url, timeout=5)
            logger.debug(f"استدعاء خدمة المراقبة {url}: {resp.status_code}")
        except:
            pass

def uptime_monitor_thread():
    """الخيط الرئيسي لمراقبة الاستمرارية"""
    global is_running, last_check_time, last_activity_time
    
    logger.info("🚀 بدء خيط مراقبة الاستمرارية")
    
    while is_running:
        try:
            # فحص الوقت منذ آخر نشاط
            time_since_last_activity = time.time() - last_activity_time
            if time_since_last_activity >= ACTIVITY_INTERVAL:
                perform_system_activity()
                
            # فحص الوقت منذ آخر فحص
            time_since_last_check = time.time() - last_check_time
            if time_since_last_check >= CHECK_INTERVAL:
                check_signal_system()
                check_always_on_systems()
                ping_monitors()
                last_check_time = time.time()
                
            # توثيق وقت التشغيل
            uptime = time.time() - startup_time
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            logger.debug(f"وقت التشغيل: {int(hours)} ساعة, {int(minutes)} دقيقة, {int(seconds)} ثانية")
            
            # الانتظار
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"خطأ في خيط المراقبة: {e}")
            time.sleep(30)  # الانتظار قبل المحاولة مرة أخرى

def start():
    """بدء نظام مراقبة الاستمرارية"""
    global is_running, uptime_check_thread, active_threads
    
    if is_running:
        logger.warning("نظام مراقبة الاستمرارية قيد التشغيل بالفعل")
        return False
        
    is_running = True
    
    # تسجيل دالة التنظيف عند الخروج
    atexit.register(cleanup)
    
    # بدء خيط المراقبة
    uptime_check_thread = threading.Thread(
        target=uptime_monitor_thread,
        name="UptimeMonitorThread",
        daemon=True
    )
    uptime_check_thread.start()
    active_threads.append(uptime_check_thread)
    
    logger.info("✅ تم بدء نظام مراقبة الاستمرارية")
    return True

def stop():
    """إيقاف نظام مراقبة الاستمرارية"""
    global is_running
    
    if not is_running:
        logger.warning("نظام مراقبة الاستمرارية متوقف بالفعل")
        return False
        
    is_running = False
    cleanup()
    logger.info("✅ تم إيقاف نظام مراقبة الاستمرارية")
    return True

def cleanup():
    """تنظيف الموارد المستخدمة"""
    global active_threads
    
    logger.info("🧹 تنظيف موارد نظام المراقبة...")
    
    # حذف أي ملفات مؤقتة
    for file in os.listdir('.'):
        if file.startswith('uptime_activity_') and file.endswith('.tmp'):
            try:
                os.remove(file)
            except:
                pass
                
    active_threads = []

def get_status():
    """الحصول على حالة النظام"""
    return {
        "is_running": is_running,
        "uptime_seconds": time.time() - startup_time,
        "last_check_time": last_check_time,
        "last_activity_time": last_activity_time,
        "active_threads": len(active_threads),
        "system_stats": get_system_stats()
    }

if __name__ == "__main__":
    # عند تنفيذ الملف مباشرة، ابدأ النظام
    start()
    
    # البقاء على قيد الحياة
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop()