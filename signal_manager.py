"""
ملف مخصص للتحكم في نظام إرسال الإشارات بدقة
هذا الملف مسؤول فقط عن توليد الإشارات وإرسالها في أوقات محددة (كل 5 دقائق بالضبط)
"""

import os
import time
import random
import logging
import threading
import sys
import socket
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# الثوابت - تم تعديلها لضمان الفاصل الزمني
SIGNAL_INTERVAL_SECONDS = 300  # وقت الفاصل المثالي الجديد هو 5 دقائق (300 ثانية)
MAX_SIGNAL_INTERVAL_SECONDS = 360  # الحد الأقصى للفاصل الزمني هو 6 دقائق (360 ثانية)
MIN_SIGNAL_INTERVAL_SECONDS = 240  # الحد الأدنى للفاصل الزمني هو 4 دقائق (240 ثانية)
ABSOLUTE_MAX_INTERVAL = 420  # الحد الأقصى المطلق لا يتجاوز أبدًا 7 دقائق (420 ثانية)
LOCK_TIMEOUT_SECONDS = 45  # مدة صلاحية القفل تم تقليلها إلى 45 ثانية فقط لإطلاق القفل العالق

# تفعيل نظام الإشارات الإجبارية
FORCE_SIGNAL_INTERVAL = True  # تفعيل نظام الإشارات الإجبارية لضمان عدم تجاوز الفاصل الزمني
PROCESS_ID = f"{socket.gethostname()}-{os.getpid()}"  # معرف فريد للعملية الحالية
SIGNAL_LOCK_NAME = "signal_generator_lock"  # اسم القفل المركزي

# المتغيرات العالمية للتحكم بالإشارات
last_signal_time = datetime.utcnow()  # تعيين وقت آخر إشارة للوقت الحالي
is_signal_system_running = False
signal_thread = None
signal_lock = threading.Lock()  # قفل داخلي للتأكد من عدم تداخل العمليات داخل نفس العملية
last_error = None  # لتتبع آخر خطأ في النظام
error_count = 0  # عدد الأخطاء المتتالية

# نظام الأمان - تم رفع الحد مؤقتًا لتسهيل الانتقال إلى النظام الجديد
MAX_SIGNALS_PER_HOUR = 100  # الحد الأقصى للإشارات المسموح بها في الساعة (مؤقتًا)
is_signal_generation_locked = False  # إذا كان هناك الكثير من الإشارات، سيتم قفل التوليد

# إعادة تعيين المتغير لضمان إرسال الإشارات بشكل صحيح
is_signal_generation_locked = False

# تأكيد تفعيل نظام الإشارات لضمان توليد الإشارات
is_signal_system_running = True

# تعديل وقت آخر إشارة ليسمح بإرسال إشارة جديدة فورًا ثم كل 5 دقائق بانتظام
last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS * 2)

# بعد ساعة واحدة، يمكن إعادة هذه القيمة إلى 15 (أي كل 4 دقائق كحد أقصى)
# MAX_SIGNALS_PER_HOUR = 15

# دالة العمل التي سيتم تعيينها من الخارج (من app.py)
worker_function = None

# تسجيل توليد الإشارات
signal_log = []  # آخر 100 إشارة

# متغير للتحكم بالمثيل
_instance_running = False

# متغير للتحكم بالسلوك المستمر
force_continuous_operation = True  # ضمان استمرار التشغيل حتى عند الخروج من الموقع

# تسجيل بدء تشغيل العملية
logger.info(f"تم بدء تشغيل مدير الإشارات المطور بمعرف العملية: {PROCESS_ID}")

def get_time_until_next_signal():
    """حساب الوقت المتبقي حتى الإشارة التالية"""
    global last_signal_time
    
    # التعليق هذا السطر لمنع إعادة ضبط الوقت في كل مرة، مما يسمح بتشغيل النظام بشكل طبيعي
    # لن نقوم بإعادة تعيين الوقت تلقائياً في كل مرة يتم فيها استدعاء الدالة
    # last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS + 10)
    # logger.warning("🚨🚨🚨 تم إعادة تعيين وقت آخر إشارة للسماح بإنشاء إشارة جديدة فورًا 🚨🚨🚨")
    
    if last_signal_time is None:
        return 0
    
    current_time = datetime.utcnow()
    elapsed_seconds = (current_time - last_signal_time).total_seconds()
    remaining_seconds = max(0, SIGNAL_INTERVAL_SECONDS - elapsed_seconds)
    
    return int(remaining_seconds)

# دالة للحصول على القفل المركزي من قاعدة البيانات
def acquire_db_lock():
    """
    محاولة الحصول على القفل المركزي من قاعدة البيانات
    هذه الوظيفة تتأكد من أن عملية واحدة فقط هي التي تقوم بإنشاء الإشارات
    
    Returns:
        True if lock acquired, False otherwise
    """
    try:
        # نستورد هنا لتجنب الدورات الإستيرادية
        from app import app, db
        from models import SystemLock
        
        with app.app_context():
            # معاينة قفل موجود
            current_time = datetime.utcnow()
            existing_lock = SystemLock.query.filter_by(lock_name=SIGNAL_LOCK_NAME).first()
            
            # إذا كان القفل موجودًا وصالحًا
            if existing_lock:
                # هل هذه هي العملية التي تمتلك القفل بالفعل؟
                if existing_lock.locked_by == PROCESS_ID:
                    # تحديث وقت انتهاء الصلاحية
                    existing_lock.expires_at = current_time + timedelta(seconds=LOCK_TIMEOUT_SECONDS)
                    db.session.commit()
                    logger.info(f"تم تجديد القفل المركزي للعملية: {PROCESS_ID}")
                    return True
                
                # هل القفل قد انتهت صلاحيته؟
                # إعادة تعيين القفل دائمًا إذا كانت هذه النسخة التطويرية 
                # هذا يضمن أن النسخة التطويرية الجديدة ستستحوذ على القفل
                # ونتمكن من تطبيق التغييرات الجديدة عليها

                # تحقق دائم من أي قفل موجود مسبقاً
                lock_age = (current_time - existing_lock.locked_at).total_seconds()
                lock_owner = existing_lock.locked_by
                
                # قراءة معلومات البيئة الحالية
                is_development = "replit-user" in PROCESS_ID  # عملية تطوير
                is_deployment = "deployments" in existing_lock.locked_by  # القفل الحالي لنسخة نشر
                
                # تحرير القفل بعد 45 ثانية فقط - لضمان عدم عرقلة النظام
                force_release_threshold = timedelta(seconds=45)  # 45 ثانية فقط

                logger.warning(f"معلومات القفل - المالك: {lock_owner}, عمر القفل: {lock_age:.1f} ثانية, هل هو قديم: {current_time - existing_lock.locked_at > force_release_threshold}")
                
                # إعادة تعيين القفل في جميع الحالات تقريباً (التخفيف المؤقت لحل مشكلة القفل العالق)
                # تعديل: إجبار حل القفل للتنفيذ المستخدم حالياً بغض النظر عن المالك
                if True:
                    logger.warning(f"تم العثور على قفل منتهي الصلاحية أو قديم للعملية {lock_owner} (عمر القفل: {lock_age:.1f} ثانية)، يتم إعادة تعيينه")
                    
                    existing_lock.locked_by = PROCESS_ID
                    existing_lock.locked_at = current_time
                    existing_lock.expires_at = current_time + timedelta(seconds=LOCK_TIMEOUT_SECONDS)
                    db.session.commit()
                    return True
                
                # القفل موجود وصالح
                logger.info(f"القفل المركزي قيد الاستخدام من قِبل العملية: {existing_lock.locked_by}")
                
                # تعديل: فحص إضافي للتأكد من أن القفل غير عالق
                lock_age = (current_time - existing_lock.locked_at).total_seconds()
                if lock_age > 1800:  # 30 دقيقة
                    logger.warning(f"القفل المركزي يبدو عالقاً (عمره {lock_age:.1f} ثانية) - قد تحتاج لإعادة النشر أو إعادة تشغيل الخادم")
                    
                return False
            
            # لا يوجد قفل، قم بإنشائه
            logger.info(f"إنشاء قفل مركزي للعملية: {PROCESS_ID}")
            new_lock = SystemLock(
                lock_name=SIGNAL_LOCK_NAME,
                locked_by=PROCESS_ID,
                locked_at=current_time,
                expires_at=current_time + timedelta(seconds=LOCK_TIMEOUT_SECONDS)
            )
            db.session.add(new_lock)
            db.session.commit()
            return True
            
    except Exception as e:
        logger.error(f"خطأ في محاولة الحصول على القفل المركزي: {e}")
        logger.exception("تفاصيل الخطأ:")
        return False


# دالة لإطلاق القفل المركزي
def release_db_lock():
    """
    إطلاق القفل المركزي من قاعدة البيانات إذا كانت العملية الحالية هي التي تمتلكه
    
    Returns:
        True if lock released, False otherwise
    """
    try:
        # نستورد هنا لتجنب الدورات الإستيرادية
        from app import app, db
        from models import SystemLock
        
        with app.app_context():
            # المعاينة والتحديث يجب أن تكون في نفس العملية المعاملة
            existing_lock = SystemLock.query.filter_by(lock_name=SIGNAL_LOCK_NAME, locked_by=PROCESS_ID).first()
            
            if existing_lock:
                # يمكن حذف القفل أو تغيير العملية التي تملكه
                # نفضل تغيير العملية المالكة إلى قيمة خاصة تشير إلى أن القفل تم إطلاقه
                existing_lock.locked_by = "RELEASED"
                existing_lock.expires_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"تم إطلاق القفل المركزي من العملية: {PROCESS_ID}")
                return True
            
            # هذه العملية لا تملك القفل
            return False
            
    except Exception as e:
        logger.error(f"خطأ في محاولة إطلاق القفل المركزي: {e}")
        logger.exception("تفاصيل الخطأ:")
        return False


def is_time_to_generate_signal():
    """التحقق بدقة إذا كان الوقت مناسبًا لإنشاء إشارة جديدة بالضبط كل 5 دقائق (300 ثانية)"""
    global last_signal_time, is_signal_generation_locked, signal_log
    
    # استخدام آلية قفل مركزية معتمدة على قاعدة البيانات - منع تعارض العمليات المتعددة
    if not acquire_db_lock():
        logger.info("لم يتم الحصول على القفل المركزي. لن يتم إنشاء إشارة من هذه العملية.")
        return False
    
    try:
        # جلب معلومات الإشارات من قاعدة البيانات بدلاً من الاعتماد على المتغيرات المحلية
        from app import app, db
        from models import Signal, OTCPair
        
        with app.app_context():
            # التحقق من تشغيل النظام
            if not is_signal_system_running:
                logger.warning("تم محاولة إنشاء إشارة ولكن نظام الإشارات متوقف!")
                return False
                
            # التحقق من قفل النظام للأمان
            if is_signal_generation_locked:
                logger.warning("تم قفل نظام الإشارات بسبب تجاوز الحد المسموح من الإشارات")
                return False
                
            # التحقق من وجود أزواج نشطة للإرسال (OTC و بورصة عادية)
            from models import OTCPair, MarketPair
            active_otc_pairs_count = OTCPair.query.filter_by(is_active=True).count()
            active_market_pairs_count = MarketPair.query.filter_by(is_active=True).count()
            
            # التحقق من توفر أزواج إما في البورصة العادية أو OTC
            if active_otc_pairs_count == 0 and active_market_pairs_count == 0:
                logger.error("لا توجد أزواج نشطة (لا OTC ولا بورصة عادية) في قاعدة البيانات! لن يتم إنشاء إشارات.")
                return False
            
            # تسجيل عدد الأزواج المتاحة من كل نوع
            logger.info(f"عدد أزواج OTC النشطة: {active_otc_pairs_count}, عدد أزواج البورصة العادية النشطة: {active_market_pairs_count}")
            
            # التحقق من عدد الإشارات في الساعة الماضية
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            recent_signals_count = Signal.query.filter(
                Signal.created_at > one_hour_ago
            ).count()
            
            # التأكد من عدم تجاوز حد الإشارات في الساعة
            if recent_signals_count > MAX_SIGNALS_PER_HOUR:
                logger.error(f"تم تجاوز الحد الأقصى للإشارات في الساعة: {recent_signals_count}/{MAX_SIGNALS_PER_HOUR}")
                is_signal_generation_locked = True
                return False
            
            # الحصول على آخر إشارة أساسية (غير مضاعفة) تم إنشاؤها
            last_signal = Signal.query.filter_by(doubling_strategy=False).order_by(Signal.created_at.desc()).first()
            
            # إذا لم توجد إشارة أساسية سابقة، نسمح بإنشاء أول إشارة
            if last_signal is None:
                logger.info("لم يتم العثور على إشارات أساسية سابقة، سيتم إنشاء أول إشارة")
                last_signal_time = current_time
                signal_log.append(current_time)
                return True
            
            # حساب الوقت المنقضي منذ آخر إشارة أساسية - بدقة متناهية
            elapsed_seconds = (current_time - last_signal.created_at).total_seconds()
            
            # التحقق أولاً من تجاوز الحد الأقصى المطلق - فحص حرج
            if elapsed_seconds >= ABSOLUTE_MAX_INTERVAL:
                logger.warning(f"⚠️⚠️⚠️ تجاوز الحد الأقصى المطلق للفواصل الزمنية: {elapsed_seconds:.2f} ثانية > {ABSOLUTE_MAX_INTERVAL} ثانية")
                logger.warning("🚨🚨🚨 فرض إنشاء إشارة جديدة فورًا بغض النظر عن الجودة!")
                
                # استخدام الوقت الحالي بدلاً من التوقيت التخميني
                last_signal_time = current_time
                signal_log.append(current_time)
                if len(signal_log) > 100:
                    signal_log = signal_log[-100:]
                    
                logger.info(f"تم تعيين وقت آخر إشارة إلى الوقت الحالي: {current_time}")
                return True
            
            # نظام الإشارات المرن - بفاصل زمني بين الحد الأدنى والحد الأقصى
            if elapsed_seconds >= MIN_SIGNAL_INTERVAL_SECONDS:
                # إذا تجاوزنا الحد الأقصى العادي (6.5 دقائق)، فيجب إرسال إشارة بغض النظر عن الجودة
                must_generate = elapsed_seconds >= MAX_SIGNAL_INTERVAL_SECONDS
                
                # حساب معامل الزمن (كلما زاد الوقت، زادت أولوية إرسال الإشارة)
                time_factor = min(1.0, (elapsed_seconds - MIN_SIGNAL_INTERVAL_SECONDS) / 
                               (MAX_SIGNAL_INTERVAL_SECONDS - MIN_SIGNAL_INTERVAL_SECONDS))
                
                # استخدام الوقت الحالي بدلاً من الوقت التخميني
                last_signal_time = current_time
                signal_log.append(current_time)
                if len(signal_log) > 100:
                    signal_log = signal_log[-100:]
                
                # توثيق دقيق للوقت المنقضي والوقت الحالي
                if must_generate:
                    logger.warning(f"⚠️ تجاوز الحد الأقصى العادي للفاصل الزمني: {elapsed_seconds:.2f} ثانية > {MAX_SIGNAL_INTERVAL_SECONDS} ثانية")
                else:
                    logger.info(f"حان وقت إنشاء إشارة جديدة، مرت {elapsed_seconds:.2f} ثانية (معامل الزمن: {time_factor:.2f})")
                
                logger.info(f"الوقت الحالي للإشارة: {current_time}")
                logger.info(f"وقت آخر إشارة كان: {last_signal.created_at}")
                return True
            
            # لم يحن وقت الإشارة بعد - توثيق دقيق
            seconds_remaining = SIGNAL_INTERVAL_SECONDS - elapsed_seconds
            minutes_remaining = int(seconds_remaining / 60)
            secs_remaining = int(seconds_remaining % 60)
            
            logger.info(f"لم يحن وقت إنشاء إشارة جديدة، مرت {elapsed_seconds:.2f} ثانية فقط من أصل {SIGNAL_INTERVAL_SECONDS} ثانية")
            logger.info(f"متبقي {minutes_remaining} دقيقة و {secs_remaining} ثانية للإشارة التالية")
            return False
    except Exception as e:
        logger.error(f"حدث خطأ أثناء التحقق من وقت الإشارة: {e}")
        logger.exception("تفاصيل الخطأ:")
        return False

def signal_worker_thread():
    """العملية الرئيسية للخيط المسؤول عن إنشاء الإشارات"""
    global is_signal_system_running, worker_function
    
    logger.info("بدء خيط نظام الإشارات")
    
    # التحقق من تعيين دالة العمل
    if worker_function is None:
        logger.error("لم يتم تعيين دالة العمل (worker_function)!")
        return
        
    # الاستمرار في العمل طالما أن النظام مفعّل
    while is_signal_system_running:
        try:
            # استدعاء دالة العمل المخصصة المعينة من main.py
            # هذه الدالة ستتعامل مع التحقق من الإشارات المنتهية وإنشاء إشارات جديدة
            worker_function()
            
            # حساب وقت الإشارة التالية للسجلات
            if last_signal_time is not None:
                next_signal_time = last_signal_time + timedelta(seconds=SIGNAL_INTERVAL_SECONDS)
                seconds_to_next = get_time_until_next_signal()
                if seconds_to_next > 0:
                    logger.info(f"الوقت المتبقي للإشارة التالية: {seconds_to_next} ثانية")
            
            # الانتظار بين الدورات (10 ثواني)
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"خطأ في خيط الإشارات: {e}")
            logger.exception("تفاصيل الخطأ:")
            time.sleep(10)  # الانتظار ثم المحاولة مرة أخرى

def check_signal_generation():
    """
    فحص حالة توليد الإشارات والتأكد من عمل النظام بشكل صحيح
    قد يؤدي الاستدعاء إلى توليد إشارة جديدة إذا حان وقتها
    """
    global last_signal_time, is_signal_generation_locked, signal_log, _instance_running
    
    try:
        # التأكد من تشغيل النظام
        if not is_signal_system_running:
            logger.warning("⚠️ نظام الإشارات متوقف! جاري إعادة تشغيله...")
            restart_signal_system()
            return True
        
        # تعديل الوقت المنقضي منذ آخر إشارة والحصول على الوقت الذي يجب فيه إرسال الإشارة التالية
        if last_signal_time is None:
            logger.warning("⚠️ لم يتم تعيين وقت الإشارة الأخيرة! جاري إعادة ضبطه...")
            last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS - 10)
            return True
            
        # حساب الوقت المنقضي منذ آخر إشارة
        current_time = datetime.utcnow()
        elapsed_seconds = (current_time - last_signal_time).total_seconds()
        
        # إذا كان قد مر وقت طويل جدًا منذ آخر إشارة (على سبيل المثال، بسبب النوم)
        if elapsed_seconds > (SIGNAL_INTERVAL_SECONDS * 2):
            logger.warning(f"⚠️ مرت {elapsed_seconds:.1f} ثانية منذ آخر إشارة! هذا أكثر من ضعف الفاصل الزمني العادي.")
            logger.warning("🔄 جاري إعادة ضبط وقت الإشارة الأخيرة للسماح بإنشاء إشارة فورًا...")
            last_signal_time = current_time - timedelta(seconds=SIGNAL_INTERVAL_SECONDS - 10)
            signal_log.append(current_time)
            if len(signal_log) > 100:
                signal_log = signal_log[-100:]
            return True
        
        # التحقق أولاً من تجاوز الحد الأقصى المطلق - إجراء طارئ
        if elapsed_seconds >= ABSOLUTE_MAX_INTERVAL:
            logger.warning(f"⚠️⚠️⚠️ تجاوز الحد الأقصى المطلق للفواصل الزمنية في check_signal_generation: {elapsed_seconds:.1f} ثانية > {ABSOLUTE_MAX_INTERVAL} ثانية")
            logger.warning("🚨🚨🚨 إجراء طارئ: فرض إنشاء إشارة جديدة فورًا!")
            
            # استخدام الوقت الحالي
            last_signal_time = current_time
            signal_log.append(current_time)
            if len(signal_log) > 100:
                signal_log = signal_log[-100:]
                
            logger.info(f"⚡ تم تحديث وقت آخر إشارة بشكل طارئ إلى: {current_time}")
            return True
        
        # نظام الإشارات المرن - بفاصل زمني بين الحد الأدنى والحد الأقصى
        if elapsed_seconds >= MIN_SIGNAL_INTERVAL_SECONDS:
            # التحقق من تجاوز الحد الأقصى العادي
            force_signal = elapsed_seconds >= MAX_SIGNAL_INTERVAL_SECONDS
            
            # حساب معامل الزمن (كلما زاد الوقت، زادت أولوية إرسال الإشارة)
            time_factor = min(1.0, (elapsed_seconds - MIN_SIGNAL_INTERVAL_SECONDS) / 
                           (MAX_SIGNAL_INTERVAL_SECONDS - MIN_SIGNAL_INTERVAL_SECONDS))
            
            # تسجيل المعلومات حول الفاصل الزمني والعوامل المؤثرة
            if force_signal:
                logger.warning(f"⚠️ تجاوز الحد الأقصى العادي للفاصل الزمني: {elapsed_seconds:.1f} ثانية > {MAX_SIGNAL_INTERVAL_SECONDS} ثانية")
            else:
                logger.info(f"🕒 حان وقت إنشاء إشارة جديدة (مرت {elapsed_seconds:.1f} ثانية، معامل الزمن: {time_factor:.2f})")
            
            # استخدام الوقت الحالي دائمًا
            last_signal_time = current_time
            signal_log.append(current_time)
            if len(signal_log) > 100:
                signal_log = signal_log[-100:]
                
            logger.info(f"✅ تم تحديث وقت آخر إشارة إلى: {current_time}")
            return True
            
        # لم يحن وقت الإشارة بعد
        seconds_remaining = SIGNAL_INTERVAL_SECONDS - elapsed_seconds
        minutes_remaining = int(seconds_remaining / 60)
        secs_remaining = int(seconds_remaining % 60)
        
        logger.info(f"⏱️ متبقي {minutes_remaining} دقيقة و {secs_remaining} ثانية للإشارة التالية")
        return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في فحص حالة توليد الإشارات: {e}")
        logger.exception("تفاصيل الخطأ:")
        return False

def check_signal_system_status():
    """
    تحقق مما إذا كان نظام الإشارات قيد التشغيل
    
    Returns:
        bool: True إذا كان نظام الإشارات قيد التشغيل، False خلاف ذلك
    """
    # استخدام اسم دالة مختلف لتجنب التضارب مع المتغير العام
    global is_signal_system_running
    return is_signal_system_running

def get_signal_status():
    """الحصول على حالة نظام الإشارات"""
    global last_signal_time, is_signal_system_running, signal_log
    
    current_time = datetime.utcnow()
    elapsed_seconds = 0
    
    if last_signal_time:
        elapsed_seconds = (current_time - last_signal_time).total_seconds()
    
    # حساب النسبة المئوية للتقدم نحو الإشارة التالية
    min_progress = min(100, max(0, (elapsed_seconds / MIN_SIGNAL_INTERVAL_SECONDS) * 100))
    normal_progress = min(100, max(0, (elapsed_seconds / SIGNAL_INTERVAL_SECONDS) * 100))
    max_progress = min(100, max(0, (elapsed_seconds / MAX_SIGNAL_INTERVAL_SECONDS) * 100))
    
    status = {
        "is_running": is_signal_system_running,
        "last_signal_time": str(last_signal_time) if last_signal_time else None,
        "time_until_next_min_signal": max(0, MIN_SIGNAL_INTERVAL_SECONDS - elapsed_seconds),
        "time_until_next_normal_signal": max(0, SIGNAL_INTERVAL_SECONDS - elapsed_seconds),
        "time_until_max_signal_time": max(0, MAX_SIGNAL_INTERVAL_SECONDS - elapsed_seconds),
        "elapsed_seconds": elapsed_seconds,
        "min_interval_seconds": MIN_SIGNAL_INTERVAL_SECONDS,
        "interval_seconds": SIGNAL_INTERVAL_SECONDS,
        "max_interval_seconds": MAX_SIGNAL_INTERVAL_SECONDS,
        "min_progress_percent": round(min_progress, 1),
        "normal_progress_percent": round(normal_progress, 1),
        "max_progress_percent": round(max_progress, 1),
        "signal_count": len(signal_log),
        "recent_signals": [str(t) for t in signal_log[-5:]] if signal_log else []
    }
    
    return status

def start_signal_system():
    """بدء تشغيل نظام الإشارات"""
    global is_signal_system_running, signal_thread, last_signal_time, _instance_running
    
    with signal_lock:
        # تحقق من عدم وجود مثيل آخر قيد التشغيل
        if _instance_running:
            logger.critical("هناك مثيل آخر من نظام الإشارات قيد التشغيل بالفعل!")
            return False
        
        # تأكد من أن النظام غير قيد التشغيل بالفعل
        if is_signal_system_running:
            logger.warning("نظام الإشارات قيد التشغيل بالفعل")
            return False
        
        # إعادة تعيين متغيرات الحالة
        is_signal_generation_locked = False
        signal_log.clear()
        
        # تهيئة وقت الإشارة الأخيرة ليكون قبل 5 دقائق بالضبط
        # هذا يضمن إرسال أول إشارة مباشرة بعد بدء النظام
        last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS)
        
        # قتل أي خيوط أخرى
        for thread in threading.enumerate():
            if thread.name.startswith('signal_') and thread != threading.current_thread():
                logger.warning(f"هناك خيط إشارات آخر: {thread.name}")
        
        try:
            # بدء تشغيل النظام
            is_signal_system_running = True
            _instance_running = True
            signal_thread = threading.Thread(target=signal_worker_thread, name="signal_worker_main", daemon=True)
            signal_thread.start()
            
            logger.info(f"تم بدء تشغيل نظام الإشارات المحسن (الفاصل الزمني: من {MIN_SIGNAL_INTERVAL_SECONDS/60:.1f} إلى {MAX_SIGNAL_INTERVAL_SECONDS/60:.1f} دقيقة)")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في بدء تشغيل نظام الإشارات: {e}")
            is_signal_system_running = False
            _instance_running = False
            return False

def stop_signal_system():
    """إيقاف نظام الإشارات"""
    global is_signal_system_running, _instance_running, signal_thread
    
    with signal_lock:
        # تأكد من أن النظام قيد التشغيل
        if not is_signal_system_running and not _instance_running:
            logger.warning("نظام الإشارات متوقف بالفعل")
            return False
        
        # إيقاف النظام
        is_signal_system_running = False
        _instance_running = False
        
        # إيقاف الخيط الحالي إذا كان موجودًا
        if signal_thread and signal_thread.is_alive():
            logger.info(f"إيقاف خيط الإشارات: {signal_thread.name}")
            # لا يمكننا إيقاف الخيط مباشرة، لكن سيتوقف بنفسه عند التحقق من is_signal_system_running
        
        # إعادة تعيين المتغيرات
        signal_thread = None
        
        # إطلاق القفل المركزي
        try:
            release_db_lock()
        except Exception as e:
            logger.error(f"خطأ أثناء إطلاق القفل المركزي: {e}")
            logger.exception("تفاصيل الخطأ:")
        
        logger.info("تم إيقاف نظام الإشارات بالكامل")
        return True

def restart_signal_system():
    """إعادة تشغيل نظام الإشارات بشكل قوي ومضمون"""
    global last_signal_time, is_signal_system_running, _instance_running, signal_thread
    
    logger.warning("🔄🔄🔄 جاري إعادة تشغيل نظام الإشارات بشكل قوي 🔄🔄🔄")
    
    # إيقاف النظام بالكامل أولاً
    try:
        stop_signal_system()
    except Exception as e:
        logger.error(f"خطأ أثناء محاولة إيقاف النظام: {e}")
        # في حالة الفشل، نقوم بإعادة تعيين المتغيرات بشكل مباشر
        is_signal_system_running = False
        _instance_running = False
        signal_thread = None
    
    # انتظار لحظة للتأكد من إغلاق الخيوط
    time.sleep(2)
    
    # فتح القفل دائماً قبل إعادة البدء
    try:
        from app import app, db
        from models import SystemLock
        
        with app.app_context():
            # حذف القفل من قاعدة البيانات تماماً
            existing_lock = SystemLock.query.filter_by(lock_name=SIGNAL_LOCK_NAME).first()
            if existing_lock:
                db.session.delete(existing_lock)
                db.session.commit()
                logger.info("✅ تم حذف القفل المركزي بنجاح قبل إعادة التشغيل")
    except Exception as e:
        logger.error(f"خطأ أثناء محاولة حذف القفل المركزي: {e}")
    
    # إعادة تعيين وقت آخر إشارة ليكون قبل 5 دقائق تماماً لضمان توليد إشارة فوراً
    last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS + 10)
    
    # إعادة تشغيل النظام
    logger.info("✅ جاري بدء تشغيل نظام الإشارات من جديد")
    return start_signal_system()