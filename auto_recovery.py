"""
نظام التعافي التلقائي من الأخطاء الحرجة
يراقب حالة الخدمة ويقوم بإعادة تشغيلها تلقائيًا عند حدوث مشاكل

يعمل هذا النظام بشكل منفصل لضمان استمرارية الخدمة حتى في حالة تعطل النظام الرئيسي
"""

import os
import sys
import time
import logging
import threading
import subprocess
import signal
import requests
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_recovery.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_recovery")

# محاولة استيراد نظام تسجيل الأخطاء المتقدم
try:
    from advanced_error_logger import log_error, ErrorSeverity
except ImportError:
    # إنشاء دوال بديلة في حالة عدم توفر النظام المتقدم
    def log_error(message, severity=None, exception=None, context=None):
        logger.error(message)
    
    class ErrorSeverity:
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        CRITICAL = 4


class AutoRecoverySystem:
    """نظام التعافي التلقائي من الأخطاء الحرجة"""
    
    def __init__(self, service_name="Trading Elite Pro", check_interval=180):
        """
        تهيئة نظام التعافي التلقائي
        
        Args:
            service_name: اسم الخدمة للعرض في السجلات
            check_interval: الفاصل الزمني بين عمليات الفحص (بالثواني) - تم تقليله إلى 3 دقائق
        """
        self.service_name = service_name
        self.check_interval = check_interval
        self.monitoring_thread = None
        self.signal_monitoring_thread = None  # خيط جديد لمراقبة الإشارات
        self.recovery_stats = {
            "start_time": datetime.now(),
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "signal_checks": 0,
            "signal_failures": 0,
            "signal_recoveries": 0
        }
        self.running = False
        self.consecutive_failures = 0
        self.max_consecutive_failures = 2  # تم تقليله لسرعة الاستجابة
        self.signal_failure_threshold = 4  # عدد دقائق عدم وجود إشارات قبل اعتبارها فشلًا
        
        # مؤشر لمعرفة ما إذا كان النظام في مرحلة التعافي
        self.is_recovering = False
        
        # وقت آخر إشارة تم إرسالها بنجاح
        self.last_signal_time = None
        
        logger.info(f"✅ تم تهيئة نظام التعافي التلقائي لخدمة {service_name}")
    
    def start_monitoring(self):
        """بدء مراقبة الخدمة"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("نظام المراقبة قيد التشغيل بالفعل")
            return False
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # بدء مراقبة الإشارات
        self.signal_monitoring_thread = threading.Thread(target=self._signal_monitoring_loop, daemon=True)
        self.signal_monitoring_thread.start()
        
        logger.info("✅ تم بدء نظام المراقبة والتعافي التلقائي")
        return True
    
    def stop_monitoring(self):
        """إيقاف المراقبة"""
        if not self.running:
            logger.warning("نظام المراقبة متوقف بالفعل")
            return False
        
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.signal_monitoring_thread:
            self.signal_monitoring_thread.join(timeout=5)
        
        logger.info("⛔ تم إيقاف نظام المراقبة والتعافي التلقائي")
        return True
        
    def _signal_monitoring_loop(self):
        """حلقة مراقبة الإشارات"""
        logger.info("🔄 بدء حلقة مراقبة الإشارات")
        
        # حاول تحديد آخر وقت للإشارة من قاعدة البيانات
        try:
            # نحاول الحصول على آخر إشارة من واجهة الـ API
            response = requests.get("http://localhost:5000/signal_status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'last_signal_time' in data:
                    self.last_signal_time = datetime.fromisoformat(data['last_signal_time'])
                    logger.info(f"✅ تم العثور على آخر إشارة بتاريخ: {self.last_signal_time}")
        except Exception as e:
            logger.warning(f"⚠️ لم يتم العثور على آخر إشارة: {e}")
            # إذا لم يتم العثور على إشارات، نفترض أن آخر إشارة كانت الآن
            self.last_signal_time = datetime.now()
        
        while self.running:
            try:
                self.recovery_stats["signal_checks"] += 1
                now = datetime.now()
                
                # إذا لم يكن هناك سجل لآخر إشارة، قم بتعيينه الآن
                if not self.last_signal_time:
                    self.last_signal_time = now
                
                # حساب الوقت منذ آخر إشارة
                time_since_last_signal = (now - self.last_signal_time).total_seconds() / 60  # بالدقائق
                
                # إذا تجاوزت المدة الحد الأقصى، محاولة استعادة نظام الإشارات
                if time_since_last_signal > self.signal_failure_threshold:
                    logger.warning(f"⚠️ لم يتم إرسال إشارات منذ {time_since_last_signal:.2f} دقائق (أكثر من الحد {self.signal_failure_threshold})")
                    self.recovery_stats["signal_failures"] += 1
                    self._recover_signal_system()
                else:
                    logger.debug(f"✅ آخر إشارة منذ {time_since_last_signal:.2f} دقائق (أقل من الحد {self.signal_failure_threshold})")
                
                # تحديث آخر وقت للإشارة من واجهة الـ API
                try:
                    response = requests.get("http://localhost:5000/signal_status", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if 'last_signal_time' in data:
                            new_last_signal = datetime.fromisoformat(data['last_signal_time'])
                            if not self.last_signal_time or new_last_signal > self.last_signal_time:
                                self.last_signal_time = new_last_signal
                                logger.debug(f"✅ تم تحديث آخر وقت للإشارة: {self.last_signal_time}")
                except Exception as e:
                    logger.debug(f"⚠️ تعذر تحديث آخر وقت للإشارة: {e}")
                
                # انتظار دقيقة واحدة قبل الفحص التالي
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"⚠️ حدث خطأ في حلقة مراقبة الإشارات: {e}")
                log_error("خطأ في حلقة مراقبة الإشارات", ErrorSeverity.HIGH, e, "auto_recovery")
                time.sleep(60)  # انتظار قصير قبل المحاولة مرة أخرى
                
    def _recover_signal_system(self):
        """محاولة استعادة نظام الإشارات"""
        if self.is_recovering:
            logger.warning("نظام التعافي قيد التنفيذ بالفعل، تخطي محاولة استعادة نظام الإشارات")
            return False
        
        self.is_recovering = True
        self.recovery_stats["signal_recoveries"] += 1
        
        try:
            logger.warning("🔄 بدء محاولة استعادة نظام الإشارات")
            log_error("توقف نظام الإشارات عن العمل بشكل صحيح. محاولة التعافي.", ErrorSeverity.HIGH)
            
            # 1. محاولة إرسال إشارة مباشرة عبر API
            try:
                force_signal_response = requests.get("http://localhost:5000/api/signals/force", timeout=10)
                if force_signal_response.status_code == 200:
                    logger.info("✅ تم إرسال إشارة إجبارية بنجاح")
                    self.last_signal_time = datetime.now()
                    self.is_recovering = False
                    return True
            except Exception as e:
                logger.error(f"⚠️ فشل في إرسال إشارة إجبارية: {e}")
            
            # 2. محاولة إنشاء إشارة طوارئ مباشرة
            try:
                logger.warning("🚨 فشل في إرسال إشارة إجبارية، محاولة إنشاء إشارة طوارئ...")
                
                # استيراد مولد إشارات الطوارئ
                import sys
                from os.path import dirname, abspath
                sys.path.insert(0, dirname(dirname(abspath(__file__))))
                
                # استخدام مولد إشارات الطوارئ
                try:
                    from bot.emergency_signal_generator import generate_emergency_signal_for_auto_recovery
                    if generate_emergency_signal_for_auto_recovery():
                        logger.info("✅ تم إنشاء إشارة طوارئ بنجاح")
                        self.last_signal_time = datetime.now()
                        self.is_recovering = False
                        return True
                    else:
                        logger.error("❌ فشل في إنشاء إشارة الطوارئ")
                except ImportError as ie:
                    logger.error(f"❌ لم يتم العثور على مولد إشارات الطوارئ: {ie}")
                except Exception as ee:
                    logger.error(f"❌ خطأ أثناء إنشاء إشارة الطوارئ: {ee}")
            except Exception as e:
                logger.error(f"⚠️ فشل في تنفيذ قسم إشارات الطوارئ: {e}")
            
            # 3. إذا فشلت المحاولات السابقة، قم بإعادة تشغيل النظام
            logger.warning("⚠️ فشلت كل المحاولات، محاولة إعادة تشغيل النظام")
            self._attempt_recovery()
            
            # تحديث وقت آخر إشارة على أي حال لتجنب محاولات متكررة
            self.last_signal_time = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"⚠️ خطأ أثناء محاولة استعادة نظام الإشارات: {e}")
            log_error("خطأ في استعادة نظام الإشارات", ErrorSeverity.CRITICAL, e, "auto_recovery")
            return False
            
        finally:
            self.is_recovering = False
    
    def _monitoring_loop(self):
        """حلقة المراقبة الرئيسية"""
        logger.info("🔄 بدء حلقة المراقبة")
        
        while self.running:
            try:
                self.recovery_stats["total_checks"] += 1
                
                # فحص صحة الخدمة
                if self._check_service_health():
                    self.recovery_stats["successful_checks"] += 1
                    self.consecutive_failures = 0
                    logger.debug("✅ الخدمة تعمل بشكل طبيعي")
                else:
                    self.recovery_stats["failed_checks"] += 1
                    self.consecutive_failures += 1
                    logger.warning(f"⚠️ فشل فحص صحة الخدمة (محاولة #{self.consecutive_failures})")
                    
                    # إذا تجاوز عدد الفشل المتتالي الحد الأقصى، محاولة التعافي
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        log_error(
                            f"تجاوز عدد محاولات الفشل الحد الأقصى ({self.consecutive_failures}). محاولة التعافي التلقائي.",
                            ErrorSeverity.HIGH, 
                            context=f"Last check time: {datetime.now()}"
                        )
                        self._attempt_recovery()
                
                # انتظار حتى الفحص التالي
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"⚠️ حدث خطأ في حلقة المراقبة: {e}")
                log_error("خطأ في حلقة المراقبة الرئيسية", ErrorSeverity.HIGH, e, "auto_recovery")
                time.sleep(60)  # انتظار قصير قبل المحاولة مرة أخرى
    
    def _check_service_health(self):
        """
        فحص صحة الخدمة
        
        Returns:
            bool: ما إذا كانت الخدمة تعمل بشكل صحيح
        """
        try:
            # 1. فحص نقطة النهاية الصحية للتطبيق (إذا كانت متاحة)
            try:
                health_response = requests.get("http://localhost:5000/ping", timeout=5)
                if health_response.status_code == 200:
                    return True
            except:
                # فشل فحص نقطة النهاية الصحية، الانتقال إلى الاختبارات الأخرى
                pass
            
            # 2. فحص ما إذا كانت توجد عمليات Flask أو Gunicorn قيد التشغيل
            ps_output = subprocess.check_output(["ps", "aux"], universal_newlines=True)
            if "gunicorn" in ps_output or "python" in ps_output and ("main.py" in ps_output or "app.py" in ps_output):
                # في حالة وجود عملية ولكن لم تستجب لفحص صحة API
                # قد تكون الخدمة متوقفة مؤقتًا أو تعمل ببطء، لذا نحتاج إلى مزيد من المعلومات
                # فحص المنافذ المفتوحة
                port_check = subprocess.check_output(["netstat", "-tuln"], universal_newlines=True)
                if ":5000" in port_check:
                    # الخدمة تستمع على المنفذ 5000 ولكن لا تستجيب
                    logger.warning("الخدمة تستمع على المنفذ 5000 ولكنها لا تستجيب لطلبات API")
                    return False
                else:
                    # العملية موجودة ولكن لا تستمع على أي منفذ
                    logger.warning("تم العثور على عملية الخدمة ولكنها لا تستمع على المنفذ 5000")
                    return False
            
            # 3. لم يتم العثور على أي عملية، الخدمة متوقفة
            logger.error("لم يتم العثور على أي عملية للخدمة")
            return False
            
        except Exception as e:
            logger.error(f"⚠️ خطأ أثناء فحص صحة الخدمة: {e}")
            return False
    
    def _attempt_recovery(self):
        """محاولة استعادة الخدمة"""
        if self.is_recovering:
            logger.warning("نظام التعافي قيد التنفيذ بالفعل، تخطي محاولة التعافي الجديدة")
            return False
        
        self.is_recovering = True
        self.recovery_stats["recovery_attempts"] += 1
        
        try:
            logger.warning("🔄 بدء محاولة التعافي التلقائي")
            
            # 1. محاولة إنهاء أي عمليات متعلقة بالخدمة
            try:
                # البحث عن عمليات Flask أو Gunicorn أو Python مرتبطة بالتطبيق
                ps_result = subprocess.check_output(
                    "ps aux | grep -E 'gunicorn|main.py|app.py' | grep -v grep | awk '{print $2}'",
                    shell=True, universal_newlines=True
                ).strip()
                
                # إنهاء العمليات إذا وجدت
                if ps_result:
                    for pid in ps_result.split('\n'):
                        if pid:
                            try:
                                pid = int(pid)
                                os.kill(pid, signal.SIGTERM)
                                logger.info(f"تم إنهاء العملية {pid}")
                            except:
                                # في حالة فشل SIGTERM، استخدام SIGKILL
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                    logger.info(f"تم إجبار إنهاء العملية {pid}")
                                except:
                                    logger.warning(f"تعذر إنهاء العملية {pid}")
            except Exception as e:
                logger.error(f"⚠️ خطأ أثناء محاولة إنهاء العمليات: {e}")
            
            # 2. إعادة تشغيل الخدمة
            try:
                # تحديد أمر إعادة التشغيل المناسب
                restart_command = "cd /home/runner/workspace && gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app"
                
                subprocess.Popen(
                    restart_command, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    start_new_session=True
                )
                
                logger.info("تم إرسال أمر إعادة تشغيل الخدمة")
                
                # انتظار لمدة 10 ثوانٍ للتحقق من نجاح إعادة التشغيل
                time.sleep(10)
                
                # التحقق مما إذا تم تشغيل الخدمة بنجاح
                if self._check_service_health():
                    self.recovery_stats["successful_recoveries"] += 1
                    self.consecutive_failures = 0
                    logger.info("✅ تم استعادة الخدمة بنجاح")
                    log_error("تم استعادة الخدمة بنجاح بعد الفشل", ErrorSeverity.MEDIUM, context="auto_recovery")
                    return True
                else:
                    logger.error("❌ فشلت محاولة استعادة الخدمة")
                    log_error("فشلت محاولة استعادة الخدمة", ErrorSeverity.CRITICAL, context="auto_recovery")
                    return False
                
            except Exception as e:
                logger.error(f"⚠️ خطأ أثناء محاولة إعادة تشغيل الخدمة: {e}")
                log_error("خطأ أثناء محاولة التعافي", ErrorSeverity.CRITICAL, e, "auto_recovery")
                return False
                
        finally:
            self.is_recovering = False
    
    def get_status(self):
        """
        الحصول على حالة نظام التعافي
        
        Returns:
            dict: معلومات حالة نظام التعافي
        """
        uptime = datetime.now() - self.recovery_stats["start_time"]
        uptime_hours = uptime.total_seconds() / 3600
        
        success_rate = 0
        if self.recovery_stats["total_checks"] > 0:
            success_rate = (self.recovery_stats["successful_checks"] / self.recovery_stats["total_checks"]) * 100
        
        recovery_success_rate = 0
        if self.recovery_stats["recovery_attempts"] > 0:
            recovery_success_rate = (self.recovery_stats["successful_recoveries"] / self.recovery_stats["recovery_attempts"]) * 100
        
        return {
            "status": "running" if self.running else "stopped",
            "uptime_hours": round(uptime_hours, 2),
            "total_checks": self.recovery_stats["total_checks"],
            "success_rate": round(success_rate, 2),
            "recovery_attempts": self.recovery_stats["recovery_attempts"],
            "recovery_success_rate": round(recovery_success_rate, 2),
            "consecutive_failures": self.consecutive_failures,
            "is_currently_recovering": self.is_recovering
        }


# إنشاء كائن عالمي لنظام التعافي التلقائي
recovery_system = AutoRecoverySystem(check_interval=300)  # فحص كل 5 دقائق


# دوال مساعدة للاستخدام المباشر في البرنامج
def start_auto_recovery():
    """بدء نظام التعافي التلقائي"""
    return recovery_system.start_monitoring()


def stop_auto_recovery():
    """إيقاف نظام التعافي التلقائي"""
    return recovery_system.stop_monitoring()


def get_recovery_status():
    """الحصول على حالة نظام التعافي التلقائي"""
    return recovery_system.get_status()


# عند تشغيل الملف مباشرة
if __name__ == "__main__":
    logger.info("⚡ بدء تشغيل نظام التعافي التلقائي")
    start_auto_recovery()
    
    try:
        # الحفاظ على تشغيل البرنامج
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("⛔ تم إيقاف نظام التعافي التلقائي")
        stop_auto_recovery()