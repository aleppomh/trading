"""
نقطة البداية الرئيسية للتطبيق - تشغيل خادم Flask وبدء نظام الإشارات
نسخة محسنة مع دعم منع الخمول المتقدم ونظام التعافي الذكي ونظام الاستمرارية الشامل
"""

import os
import time
import logging
import threading
import atexit
import signal
import random  # للنظام البديل عند عدم توفر الأنظمة المتقدمة
import signal_manager  # استيراد مدير الإشارات الجديد
from app import app, check_expired_signals, generate_new_signal
from keep_alive import keep_alive
from replit_fetch import start_fetcher
from pocket_option_otc_pairs import get_all_otc_pairs
from market_pairs import update_active_pairs_in_database as update_market_pairs_in_database

# استيراد أنظمة منع الخمول المتطورة
import no_sleep
import always_on  # نظام متطور للحفاظ على استمرارية العمل

# استيراد نظام keep_replit_alive المتقدم
try:
    import keep_replit_alive  # نظام استمرارية إضافي مع خادم HTTP منفصل
    keep_replit_alive_available = True
    logging.info("✅ تم استيراد نظام keep_replit_alive المتقدم")
except ImportError:
    keep_replit_alive_available = False
    logging.warning("⚠️ لم يتم العثور على نظام keep_replit_alive المتقدم")

# استيراد أنظمة الاستمرارية الشاملة الجديدة
try:
    import replit_always_on  # نظام الاستمرارية الشامل الجديد
    always_on_system_available = True
    logging.info("✅ تم استيراد نظام الاستمرارية الشامل الجديد")
except ImportError:
    always_on_system_available = False
    logging.warning("⚠️ لم يتم العثور على نظام الاستمرارية الشامل الجديد")

# استيراد نظام مراقبة الاستمرارية الإضافي
try:
    import uptime_monitor  # نظام مراقبة الاستمرارية الجديد
    uptime_monitor_available = True
    logging.info("✅ تم استيراد نظام مراقبة الاستمرارية الجديد")
except ImportError:
    uptime_monitor_available = False
    logging.warning("⚠️ لم يتم العثور على نظام مراقبة الاستمرارية الجديد")

# استيراد الأنظمة المتقدمة
try:
    from advanced_error_logger import log_error, log_exception, ErrorSeverity
    error_logging_available = True
    logging.info("✅ تم استيراد نظام تسجيل الأخطاء المتقدم")
except ImportError:
    error_logging_available = False
    logging.warning("⚠️ لم يتم العثور على نظام تسجيل الأخطاء المتقدم")
    
    # إنشاء دوال بديلة في حالة عدم توفر النظام المتقدم
    def log_error(message, severity=None, exception=None, context=None):
        logging.error(message)
    
    def log_exception(message="حدث خطأ غير متوقع", severity=None, context=None):
        logging.exception(message)
    
    class ErrorSeverity:
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        CRITICAL = 4

try:
    from auto_recovery import start_auto_recovery, stop_auto_recovery, get_recovery_status
    recovery_system_available = True
    logging.info("✅ تم استيراد نظام التعافي التلقائي")
except ImportError:
    recovery_system_available = False
    logging.warning("⚠️ لم يتم العثور على نظام التعافي التلقائي")
    
    # إنشاء دوال بديلة في حالة عدم توفر النظام المتقدم
    def start_auto_recovery():
        logging.warning("⚠️ نظام التعافي التلقائي غير متاح")
        return False
    
    def stop_auto_recovery():
        return False
    
    def get_recovery_status():
        return {"status": "unavailable"}

try:
    from adaptive_pair_selector import get_optimal_trading_pair, mark_pair_availability, get_pairs_status
    adaptive_selector_available = True
    logging.info("✅ تم استيراد نظام اختيار الأزواج التكيفي")
except ImportError:
    adaptive_selector_available = False
    logging.warning("⚠️ لم يتم العثور على نظام اختيار الأزواج التكيفي")

# إعداد سجل الأحداث
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# متغيرات عامة
signal_timer = None
signal_thread = None
STOP_THREADS = False

# دالة للتأكد من تشغيل نظام الإشارات كل 5 دقائق
def run_signal_check():
    """
    الدالة المسؤولة عن التحقق من إرسال الإشارات كل 5 دقائق
    """
    global STOP_THREADS
    
    if STOP_THREADS:
        logger.info("توقف خيط فحص الإشارات بناءً على طلب التوقف")
        return
        
    try:
        logger.info("⏰ التحقق من حالة نظام الإشارات...")
        
        # التحقق من حالة نظام الإشارات
        if not signal_manager.check_signal_system_status():
            logger.warning("⚠️ نظام الإشارات غير نشط! جاري إعادة تشغيله...")
            
            try:
                # إعادة تشغيل نظام الإشارات
                signal_manager.restart_signal_system()
                
                # فحص الإشارات منتهية الصلاحية
                with app.app_context():
                    check_expired_signals()
                
                # إنشاء إشارة جديدة (مباشرة)
                with app.app_context():
                    generate_new_signal()
                    
                logger.info("✅ تم إعادة تشغيل نظام الإشارات بنجاح")
            except Exception as e:
                logger.error(f"❌ فشل في إعادة تشغيل نظام الإشارات: {e}")
        else:
            logger.info("✅ نظام الإشارات يعمل بشكل صحيح")
            
            # التحقق من إنشاء إشارة جديدة إذا لزم الأمر
            with app.app_context():
                signal_manager.check_signal_generation()
    except Exception as e:
        logger.error(f"❌ خطأ في خيط فحص الإشارات: {e}")
    
    # إعادة جدولة التحقق التالي
    if not STOP_THREADS:
        global signal_timer
        signal_timer = threading.Timer(300, run_signal_check)  # كل 5 دقائق
        signal_timer.daemon = True
        signal_timer.start()

# دالة تشغيل فحص الإشارات في خيط منفصل
def start_signal_check():
    """
    بدء خيط فحص الإشارات
    """
    global signal_thread
    
    logger.info("بدء خيط فحص الإشارات...")
    signal_thread = threading.Thread(target=run_signal_check, name="SignalCheckThread")
    signal_thread.daemon = True
    signal_thread.start()
    
    logger.info("تم بدء خيط فحص الإشارات بنجاح")

# دالة تحديث الأزواج النشطة
def update_active_pairs():
    """
    تحديث أزواج التداول النشطة في قاعدة البيانات
    """
    with app.app_context():
        try:
            # تحديث أزواج OTC
            logger.info("تحديث أزواج Pocket Option OTC النشطة في قاعدة البيانات...")
            otc_pairs = get_all_otc_pairs()
            updated_count_otc = len(otc_pairs)
            logger.info(f"تم تحديث {updated_count_otc} من أزواج OTC")
            
            # تحديث أزواج البورصة العادية
            logger.info("تحديث أزواج البورصة العادية في قاعدة البيانات...")
            updated_count_market = update_market_pairs_in_database()
            logger.info(f"تم تحديث {updated_count_market} من أزواج البورصة العادية")
            
            logger.info(f"إجمالي الأزواج المحدثة: {updated_count_otc + updated_count_market}")
            return True
        except Exception as e:
            logger.error(f"خطأ أثناء تحديث الأزواج: {e}")
            return False

# دالة التنظيف عند إنهاء التطبيق
def cleanup():
    """
    تنظيف الموارد عند إنهاء التطبيق
    """
    global STOP_THREADS, signal_timer
    
    logger.info("🧹 تنظيف الموارد...")
    
    # إيقاف جميع الخيوط
    STOP_THREADS = True
    
    # إيقاف مؤقت فحص الإشارات
    if signal_timer:
        signal_timer.cancel()
    
    # إيقاف أنظمة منع الخمول
    try:
        # إيقاف النظام التقليدي
        no_sleep.stop()
        logger.info("✅ تم إيقاف نظام منع الخمول التقليدي")
    except Exception as e:
        logger.error(f"❌ خطأ عند إيقاف نظام منع الخمول التقليدي: {e}")
    
    try:
        # إيقاف نظام الاستمرارية المتطور
        always_on.stop_always_on_system()
        logger.info("✅ تم إيقاف نظام الاستمرارية المتطور")
    except Exception as e:
        logger.error(f"❌ خطأ عند إيقاف نظام الاستمرارية المتطور: {e}")
    
    # إيقاف نظام keep_replit_alive
    if keep_replit_alive_available:
        try:
            keep_replit_alive.stop()
            logger.info("✅ تم إيقاف نظام keep_replit_alive")
        except Exception as e:
            logger.error(f"❌ خطأ عند إيقاف نظام keep_replit_alive: {e}")
    
    # إيقاف نظام الاستمرارية الشامل الجديد
    if always_on_system_available:
        try:
            replit_always_on.stop()
            logger.info("✅ تم إيقاف نظام الاستمرارية الشامل الجديد")
        except Exception as e:
            logger.error(f"❌ خطأ عند إيقاف نظام الاستمرارية الشامل الجديد: {e}")
    
    # إيقاف نظام مراقبة الاستمرارية الإضافي
    if uptime_monitor_available:
        try:
            uptime_monitor.stop()
            logger.info("✅ تم إيقاف نظام مراقبة الاستمرارية الجديد")
        except Exception as e:
            logger.error(f"❌ خطأ عند إيقاف نظام مراقبة الاستمرارية الجديد: {e}")
    
    logger.info("👋 تم تنظيف الموارد بنجاح")

# التحضير
def enable_adaptive_pair_selection():
    """
    تفعيل نظام اختيار الأزواج التكيفي في التطبيق
    """
    if not adaptive_selector_available:
        logger.warning("⚠️ لا يمكن تفعيل نظام اختيار الأزواج التكيفي (غير متاح)")
        return False
    
    try:
        # تسجيل الوظائف في وحدة إدارة الإشارات لاستخدامها عند اختيار الأزواج
        signal_manager.register_pair_selector(
            get_optimal_trading_pair, 
            mark_pair_availability,
            get_pairs_status
        )
        
        logger.info("✅ تم تفعيل نظام اختيار الأزواج التكيفي في التطبيق")
        return True
    except Exception as e:
        if error_logging_available:
            log_exception(
                "فشل تفعيل نظام اختيار الأزواج التكيفي",
                ErrorSeverity.MEDIUM,
                "adaptive_selector"
            )
        else:
            logger.error(f"❌ فشل تفعيل نظام اختيار الأزواج التكيفي: {e}")
        return False


def initialize_app():
    """
    تهيئة التطبيق وجميع المكونات
    """
    # تحديث أزواج التداول
    update_active_pairs()
    
    # تفعيل نظام اختيار الأزواج التكيفي
    if adaptive_selector_available:
        enable_adaptive_pair_selection()
    
    # تفعيل آليات منع الخمول
    # 1. نظام keep alive التقليدي
    keep_alive()
    
    # 2. آلية الجلب المستمر
    start_fetcher()
    
    # 3. نظام منع الخمول المتطور
    logger.info("🚀 بدء نظام منع الخمول المتطور...")
    no_sleep.start()
    
    # 4. نظام الاستمرارية المتطور - هذا هو الأكثر فعالية للحفاظ على استمرار العمل
    logger.info("🚀🚀🚀 بدء نظام الاستمرارية المتطور...")
    always_on.start_always_on_system()
    
    # 4.1 نظام keep_replit_alive الإضافي مع خادم HTTP منفصل
    if keep_replit_alive_available:
        logger.info("🚀🚀🚀 بدء نظام keep_replit_alive الإضافي...")
        keep_replit_alive.start()
        logger.info("✅ تم بدء نظام keep_replit_alive الإضافي")
    
    # 5. نظام الاستمرارية الشامل الجديد
    if always_on_system_available:
        logger.info("🚀🚀🚀 بدء نظام الاستمرارية الشامل الجديد...")
        replit_always_on.start()
        logger.info("✅ تم بدء نظام الاستمرارية الشامل الجديد")
    
    # 6. نظام مراقبة الاستمرارية الإضافي
    if uptime_monitor_available:
        logger.info("🚀🚀🚀 بدء نظام مراقبة الاستمرارية الجديد...")
        uptime_monitor.start()
        logger.info("✅ تم بدء نظام مراقبة الاستمرارية الجديد")
    
    # 7. تفعيل نظام التعافي التلقائي إذا كان متاحًا
    if recovery_system_available:
        logger.info("🚀 بدء نظام التعافي التلقائي...")
        start_auto_recovery()
        
        # طباعة حالة نظام التعافي للتحقق
        recovery_status = get_recovery_status()
        logger.info(f"ℹ️ حالة نظام التعافي التلقائي: {recovery_status['status']}")
    
    # بدء خيط فحص الإشارات
    start_signal_check()
    
    # تسجيل دالة التنظيف
    atexit.register(cleanup)
    
    # التعامل مع إشارات النظام
    signal.signal(signal.SIGTERM, lambda sig, frame: cleanup())
    signal.signal(signal.SIGINT, lambda sig, frame: cleanup())
    
    logger.info("✅ تم تهيئة التطبيق بنجاح")

def run_app_with_recovery():
    """تشغيل التطبيق مع آلية التعافي التلقائي من الأخطاء"""
    # تهيئة التطبيق
    initialize_app()
    
    max_retries = 5
    retry_count = 0
    retry_delay = 5  # ثوانٍ

    while retry_count < max_retries:
        try:
            # نستخدم تكوين نظام الإشارات من app.py
            logger.info("بدء تشغيل التطبيق...")
            
            # التأكد من أن نظام الإشارات يعمل
            if not signal_manager.check_signal_system_status():
                logger.warning("نظام الإشارات غير نشط، إعادة تشغيله...")
                signal_manager.restart_signal_system()
                logger.info("تم إعادة تشغيل نظام الإشارات")
            
            # تشغيل خادم الويب
            logger.info("بدء تشغيل خادم الويب...")
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
            
            # إذا وصلنا إلى هنا فالتطبيق توقف بشكل طبيعي
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"حدث خطأ عند تشغيل التطبيق (محاولة {retry_count}/{max_retries}): {e}")
            logger.exception("تفاصيل الخطأ:")
            
            # محاولة إعادة تشغيل نظام الإشارات
            try:
                logger.warning("محاولة إعادة تشغيل نظام الإشارات...")
                signal_manager.restart_signal_system()
                logger.info("تم إعادة تشغيل نظام الإشارات")
            except Exception as restart_error:
                logger.error(f"فشل إعادة تشغيل نظام الإشارات: {restart_error}")
            
            if retry_count < max_retries:
                logger.info(f"الانتظار {retry_delay} ثوانٍ قبل إعادة المحاولة...")
                time.sleep(retry_delay)
                # زيادة وقت الانتظار تدريجياً
                retry_delay = min(60, retry_delay * 2)  # الحد الأقصى للانتظار هو 60 ثانية
            else:
                logger.critical("تم استنفاد الحد الأقصى من المحاولات. فشل بدء التطبيق.")

if __name__ == '__main__':
    run_app_with_recovery()
