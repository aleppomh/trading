"""
نظام متقدم لمنع وضع الخمول على Replit
هذا النظام يعمل بطريقة أكثر فعالية عن طريق إبقاء النظام نشطًا حتى عند الخروج من Replit
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
from urllib.parse import urljoin

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("no_sleep")

# التكوين العام
DEFAULT_INTERVAL = 45  # ثانية
DEFAULT_TIMEOUT = 30   # ثانية
DOMAIN_CHECK_INTERVAL = 120  # ثانية
MAX_ERRORS = 5  # عدد الأخطاء المتتالية قبل تسجيل تحذير بالغ

# المتغيرات العامة
_active = False
_last_ping_time = time.time()
_error_count = 0
_ping_count = 0
_current_domain = None

def get_replit_domain():
    """الحصول على دومين Replit الديناميكي"""
    try:
        # محاولة الحصول على الدومين المخصص أولاً
        try:
            from custom_domain_config import CUSTOM_DOMAIN
            if CUSTOM_DOMAIN and isinstance(CUSTOM_DOMAIN, str) and len(CUSTOM_DOMAIN) > 5:
                logger.info(f"تم استخدام الدومين المخصص: {CUSTOM_DOMAIN}")
                return f"https://{CUSTOM_DOMAIN}"
        except (ImportError, Exception) as e:
            pass  # تجاهل الخطأ واستمر

        # الحصول على المعلومات من متغيرات البيئة
        repl_slug = os.environ.get('REPL_SLUG')
        repl_owner = os.environ.get('REPL_OWNER')
        
        # إذا كانت متوفرة، استخدم الصيغة الجديدة
        if repl_slug and repl_owner:
            domain = f"https://{repl_slug}.{repl_owner}.repl.co"
            logger.info(f"تم استخدام دومين Replit من متغيرات البيئة: {domain}")
            return domain
            
        # محاولة القراءة من ملف التكوين
        if os.path.exists('/etc/replit/cluster-url'):
            with open('/etc/replit/cluster-url', 'r') as f:
                cluster_url = f.read().strip()
                repl_slug = os.environ.get('REPL_SLUG', 'repl')
                domain = f"https://{repl_slug}.{cluster_url}"
                logger.info(f"تم استخدام دومين Replit من ملف التكوين: {domain}")
                return domain
                
    except Exception as e:
        logger.warning(f"فشل في الحصول على دومين Replit: {e}")
    
    # استخدام دومين احتياطي في حالة فشل كل المحاولات
    backup_domain = "https://f5fb8356-b420-4e32-b2b6-05ac9d1a1c71-00-3blbjrsd87z4d.janeway.replit.dev"
    logger.warning(f"استخدام دومين احتياطي: {backup_domain}")
    return backup_domain

def perform_activity():
    """
    تنفيذ أنشطة حقيقية على النظام لمنع وضع الخمول
    هذه الأنشطة تشمل عمليات ملفات وحسابات وذاكرة فعلية
    """
    try:
        # 1. إنشاء ملف مؤقت وكتابة بيانات به
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"temp_activity_{timestamp}_{random.randint(1000, 9999)}.txt"
        
        with open(temp_file, "w") as f:
            f.write(f"نشاط منع الخمول: {datetime.datetime.now()}\n")
            # كتابة بعض البيانات العشوائية
            for i in range(10):
                f.write(f"سطر بيانات عشوائية {i}: {random.random() * 1000}\n")
        
        # 2. قراءة الملف
        with open(temp_file, "r") as f:
            data = f.read()
            
        # 3. إنشاء مصفوفة وإجراء عمليات عليها
        arr = []
        for i in range(1000):
            arr.append(random.random())
        
        # حساب المتوسط
        avg = sum(arr) / len(arr)
        
        # 4. الوصول إلى الشبكة (اختياري)
        hostname = socket.gethostname()
        
        try:
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = "127.0.0.1"
        
        # 5. حذف الملف المؤقت
        os.remove(temp_file)
        
        # تسجيل النشاط
        logger.debug(f"تم تنفيذ نشاط منع الخمول: متوسط={avg:.2f}, المضيف={hostname}, IP={ip_address}")
        
        return True
    except Exception as e:
        logger.error(f"فشل في تنفيذ نشاط منع الخمول: {e}")
        return False

def ping_self():
    """
    إجراء اتصال ذاتي لإبقاء التطبيق نشطًا
    """
    global _last_ping_time, _error_count, _ping_count, _current_domain
    
    # الحصول على دومين Replit (يتم التحقق منه دوريًا)
    current_time = time.time()
    if _current_domain is None or (current_time - _last_ping_time) > DOMAIN_CHECK_INTERVAL:
        _current_domain = get_replit_domain()
    
    # تكوين طلب HTTP
    endpoint = random.choice(["ping", "signal_status", ""])
    url = urljoin(_current_domain, endpoint)
    
    # إضافة معلمات عشوائية لمنع التخزين المؤقت
    params = {
        "ts": current_time,
        "r": random.random(),
        "s": "ping",
        "type": "keepalive"
    }
    
    # تكوين ترويسات HTTP
    headers = {
        "User-Agent": f"ReplicationKeepAlive/{random.randint(1, 100)}",
        "X-Keep-Alive": "true",
        "X-No-Sleep": "active",
        "Cache-Control": "no-cache, no-store"
    }
    
    try:
        # إجراء طلب HTTP
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        
        # التحقق من الاستجابة
        if response.status_code == 200:
            _last_ping_time = current_time
            _error_count = 0
            _ping_count += 1
            logger.info(f"Ping #{_ping_count} ناجح: {url}")
            return True
        else:
            _error_count += 1
            logger.warning(f"Ping فشل مع كود استجابة: {response.status_code}")
    except requests.RequestException as e:
        _error_count += 1
        logger.error(f"فشل في الاتصال بـ {url}: {e}")
    except Exception as e:
        _error_count += 1
        logger.error(f"خطأ غير متوقع: {e}")
    
    # تسجيل تحذير بالغ إذا كان هناك العديد من الأخطاء المتتالية
    if _error_count >= MAX_ERRORS:
        logger.critical(f"⚠️ {_error_count} أخطاء متتالية في الاتصال الذاتي! قد يكون التطبيق في خطر الخمول!")
    
    return False

def _no_sleep_thread():
    """
    خيط منفصل لمنع وضع الخمول
    يقوم بتنفيذ أنشطة وإجراء اتصالات ذاتية بشكل دوري
    """
    global _active
    
    logger.info("🔄 بدء خيط منع الخمول")
    
    while _active:
        try:
            # إجراء نشاط حقيقي على النظام
            activity_success = perform_activity()
            
            # إجراء اتصال ذاتي
            ping_success = ping_self()
            
            # تعديل الفاصل الزمني بناءً على نجاح العمليات
            if activity_success and ping_success:
                # كل شيء يعمل بشكل جيد، استخدم الفاصل الزمني العادي
                interval = DEFAULT_INTERVAL
            else:
                # هناك مشكلة، تقليل الفاصل الزمني
                interval = max(15, DEFAULT_INTERVAL // 2)
            
            # إضافة عنصر عشوائي لتجنب الاتصالات المتزامنة
            jitter = random.uniform(-5, 5)
            wait_time = interval + jitter
            
            logger.debug(f"الانتظار {wait_time:.1f} ثانية قبل النشاط التالي")
            
            # الانتظار مع التحقق من أن النظام لا يزال نشطًا
            end_time = time.time() + wait_time
            while time.time() < end_time and _active:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"خطأ في خيط منع الخمول: {e}")
            # الانتظار قبل المحاولة مرة أخرى في حالة الخطأ
            time.sleep(max(5, DEFAULT_INTERVAL // 4))
    
    logger.info("🛑 توقف خيط منع الخمول")

def start():
    """
    بدء نظام منع الخمول
    """
    global _active
    
    if _active:
        logger.warning("نظام منع الخمول يعمل بالفعل")
        return False
    
    logger.info("🚀 بدء نظام منع الخمول")
    _active = True
    
    # بدء خيط منع الخمول
    thread = threading.Thread(target=_no_sleep_thread, name="NoSleepThread")
    thread.daemon = True
    thread.start()
    
    return True

def stop():
    """
    إيقاف نظام منع الخمول
    """
    global _active
    
    if not _active:
        logger.warning("نظام منع الخمول متوقف بالفعل")
        return False
    
    logger.info("🛑 إيقاف نظام منع الخمول")
    _active = False
    
    return True

def get_status():
    """
    الحصول على حالة نظام منع الخمول
    """
    return {
        "active": _active,
        "last_ping_time": datetime.datetime.fromtimestamp(_last_ping_time).strftime("%Y-%m-%d %H:%M:%S"),
        "error_count": _error_count,
        "ping_count": _ping_count,
        "domain": _current_domain
    }

# بدء نظام منع الخمول تلقائيًا عند استيراد هذا الملف
# إزالة التعليق من السطر أدناه لبدء التشغيل التلقائي
# start()

# تسجيل وظيفة إيقاف النظام عند انتهاء البرنامج
import atexit
atexit.register(stop)