"""
نظام تسجيل الأخطاء المتقدم مع التكامل مع تيليجرام
يسمح بإرسال الأخطاء الحرجة إلى قناة مشرفي النظام على تيليجرام

يستخدم هذا النظام مستويات مختلفة من الأخطاء ويمكن تكوينه لإرسال بعض الأخطاء فقط.
"""

import os
import sys
import traceback
import logging
import time
import threading
from datetime import datetime
from enum import Enum

# محاولة استيراد دالة إرسال الرسائل للتيليجرام
try:
    from bot.telegram_client import send_message
except ImportError:
    try:
        # محاولة ثانية من مسار مختلف
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from bot.telegram_client import send_message
    except ImportError:
        # إنشاء دالة بديلة في حالة عدم توفر الوحدة الأصلية
        def send_message(channels, text, parse_mode="HTML"):
            logging.error(f"تعذر إرسال رسالة تيليجرام (لم يتم تحميل الوحدة): {text}")
            return False

# إنشاء مصنف خاص بمستويات الأخطاء
class ErrorSeverity(Enum):
    LOW = 1        # أخطاء غير حرجة، تسجل فقط في الملفات
    MEDIUM = 2     # أخطاء متوسطة، ترسل للمشرفين بشكل مجمع/دوري
    HIGH = 3       # أخطاء عالية الخطورة، ترسل فوراً للمشرفين
    CRITICAL = 4   # أخطاء حرجة، ترسل فوراً وتستدعي إعادة تشغيل النظام


class AdvancedErrorLogger:
    """نظام تسجيل الأخطاء المتقدم مع دعم تيليجرام"""
    
    def __init__(self, admin_channel_id=None, log_file="app.log", min_telegram_severity=ErrorSeverity.HIGH):
        """
        تهيئة نظام تسجيل الأخطاء
        
        Args:
            admin_channel_id: معرف قناة المشرفين على تيليجرام (اختياري)
            log_file: مسار ملف السجل
            min_telegram_severity: الحد الأدنى لمستوى الخطورة للإرسال لتيليجرام
        """
        self.admin_channel_id = admin_channel_id
        self.log_file = log_file
        self.min_telegram_severity = min_telegram_severity
        
        # إعداد نظام التسجيل
        self.logger = logging.getLogger("advanced_error_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # إعداد تسجيل الملفات
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # مخزن مؤقت للأخطاء المتوسطة لتجميعها
        self.medium_errors_buffer = []
        self.medium_errors_lock = threading.Lock()
        
        # بدء خيط دوري لإرسال الأخطاء المتوسطة
        self.medium_errors_thread = threading.Thread(target=self._periodic_medium_errors_sender, daemon=True)
        self.medium_errors_thread.start()
        
        self.logger.info("✅ تم تهيئة نظام تسجيل الأخطاء المتقدم")
    
    def log_error(self, error_message, severity=ErrorSeverity.MEDIUM, exception=None, context=None):
        """
        تسجيل خطأ في النظام
        
        Args:
            error_message: رسالة الخطأ
            severity: مستوى خطورة الخطأ
            exception: استثناء البايثون (اختياري)
            context: سياق الخطأ (معلومات إضافية)
            
        Returns:
            bool: نجاح العملية
        """
        # تحضير التفاصيل الكاملة
        error_details = f"🔴 خطأ: {error_message}\n"
        
        if context:
            error_details += f"📋 السياق: {context}\n"
        
        if exception:
            error_stack = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            error_details += f"⚠️ الاستثناء: {type(exception).__name__}: {str(exception)}\n"
            error_details += f"📚 التفاصيل التقنية:\n<pre>{error_stack[:500]}</pre>"
        
        # تسجيل في ملف السجل
        if severity == ErrorSeverity.LOW:
            self.logger.info(error_details)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_details)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(error_details)
        elif severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error_details)
        
        # معالجة الإرسال إلى تيليجرام
        if self.admin_channel_id and severity.value >= self.min_telegram_severity.value:
            # إذا كان مستوى الخطورة عالي أو حرج، يتم الإرسال فوراً
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                telegram_message = f"🚨 تنبيه نظام ({timestamp})\n\n{error_details}"
                return self._send_telegram_alert(telegram_message)
            # إذا كان متوسط، يضاف إلى المخزن المؤقت لإرساله لاحقاً
            elif severity == ErrorSeverity.MEDIUM:
                with self.medium_errors_lock:
                    self.medium_errors_buffer.append((datetime.now(), error_details))
                return True
        
        return True
    
    def log_exception(self, message="حدث خطأ غير متوقع", severity=ErrorSeverity.HIGH, context=None):
        """
        تسجيل الاستثناء الحالي (يستخدم مباشرة في بلوك except)
        
        Args:
            message: رسالة بسيطة تصف الخطأ
            severity: مستوى خطورة الخطأ
            context: سياق الخطأ (معلومات إضافية)
            
        Returns:
            bool: نجاح العملية
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is None:
            return self.log_error(f"{message} (لا توجد تفاصيل استثناء)", severity, None, context)
        return self.log_error(message, severity, exc_value, context)
    
    def _send_telegram_alert(self, message):
        """
        إرسال تنبيه إلى قناة تيليجرام
        
        Args:
            message: نص الرسالة
            
        Returns:
            bool: نجاح العملية
        """
        if not self.admin_channel_id:
            return False
        
        try:
            result = send_message([self.admin_channel_id], message, parse_mode="HTML")
            return result
        except Exception as e:
            self.logger.error(f"فشل إرسال تنبيه تيليجرام: {e}")
            return False
    
    def _periodic_medium_errors_sender(self):
        """خيط يرسل الأخطاء المتوسطة بشكل دوري"""
        while True:
            try:
                # فحص ما إذا كان هناك أخطاء متوسطة للإرسال
                if self.admin_channel_id:
                    with self.medium_errors_lock:
                        if self.medium_errors_buffer:
                            # تجميع الأخطاء المتوسطة في رسالة واحدة
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            message = f"📒 تقرير الأخطاء المتوسطة ({timestamp})\n\n"
                            
                            # إضافة كل خطأ (بحد أقصى 5)
                            errors_to_send = self.medium_errors_buffer[:5]
                            for idx, (error_time, error_details) in enumerate(errors_to_send, 1):
                                time_str = error_time.strftime("%H:%M:%S")
                                message += f"#{idx} ({time_str}):\n{error_details}\n\n"
                            
                            # إضافة عدد الأخطاء المتبقية إذا كان هناك أكثر من 5
                            remaining = len(self.medium_errors_buffer) - 5
                            if remaining > 0:
                                message += f"...و {remaining} أخطاء أخرى لم يتم عرضها."
                            
                            # إرسال التقرير وحذف الأخطاء المرسلة
                            if self._send_telegram_alert(message):
                                self.medium_errors_buffer = self.medium_errors_buffer[5:]
            except Exception as e:
                # تسجيل الأخطاء في الملف فقط لتجنب التكرار
                self.logger.error(f"خطأ في خيط إرسال الأخطاء المتوسطة: {e}")
            
            # انتظار لمدة 30 دقيقة قبل الإرسال التالي
            time.sleep(1800)  # 30 دقيقة
    
    def is_system_healthy(self):
        """
        التحقق من صحة النظام العامة
        
        Returns:
            bool: حالة صحة النظام
        """
        # يمكن تحسين هذه الدالة لإجراء فحوصات إضافية على صحة النظام
        return True


# إنشاء كائن عالمي لنظام تسجيل الأخطاء المتقدم (مع قناة المشرفين)
error_logger = AdvancedErrorLogger(
    admin_channel_id="@trading_elite_admin",  # استبدل بقناة المشرفين الفعلية
    min_telegram_severity=ErrorSeverity.HIGH  # إرسال الأخطاء العالية والحرجة فقط
)


# توفير دوال مساعدة للاستخدام المباشر في البرنامج
def log_error(message, severity=ErrorSeverity.MEDIUM, exception=None, context=None):
    """تسجيل خطأ في النظام"""
    return error_logger.log_error(message, severity, exception, context)


def log_exception(message="حدث خطأ غير متوقع", severity=ErrorSeverity.HIGH, context=None):
    """تسجيل الاستثناء الحالي"""
    return error_logger.log_exception(message, severity, context)


# مثال على الاستخدام
if __name__ == "__main__":
    # أمثلة للاختبار
    try:
        # إثارة خطأ للاختبار
        x = 1 / 0
    except Exception:
        log_exception("حدث خطأ أثناء العمليات الحسابية", ErrorSeverity.HIGH, "اختبار نظام تسجيل الأخطاء")
    
    # تسجيل خطأ بسيط
    log_error("اختبار تسجيل خطأ بسيط", ErrorSeverity.MEDIUM)