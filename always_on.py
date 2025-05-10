"""
نظام متطور لضمان استمرار عمل البوت على منصة Replit
هذا النظام يتكامل مع حساب Replit المرقى لضمان عدم دخول البوت في وضع الخمول
تم تحديثه ليضمن أيضًا إرسال الإشارات بفاصل زمني لا يتجاوز 8 دقائق مطلقًا
"""

import os
import time
import threading
import logging
import random
import signal
import socket
import subprocess
import json
import sys
import atexit
import datetime
from urllib.parse import urljoin

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("always_on")

# ثوابت عامة - تم تحديثها لضمان تشغيل النظام بشكل أفضل
DEFAULT_URL = "https://your-replit-app.repl.co"
DEFAULT_PING_INTERVAL = 40  # ثانية - تم تقليله لزيادة تكرار الاتصال
DEFAULT_SIGNAL_CHECK_INTERVAL = 120  # ثانية (2 دقائق) - تم تقليله لضمان الاستجابة السريعة
INTENSIVE_SIGNAL_CHECK_INTERVAL = 40  # ثانية - نظام المراقبة المكثف، تم تقليله أيضًا
MAX_ERRORS = 5  # عدد الأخطاء المتتالية قبل إعادة البدء
WAKEUP_METHODS = 3  # عدد طرق الحفاظ على النشاط
ABSOLUTE_MAX_SIGNAL_INTERVAL = 420  # الحد الأقصى المطلق (7 دقائق) تم ضبطه ليتوافق مع signal_manager.py

# متغيرات التتبع
_active = False
_ping_count = 0
_signal_check_count = 0
_error_count = 0
_last_signal_time = None
_threads = []
_stop_requested = False
_signals_tracked = {}

def get_replit_url():
    """الحصول على رابط Replit بشكل ديناميكي"""
    try:
        # محاولة الحصول على الدومين المخصص
        try:
            from custom_domain_config import CUSTOM_DOMAIN
            if CUSTOM_DOMAIN and len(CUSTOM_DOMAIN) > 5:
                return f"https://{CUSTOM_DOMAIN}"
        except (ImportError, Exception):
            pass
        
        # محاولة قراءة ملف التكوين الخاص بـ Replit
        if os.path.exists('/etc/replit/cluster-url'):
            with open('/etc/replit/cluster-url', 'r') as f:
                cluster_url = f.read().strip()
                repl_slug = os.environ.get('REPL_SLUG', 'repl')
                return f"https://{repl_slug}.{cluster_url}"
                
        # محاولة الحصول على الرابط من متغيرات البيئة
        repl_slug = os.environ.get('REPL_SLUG')
        repl_owner = os.environ.get('REPL_OWNER')
        if repl_slug and repl_owner:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
    
    except Exception as e:
        logger.error(f"فشل في الحصول على رابط Replit: {e}")
    
    # استخدام الرابط الافتراضي كحل أخير
    return DEFAULT_URL

def create_temp_file():
    """إنشاء ملف مؤقت للمساعدة في الحفاظ على النشاط"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"temp_activity_{timestamp}_{random.randint(1000, 9999)}.txt"
        
        # كتابة بيانات عشوائية
        with open(filename, 'w') as f:
            f.write(f"Keeping process alive at {datetime.datetime.now()}\n")
            f.write(f"Random data: {random.random()}\n")
            f.write(f"Hostname: {socket.gethostname()}\n")
            
        # قراءة الملف
        with open(filename, 'r') as f:
            content = f.read()
            
        # حذف الملف
        os.remove(filename)
        
        return True
    except Exception as e:
        logger.error(f"فشل في إنشاء/حذف الملف المؤقت: {e}")
        return False

def perform_system_interaction():
    """
    تنفيذ أنشطة متنوعة على النظام للحفاظ على نشاطه
    """
    actions = [
        # إنشاء وحذف ملف مؤقت
        create_temp_file,
        
        # قراءة معلومات النظام
        lambda: bool(os.getloadavg()),
        
        # تنفيذ عمليات على الذاكرة
        lambda: bool(time.time() + random.random()),
        
        # إنشاء مصفوفة والقيام بعمليات عليها
        lambda: bool(sum([random.random() for _ in range(1000)]) > 0),
    ]
    
    # اختيار عملية عشوائية
    action = random.choice(actions)
    try:
        return action()
    except Exception as e:
        logger.error(f"فشل في تنفيذ نشاط النظام: {e}")
        return False

def check_signal_process():
    """التحقق من حالة توليد الإشارات وإعادة تشغيلها إذا لزم الأمر"""
    global _signal_check_count, _last_signal_time, _signals_tracked
    
    try:
        # زيادة عداد فحص الإشارات
        _signal_check_count += 1
        
        # استدعاء النظام لفحص الإشارات
        from app import signal_status, generate_new_signal, check_expired_signals
        from signal_manager import get_signal_status, check_signal_system_status
        
        # فحص حالة النظام
        if not check_signal_system_status():
            logger.warning("⚠️ نظام الإشارات متوقف! جاري إعادة تشغيله...")
            generate_new_signal()
            logger.info("✅ تم إعادة تشغيل نظام الإشارات")
            return True
        
        # الحصول على حالة توليد الإشارات
        status = get_signal_status()
        
        # تحديث آخر وقت للإشارة (إذا كان لدينا وقت سابق)
        if status.get('last_signal_time'):
            if _last_signal_time != status['last_signal_time']:
                _last_signal_time = status['last_signal_time']
                logger.info(f"🔄 تم تحديث وقت آخر إشارة: {_last_signal_time}")
        
        # جلب معلومات الإشارات
        signal_count = status.get('signal_count', 0)
        recent_signals = status.get('recent_signals', [])
        
        # تتبع الإشارات المرسلة
        for signal_time in recent_signals:
            if signal_time not in _signals_tracked:
                _signals_tracked[signal_time] = datetime.datetime.now()
                logger.info(f"✅ تم تتبع إشارة جديدة من وقت: {signal_time}")
        
        # حذف الإشارات القديمة من المتابعة
        if len(_signals_tracked) > 20:
            # الاحتفاظ بآخر 20 إشارة فقط
            _signals_tracked = dict(list(_signals_tracked.items())[-20:])
        
        # فحص ما إذا كان هناك حاجة لتوليد إشارة جديدة
        time_until_next = status.get('time_until_next_signal', 0)
        
        # إذا كان الوقت المتبقي 0 أو تجاوز الفترة المطلوبة، نولد إشارة
        if time_until_next <= 0:
            logger.info("🔄 جاري توليد إشارة جديدة...")
            check_expired_signals()
            generate_new_signal()
            logger.info("✅ تم طلب توليد إشارة جديدة")
            return True
            
        # لا حاجة لتوليد إشارة جديدة الآن
        minutes = time_until_next // 60
        seconds = time_until_next % 60
        logger.info(f"⏱️ الوقت المتبقي للإشارة التالية: {minutes} دقيقة و {seconds} ثانية")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ أثناء فحص حالة الإشارات: {e}")
        return False

def ping_server():
    """
    إرسال نداء اتصال إلى الخادم للحفاظ عليه نشطًا
    """
    global _ping_count, _error_count
    
    try:
        # زيادة عداد نداءات الاتصال
        _ping_count += 1
        
        # الحصول على رابط التطبيق
        base_url = get_replit_url()
        
        # اختيار مسار عشوائي
        paths = ["ping", "signal_status", ""]
        path = random.choice(paths)
        
        # إنشاء رابط كامل
        url = urljoin(base_url, path)
        
        # إضافة معلمات عشوائية لتجنب التخزين المؤقت
        if "?" not in url:
            url += f"?ts={time.time()}&r={random.random()}"
        else:
            url += f"&ts={time.time()}&r={random.random()}"
            
        # إرسال طلب HTTP
        import requests
        headers = {
            "User-Agent": f"AlwaysOnSystem/{random.randint(100, 999)}",
            "Cache-Control": "no-cache",
            "X-Always-On": "true"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            logger.info(f"✅ نداء اتصال ناجح إلى {path or '/'}: {response.status_code}")
            _error_count = 0  # إعادة تعيين عداد الأخطاء
            return True
        else:
            _error_count += 1
            logger.warning(f"⚠️ نداء اتصال غير ناجح: {response.status_code}")
            return False
            
    except Exception as e:
        _error_count += 1
        logger.error(f"❌ خطأ في نداء الاتصال: {e}")
        if _error_count >= MAX_ERRORS:
            logger.critical(f"🚨 تم تجاوز الحد الأقصى للأخطاء ({MAX_ERRORS})! قد تكون هناك مشكلة في الاتصال.")
        return False

def wakeup_thread():
    """
    خيط للحفاظ على نشاط النظام من خلال نداءات اتصال دورية
    """
    global _stop_requested
    
    logger.info("🚀 بدء خيط الحفاظ على النشاط")
    
    while not _stop_requested:
        try:
            # تنفيذ تفاعل مع النظام للحفاظ على النشاط
            perform_system_interaction()
            
            # إرسال نداء اتصال
            ping_server()
            
            # الانتظار قبل النداء التالي (مع إضافة عنصر عشوائي)
            wait_time = DEFAULT_PING_INTERVAL + random.uniform(-5, 5)
            
            # انتظار مع التحقق من طلب التوقف
            end_time = time.time() + wait_time
            while time.time() < end_time and not _stop_requested:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ خطأ في خيط الحفاظ على النشاط: {e}")
            # انتظار قصير قبل المحاولة مرة أخرى
            time.sleep(10)
    
    logger.info("🛑 توقف خيط الحفاظ على النشاط")

def enforce_max_signal_interval():
    """
    مراقبة صارمة لضمان عدم تجاوز الحد الأقصى المطلق للفاصل الزمني بين الإشارات
    هذه الدالة تتحقق من آخر إشارة وتفرض إرسال إشارة جديدة إذا اقترب الوقت من الحد الأقصى المطلق
    تم تحديثها لضمان الفاصل الزمني بين 4-6 دقائق بين الإشارات
    """
    global _stop_requested, _last_signal_time
    
    try:
        # استدعاء النظام لفحص الإشارات
        from app import generate_new_signal
        from signal_manager import get_signal_status
        from models import Signal
        from datetime import datetime, timedelta
        from app import app
        
        # تعريف المتغير محلياً لتجنب الخطأ
        MIN_SIGNAL_INTERVAL_SECONDS = 240  # الحد الأدنى للفاصل الزمني هو 4 دقائق (240 ثانية)
        
        with app.app_context():
            # الحصول على حالة النظام
            status = get_signal_status()
            
            # الحصول على آخر إشارة من قاعدة البيانات
            last_signal = Signal.query.filter_by(doubling_strategy=False).order_by(Signal.created_at.desc()).first()
            
            if last_signal:
                # حساب الوقت المنقضي
                current_time = datetime.utcnow()
                elapsed_seconds = (current_time - last_signal.created_at).total_seconds()
                
                # شروط مختلفة للتوقيت:
                # 1. إذا اقترب من تجاوز الحد الأقصى المطلق (قبل 30 ثانية)
                if elapsed_seconds >= (ABSOLUTE_MAX_SIGNAL_INTERVAL - 30):
                    logger.warning(f"⚠️⚠️⚠️ تنبيه: اقتراب تجاوز الحد الأقصى المطلق ({elapsed_seconds:.1f} ثانية من أصل {ABSOLUTE_MAX_SIGNAL_INTERVAL} ثانية)!")
                    logger.warning("🚨 فرض إرسال إشارة جديدة لمنع تجاوز الحد الأقصى المطلق!")
                    
                    # محاولة فرض إرسال إشارة جديدة
                    generate_new_signal(force=True)
                    logger.warning("✅✅✅ تم طلب إرسال إشارة جديدة بشكل إجباري!")
                    return True
                
                # 2. إذا تجاوز الحد الأقصى المطلوب (360 ثانية)، يرسل إشارة
                elif elapsed_seconds >= 360:  # 6 دقائق
                    logger.warning(f"⚠️ تنبيه: تم تجاوز الحد الأقصى المطلوب ({elapsed_seconds:.1f} ثانية > 360 ثانية)!")
                    logger.warning("🔄 فرض إرسال إشارة جديدة للمحافظة على الفاصل الزمني المطلوب!")
                    
                    # إرسال إشارة جديدة 
                    generate_new_signal(force=True)
                    logger.info("✅ تم طلب إرسال إشارة جديدة")
                    return True
                
                # 3. إذا تجاوز الحد الأدنى (240 ثانية) ولم يكن هناك إشارة جديدة، يمكن إرسال إشارة
                elif elapsed_seconds >= 240 and not status.get('signal_scheduled', False):  # 4 دقائق
                    prob = (elapsed_seconds - 240) / 120  # زيادة الاحتمالية تدريجياً (0 عند 4 دقائق، 1 عند 6 دقائق)
                    
                    # احتمالية إرسال إشارة جديدة تزداد مع مرور الوقت
                    if random.random() < prob:
                        logger.info(f"🎲 تجاوز الحد الأدنى ({elapsed_seconds:.1f} ثانية > 240 ثانية) مع احتمالية {prob:.2f}")
                        logger.info("🔄 إرسال إشارة جديدة للمحافظة على تواتر الإشارات")
                        
                        # إرسال إشارة جديدة
                        generate_new_signal()
                        logger.info("✅ تم طلب إرسال إشارة جديدة")
                        return True
                
                # تسجيل الوقت المتبقي
                if elapsed_seconds >= 240:  # اكتمل الحد الأدنى
                    remaining_to_max = 360 - elapsed_seconds  # الوقت المتبقي للحد الأقصى
                    logger.info(f"⏱️ تم تجاوز الحد الأدنى، متبقي {remaining_to_max:.1f} ثانية للحد الأقصى المطلوب")
                else:
                    remaining_to_min = 240 - elapsed_seconds  # الوقت المتبقي للحد الأدنى
                    logger.info(f"⏱️ متبقي {remaining_to_min:.1f} ثانية للحد الأدنى المطلوب")
            
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في نظام مراقبة الحد الأقصى المطلق: {e}")
        return False


def signal_check_thread():
    """
    خيط للتحقق من توليد الإشارات بشكل دوري
    تم تطويره ليشمل مراقبة الحد الأقصى المطلق
    """
    global _stop_requested
    
    # تعريف المتغير محلياً لتجنب الخطأ
    MIN_SIGNAL_INTERVAL_SECONDS = 240  # الحد الأدنى للفاصل الزمني هو 4 دقائق (240 ثانية)
    
    logger.info("🚀 بدء خيط فحص الإشارات")
    
    # انتظار أولي لإعطاء التطبيق وقتًا للبدء
    time.sleep(30)
    
    while not _stop_requested:
        try:
            # فحص حالة توليد الإشارات العادية
            check_signal_process()
            
            # فحص الحد الأقصى المطلق (يتم استدعاؤه بشكل متكرر أكثر)
            if _signal_check_count % 3 == 0:  # كل 3 مرات
                enforce_max_signal_interval()
            
            # الانتظار قبل الفحص التالي
            wait_time = DEFAULT_SIGNAL_CHECK_INTERVAL + random.uniform(-10, 10)
            
            # انتظار مع التحقق من طلب التوقف والقيام بفحوصات متكررة للحد الأقصى
            end_time = time.time() + wait_time
            check_interval = INTENSIVE_SIGNAL_CHECK_INTERVAL  # فحص كل دقيقة
            next_check = time.time() + check_interval
            
            while time.time() < end_time and not _stop_requested:
                # تنفيذ فحص متكرر للحد الأقصى
                if time.time() >= next_check:
                    enforce_max_signal_interval()
                    next_check = time.time() + check_interval
                
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ خطأ في خيط فحص الإشارات: {e}")
            # انتظار قصير قبل المحاولة مرة أخرى
            time.sleep(60)
    
    logger.info("🛑 توقف خيط فحص الإشارات")

def cleanup():
    """تنظيف الموارد عند إنهاء البرنامج"""
    global _stop_requested, _threads
    
    logger.info("🧹 تنظيف الموارد...")
    
    # طلب إيقاف الخيوط
    _stop_requested = True
    
    # انتظار انتهاء جميع الخيوط
    for thread in _threads:
        if thread.is_alive():
            logger.info(f"⏳ انتظار انتهاء الخيط: {thread.name}")
            thread.join(timeout=5)
    
    logger.info("👋 تم تنظيف الموارد")

def start_always_on_system():
    """
    بدء نظام الحفاظ على استمرارية العمل
    """
    global _active, _threads, _stop_requested
    
    # التحقق من أن النظام غير نشط بالفعل
    if _active:
        logger.warning("⚠️ نظام الحفاظ على الاستمرارية نشط بالفعل")
        return False
    
    logger.info("🚀 بدء نظام الحفاظ على استمرارية العمل")
    
    # إعادة تعيين متغيرات الحالة
    _stop_requested = False
    _threads = []
    
    # 1. بدء خيط الحفاظ على النشاط
    for i in range(WAKEUP_METHODS):
        wakeup_thread_instance = threading.Thread(
            target=wakeup_thread,
            name=f"WakeupThread-{i+1}"
        )
        wakeup_thread_instance.daemon = True
        wakeup_thread_instance.start()
        _threads.append(wakeup_thread_instance)
    
    # 2. بدء خيط فحص الإشارات
    signal_thread = threading.Thread(
        target=signal_check_thread,
        name="SignalCheckThread"
    )
    signal_thread.daemon = True
    signal_thread.start()
    _threads.append(signal_thread)
    
    # تسجيل دالة التنظيف
    atexit.register(cleanup)
    
    # تعيين معالجات إشارات النظام
    signal.signal(signal.SIGTERM, lambda sig, frame: cleanup())
    signal.signal(signal.SIGINT, lambda sig, frame: cleanup())
    
    # تحديث الحالة
    _active = True
    
    logger.info("✅ تم بدء نظام الحفاظ على الاستمرارية بنجاح")
    return True

def stop_always_on_system():
    """
    إيقاف نظام الحفاظ على استمرارية العمل
    """
    global _active
    
    # التحقق من أن النظام نشط
    if not _active:
        logger.warning("⚠️ نظام الحفاظ على الاستمرارية متوقف بالفعل")
        return False
    
    logger.info("🛑 إيقاف نظام الحفاظ على الاستمرارية")
    
    # تنظيف الموارد
    cleanup()
    
    # تحديث الحالة
    _active = False
    
    logger.info("✅ تم إيقاف نظام الحفاظ على الاستمرارية بنجاح")
    return True

def get_status():
    """
    الحصول على حالة نظام الحفاظ على الاستمرارية
    """
    return {
        "active": _active,
        "ping_count": _ping_count,
        "signal_check_count": _signal_check_count,
        "error_count": _error_count,
        "last_signal_time": _last_signal_time,
        "signals_tracked": len(_signals_tracked),
        "threads": [t.name for t in _threads if t.is_alive()]
    }

# بدء نظام الحفاظ على الاستمرارية تلقائيًا
try:
    logger.info("🔄 جاري محاولة بدء نظام الحفاظ على استمرارية العمل تلقائيًا")
    # تم إزالة التعليق لبدء النظام تلقائيًا عند استيراد هذا الملف
    start_always_on_system()
except Exception as e:
    logger.error(f"❌ فشل في بدء نظام الحفاظ على الاستمرارية تلقائيًا: {e}")