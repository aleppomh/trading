"""
نظام الإشارات المتكامل
يدمج جميع الأنظمة المتقدمة لإنشاء إشارات عالية الدقة
"""
import logging
import math
import random
import time
from datetime import datetime, timedelta

from technical_analyzer import TechnicalAnalyzer
from multi_timeframe_analyzer import validate_signal, get_trading_recommendation
from signal_filter import get_high_quality_signal, generate_safe_signal
from confidence_evaluator import enhance_signal_with_confidence
from advanced_signal_generator import get_premium_signal
from market_condition_analyzer import analyze_market_condition, should_stop_trading, get_market_warning_message
from pocket_option_otc_pairs import get_all_valid_pairs, is_valid_pair, MIN_ACCEPTABLE_PAYOUT as OTC_MIN_ACCEPTABLE_PAYOUT
from market_pairs import MIN_ACCEPTABLE_PAYOUT as MARKET_MIN_ACCEPTABLE_PAYOUT

# إعداد سجل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedSignalSystem:
    """نظام متكامل لإنشاء إشارات عالية الدقة وإدارتها"""
    
    def __init__(self):
        """تهيئة نظام الإشارات المتكامل"""
        # استخدام كافة أنظمة التحليل والتوليد المتاحة
        self.technical_analyzer = TechnicalAnalyzer()
        
        # إعدادات النظام
        self.signal_interval_minutes = 6  # الفاصل الزمني بين الإشارات
        self.entry_buffer_minutes = 3     # الفاصل الزمني بين إنشاء الإشارة ووقت الدخول
        self.min_signal_quality = 92      # الحد الأدنى لجودة الإشارة
        
        # إحصائيات النظام
        self.signals_generated = 0
        self.last_signal_time = None
        self.last_signal_quality = 0
    
    def generate_signal(self, force_generation=False):
        """
        إنشاء إشارة جديدة باستخدام كافة الأنظمة المتقدمة
        
        Args:
            force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
            
        Returns:
            dict: معلومات الإشارة، أو None في حالة عدم إنشاء إشارة
        """
        # تحديد الأولويات: البحث أولاً عن زوج من البورصة العادية قبل البحث عن أزواج OTC
        logger.info("محاولة العثور على زوج قابل للتداول من البورصة العادية أولاً...")
        
        # جلب الأزواج من البورصة العادية
        from market_pairs import get_tradable_pairs_with_good_payout as get_market_tradable_pairs
        market_pairs = get_market_tradable_pairs()
        
        # طباعة السجلات للتحقق
        logger.info(f"عدد أزواج البورصة العادية المتاحة: {len(market_pairs)}")
        if market_pairs:
            logger.info(f"أزواج البورصة المتاحة: {', '.join(market_pairs[:10])}...")
            
            # تفضيل استخدام أزواج البورصة العادية أولاً
            # لكن السماح باستخدام أزواج OTC في حالة عدم وجود إشارات جيدة من البورصة العادية
            use_market_pairs = True  # نحاول أزواج البورصة العادية أولاً
            
            if use_market_pairs:
                # لزيادة العشوائية، نخلط قائمة الأزواج قبل الاختيار
                random.shuffle(market_pairs)
                
                # اختيار حتى 3 أزواج بشكل عشوائي ومحاولة إنشاء إشارة لكل منها حتى ننجح
                selected_pairs = market_pairs[:min(3, len(market_pairs))]
                logger.info(f"سيتم محاولة إنشاء إشارة لهذه الأزواج: {', '.join(selected_pairs)}")
                
                for selected_pair in selected_pairs:
                    logger.info(f"محاولة إنشاء إشارة للزوج: {selected_pair}")
                    
                    # التحقق من نسبة العائد مرة أخرى - استخدام 85% كحد أدنى للتحسين
                    from market_pairs import get_pair_payout_rate, MIN_ACCEPTABLE_PAYOUT as MARKET_MIN_PAYOUT
                    payout = get_pair_payout_rate(selected_pair)
                    
                    if payout < MARKET_MIN_PAYOUT:
                        logger.warning(f"تم تخطي الزوج {selected_pair} بسبب نسبة العائد المنخفضة ({payout}% < {MARKET_MIN_PAYOUT}%)")
                        continue
                    
                    # محاولة إنشاء إشارة لهذا الزوج
                    signal = get_premium_signal(pair_symbol=selected_pair, force_generation=force_generation)
                    if signal:
                        logger.info(f"تم إنشاء إشارة ناجحة لزوج البورصة العادية: {selected_pair} (العائد: {payout}%)")
                        return self._adjust_entry_time(signal)
                    else:
                        logger.info(f"فشل في إنشاء إشارة لزوج البورصة العادية: {selected_pair}")
                
                logger.warning("فشلت جميع محاولات إنشاء إشارة لأزواج البورصة العادية المختارة")
            else:
                logger.info("تم تخطي أزواج البورصة العادية عمداً في هذه الدورة (10% احتمالية)")
                
        # إذا لم ننجح في إنشاء إشارة من البورصة العادية، سنحاول استخدام أزواج OTC
        logger.warning("لم ننجح في إنشاء إشارة لأزواج البورصة العادية، سنحاول الآن استخدام أزواج OTC")
        
        # جلب أزواج OTC المتاحة للتداول
        try:
            from pocket_option_otc_pairs import get_tradable_pairs_with_good_payout as get_otc_tradable_pairs
            otc_pairs = get_otc_tradable_pairs()
            
            logger.info(f"عدد أزواج OTC المتاحة: {len(otc_pairs)}")
            if otc_pairs:
                logger.info(f"أزواج OTC المتاحة: {', '.join(otc_pairs[:10])}...")
                
                # لزيادة العشوائية، نخلط قائمة الأزواج قبل الاختيار
                random.shuffle(otc_pairs)
                
                # اختيار حتى 3 أزواج بشكل عشوائي ومحاولة إنشاء إشارة لكل منها حتى ننجح
                selected_pairs = otc_pairs[:min(3, len(otc_pairs))]
                logger.info(f"سيتم محاولة إنشاء إشارة لهذه الأزواج OTC: {', '.join(selected_pairs)}")
                
                for selected_pair in selected_pairs:
                    logger.info(f"محاولة إنشاء إشارة للزوج OTC: {selected_pair}")
                    
                    # التحقق من نسبة العائد مرة أخرى - استخدام 85% كحد أدنى للتحسين
                    from pocket_option_otc_pairs import get_pair_payout_rate, MIN_ACCEPTABLE_PAYOUT as OTC_MIN_PAYOUT
                    payout = get_pair_payout_rate(selected_pair)
                    
                    if payout < OTC_MIN_PAYOUT:
                        logger.warning(f"تم تخطي الزوج OTC {selected_pair} بسبب نسبة العائد المنخفضة ({payout}% < {OTC_MIN_PAYOUT}%)")
                        continue
                    
                    # محاولة إنشاء إشارة لهذا الزوج
                    signal = get_premium_signal(pair_symbol=selected_pair, force_generation=force_generation)
                    if signal:
                        # إضافة علامة تمييز أن هذه إشارة OTC
                        signal['is_otc'] = True
                        logger.info(f"تم إنشاء إشارة ناجحة لزوج OTC: {selected_pair} (العائد: {payout}%)")
                        return self._adjust_entry_time(signal)
                    else:
                        logger.info(f"فشل في إنشاء إشارة لزوج OTC: {selected_pair}")
                
                logger.warning("فشلت جميع محاولات إنشاء إشارة لأزواج OTC المختارة")
            else:
                logger.warning("لا توجد أزواج OTC متاحة للتداول حالياً")
                
        except Exception as e:
            logger.error(f"حدث خطأ أثناء محاولة إنشاء إشارة لأزواج OTC: {e}")
            
        return None
        
        # التحقق من الفاصل الزمني المناسب بين الإشارات
        current_time = datetime.now()
        
        if self.last_signal_time and not force_generation:
            time_since_last = (current_time - self.last_signal_time).total_seconds() / 60
            if time_since_last < self.signal_interval_minutes:
                remaining = self.signal_interval_minutes - time_since_last
                logger.info(f"Signal generation skipped: only {time_since_last:.1f} minutes since last signal, need {remaining:.1f} more minutes")
                return None
        
        # التحقق من حالة السوق
        if not force_generation and should_stop_trading():
            warning_message = get_market_warning_message()
            logger.warning(f"Signal generation stopped due to poor market conditions")
            
            # إذا كان هناك تحذير جديد، إرجاع معلومات التحذير
            if warning_message:
                return {
                    'type': 'market_warning',
                    'warning_message': warning_message,
                    'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                }
            return None
        
        # الحصول على إشارة ممتازة (كان يستخدم مع OTC في الأصل)
        # signal = get_premium_signal(force_generation=force_generation)
        
        # هذا القسم لن يتم تنفيذه أبداً بعد التعديلات السابقة
        # ولكن تم الحفاظ عليه للتوافق مع بقية الشيفرة
        if not signal:
            logger.info("Failed to generate a high-quality signal")
            return None
        
        # تعديل وقت الدخول ليكون بعد الوقت الحالي
        signal = self._adjust_entry_time(signal)
        
        # تحديث الإحصائيات
        self.signals_generated += 1
        self.last_signal_time = current_time
        self.last_signal_quality = signal.get('probability', 0)
        
        return signal
    
    def _adjust_entry_time(self, signal):
        """
        تعديل وقت الدخول ليكون بعد الوقت الحالي بفاصل زمني مناسب
        مع التحقق من صحة الإشارة نسبة لمناطق الدعم والمقاومة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            dict: الإشارة مع وقت دخول معدل، أو None إذا كانت الإشارة خاطئة في مناطق الدعم/المقاومة
        """
        # التحقق من صحة الإشارة نسبة لمناطق الدعم والمقاومة
        if 'pair' in signal and 'direction' in signal:
            pair = signal['pair']
            direction = signal['direction']
            
            # الحصول على السعر الحالي
            current_price = 0
            try:
                from technical_analyzer import TechnicalAnalyzer
                analyzer = TechnicalAnalyzer()
                current_price = analyzer.get_current_price(pair)
            except Exception as e:
                logger.warning(f"لم نتمكن من الحصول على السعر الحالي للزوج {pair}: {e}")
            
            if current_price > 0:
                # التحقق من مناطق الدعم والمقاومة
                is_valid, reject_reason = validate_signal(pair, direction, current_price)
                
                if not is_valid:
                    logger.warning(f"❌ تم رفض الإشارة {direction} للزوج {pair}: {reject_reason}")
                    return None
                else:
                    logger.info(f"✅ نجحت الإشارة {direction} للزوج {pair} في اختبار مناطق الدعم والمقاومة")
                    # إضافة معلومات التحقق إلى الإشارة
                    signal['sr_validated'] = True
                    signal['sr_validation_info'] = "تم التحقق من الإشارة في مناطق الدعم والمقاومة"
        
        # نسخة من الإشارة الأصلية
        adjusted_signal = signal.copy()
        
        # التأكد من وجود وقت إنشاء
        if 'generated_at' not in adjusted_signal:
            adjusted_signal['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # حساب وقت الدخول
        current_time = datetime.now()
        entry_time = current_time + timedelta(minutes=self.entry_buffer_minutes)
        
        # تنسيق وقت الدخول بتنسيق HH:MM
        entry_time_str = entry_time.strftime('%H:%M')
        adjusted_signal['entry_time'] = entry_time_str
        
        # حساب وقت انتهاء الصلاحية
        duration = adjusted_signal.get('duration', 1)
        expiration_time = entry_time + timedelta(minutes=duration)
        adjusted_signal['expiration_time'] = expiration_time
        
        logger.info(f"Adjusted entry time: {entry_time_str}, duration: {duration} min, expiration: {expiration_time.strftime('%H:%M')}")
        
        return adjusted_signal
    
    def get_signal_for_pair(self, pair_symbol, force_generation=False):
        """
        الحصول على إشارة لزوج محدد
        
        Args:
            pair_symbol (str): رمز الزوج
            force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
            
        Returns:
            dict: معلومات الإشارة، أو None في حالة عدم إنشاء إشارة
        """
        if not is_valid_pair(pair_symbol):
            logger.warning(f"Invalid pair: {pair_symbol}")
            return None
        
        # التحقق من حالة السوق للزوج المحدد
        if not force_generation:
            # تحليل حالة السوق لهذا الزوج تحديداً
            market_condition = analyze_market_condition(pair_symbol)
            if market_condition and not market_condition.get('is_suitable_for_trading', True):
                warning_message = market_condition.get('warning_message', 
                                   "ظروف سوق غير مناسبة لهذا الزوج. ينصح بتجنب التداول حالياً.")
                logger.warning(f"Signal generation for {pair_symbol} stopped due to poor market conditions")
                
                # إرجاع معلومات التحذير
                return {
                    'type': 'market_warning',
                    'warning_message': warning_message,
                    'pair': pair_symbol,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
        
        return get_premium_signal(pair_symbol=pair_symbol, force_generation=force_generation)
    
    def get_system_status(self):
        """
        الحصول على حالة نظام الإشارات
        
        Returns:
            dict: معلومات حالة النظام
        """
        current_time = datetime.now()
        
        # حساب الوقت المتبقي حتى الإشارة التالية
        next_signal_time = None
        time_until_next = None
        
        if self.last_signal_time:
            next_signal_time = self.last_signal_time + timedelta(minutes=self.signal_interval_minutes)
            time_until_next = (next_signal_time - current_time).total_seconds() / 60
            if time_until_next < 0:
                time_until_next = 0
        
        return {
            'signals_generated': self.signals_generated,
            'last_signal_time': self.last_signal_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_signal_time else None,
            'last_signal_quality': self.last_signal_quality,
            'next_signal_time': next_signal_time.strftime('%Y-%m-%d %H:%M:%S') if next_signal_time else None,
            'time_until_next': f"{time_until_next:.1f} minutes" if time_until_next is not None else None,
            'system_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        }

# النظام المتكامل العالمي للإشارات للاستخدام في جميع أنحاء التطبيق
integrated_signal_system = IntegratedSignalSystem()

def generate_integrated_signal(force_generation=False):
    """
    إنشاء إشارة متكاملة عالية الدقة
    
    Args:
        force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
        
    Returns:
        dict: معلومات الإشارة، أو None في حالة عدم إنشاء إشارة
    """
    return integrated_signal_system.generate_signal(force_generation)

def get_signal_for_specific_pair(pair_symbol, force_generation=False):
    """
    الحصول على إشارة لزوج محدد
    
    Args:
        pair_symbol (str): رمز الزوج
        force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
        
    Returns:
        dict: معلومات الإشارة، أو None في حالة عدم إنشاء إشارة
    """
    return integrated_signal_system.get_signal_for_pair(pair_symbol, force_generation)

def get_signal_system_status():
    """
    الحصول على حالة نظام الإشارات
    
    Returns:
        dict: معلومات حالة النظام
    """
    return integrated_signal_system.get_system_status()