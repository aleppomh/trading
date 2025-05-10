"""
نظام الإشارات المعزز
دمج نظام الفلترة متعدد المراحل مع نظام توليد الإشارات لزيادة الدقة.
"""

import os
import time
import logging
import json
import random
from datetime import datetime, timedelta

from advanced_signal_filter import filter_trading_signal
import multi_stage_signal_filter as msf
import advanced_otc_analyzer as otc_analyzer
import market_pairs

logger = logging.getLogger(__name__)

# إعدادات توليد الإشارات
MIN_SIGNAL_QUALITY = 85  # الحد الأدنى لجودة الإشارة
MAX_FAILED_ATTEMPTS = 5  # أقصى عدد محاولات فاشلة قبل الاستسلام
OTC_PRIORITY = 0.8       # أولوية أزواج OTC (0-1)


class EnhancedSignalSystem:
    """
    نظام الإشارات المعزز بالتصفية متعددة المراحل والتحليل المتقدم
    """
    
    def __init__(self):
        """تهيئة نظام الإشارات المعزز"""
        logger.info("تهيئة نظام الإشارات المعزز")
        # سجل الإشارات
        self.signal_history = []
        # إحصائيات النظام
        self.stats = {
            "total_signals": 0,
            "filtered_signals": 0,
            "otc_signals": 0,
            "regular_signals": 0,
            "high_quality_signals": 0
        }
    
    def generate_signal(self, pair_symbol=None, force_generation=False):
        """
        توليد إشارة عالية الجودة
        
        Args:
            pair_symbol (str, optional): رمز الزوج
            force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
            
        Returns:
            dict: معلومات الإشارة، أو None في حالة الفشل
        """
        logger.info(f"بدء توليد إشارة للزوج {pair_symbol if pair_symbol else 'عشوائي'}")
        
        # تحديد الزوج
        if not pair_symbol:
            # اختيار زوج بناءً على الأولوية
            pair_symbol, is_otc = self._select_optimal_pair()
            logger.info(f"تم اختيار الزوج {pair_symbol} (OTC: {is_otc})")
        else:
            # التحقق من نوع الزوج
            is_otc = "-OTC" in pair_symbol
        
        # محاولات توليد الإشارة
        attempt = 0
        while attempt < MAX_FAILED_ATTEMPTS:
            attempt += 1
            logger.info(f"محاولة توليد الإشارة رقم {attempt} للزوج {pair_symbol}")
            
            try:
                # الحصول على بيانات الشموع
                candles = self._get_candle_data(pair_symbol)
                
                if not candles or len(candles) < 30:
                    logger.warning(f"بيانات شموع غير كافية للزوج {pair_symbol}")
                    continue
                
                # تحليل متقدم
                otc_analysis = otc_analyzer.analyze_otc_pair(candles, pair_symbol)
                
                # توليد الإشارة الأولية
                signal = self._generate_initial_signal(pair_symbol, candles, otc_analysis)
                
                if not signal:
                    logger.warning(f"فشل في توليد إشارة أولية للزوج {pair_symbol}")
                    continue
                
                # تصفية الإشارة باستخدام النظام متعدد المراحل
                is_valid, quality, reason = msf.filter_signal_multi_stage(
                    signal, candles, pair_symbol, otc_analysis
                )
                
                if is_valid or force_generation:
                    # إذا كانت الإشارة صالحة أو تم فرض التوليد
                    enhanced_signal = self._enhance_signal(
                        signal, quality, candles, pair_symbol, otc_analysis
                    )
                    
                    # تسجيل الإشارة في السجل
                    self._record_signal(enhanced_signal, is_valid, quality)
                    
                    logger.info(f"تم توليد إشارة بنجاح للزوج {pair_symbol} بجودة {quality:.1f}%")
                    
                    # تحديث الإحصائيات
                    self.stats["total_signals"] += 1
                    if is_otc:
                        self.stats["otc_signals"] += 1
                    else:
                        self.stats["regular_signals"] += 1
                    
                    if quality >= 90:
                        self.stats["high_quality_signals"] += 1
                    
                    return enhanced_signal
                else:
                    logger.warning(f"تم رفض الإشارة للزوج {pair_symbol}: {reason}")
                    self.stats["filtered_signals"] += 1
            
            except Exception as e:
                logger.exception(f"خطأ أثناء توليد الإشارة للزوج {pair_symbol}: {str(e)}")
            
            # تأخير قبل المحاولة التالية
            time.sleep(1)
        
        logger.error(f"استنفدت جميع المحاولات لتوليد إشارة للزوج {pair_symbol}")
        return None
    
    def _select_optimal_pair(self):
        """
        اختيار الزوج الأمثل للإشارة التالية
        
        Returns:
            tuple: (الزوج المختار، ما إذا كان OTC)
        """
        # الحصول على قوائم الأزواج
        market_pairs_list = market_pairs.get_default_market_pairs()
        otc_pairs_list = market_pairs.get_default_otc_pairs()
        
        # تحديد ما إذا كان سيتم اختيار زوج OTC بناءً على الأولوية
        use_otc = random.random() < OTC_PRIORITY
        
        if use_otc and otc_pairs_list:
            # اختيار زوج OTC عشوائي
            pair = random.choice(otc_pairs_list)
            return pair, True
        elif market_pairs_list:
            # اختيار زوج سوق عادي عشوائي
            pair = random.choice(market_pairs_list)
            return pair, False
        else:
            # استخدام زوج افتراضي في حالة عدم وجود قوائم
            return "EUR/USD-OTC", True
    
    def _get_candle_data(self, pair_symbol):
        """
        الحصول على بيانات الشموع للزوج
        
        Args:
            pair_symbol (str): رمز الزوج
            
        Returns:
            list: بيانات الشموع
        """
        # هذه دالة وهمية تعيد بيانات شموع للاختبار
        # في التطبيق الحقيقي، ستقوم بجلب البيانات من مصدر خارجي أو API
        
        # محاكاة بيانات شموع لأغراض الاختبار
        candles = []
        base_price = 1.0
        
        # توليد 100 شمعة
        for i in range(100):
            change = (random.random() - 0.5) * 0.002  # تغير السعر
            base_price += change
            
            # تكوين الشمعة
            candle = {
                'time': datetime.utcnow() - timedelta(minutes=100-i),
                'open': base_price,
                'high': base_price + abs(change) * random.random() * 2,
                'low': base_price - abs(change) * random.random() * 2,
                'close': base_price + change,
                'volume': random.randint(100, 1000)
            }
            
            # التأكد من أن High أكبر من Low
            candle['high'] = max(candle['high'], candle['open'], candle['close'])
            candle['low'] = min(candle['low'], candle['open'], candle['close'])
            
            candles.append(candle)
        
        return candles
    
    def _generate_initial_signal(self, pair_symbol, candles, otc_analysis):
        """
        توليد إشارة أولية بناءً على التحليل
        
        Args:
            pair_symbol (str): رمز الزوج
            candles (list): بيانات الشموع
            otc_analysis (dict): نتائج التحليل المتقدم
            
        Returns:
            dict: الإشارة الأولية
        """
        # استخدام نتائج التحليل المتقدم
        direction = otc_analysis.get("direction", "NEUTRAL")
        confidence = otc_analysis.get("confidence", 50)
        
        # لا نعالج الإشارات المحايدة
        if direction == "NEUTRAL" or confidence < 70:
            return None
        
        # إنشاء التحليل النصي
        analysis_text = otc_analyzer.generate_analysis_text(otc_analysis, pair_symbol)
        
        # إنشاء إشارة التداول
        from datetime import datetime, timedelta
        
        current_time = datetime.utcnow()
        entry_time = current_time + timedelta(minutes=2)
        # تقريب إلى أقرب دقيقة
        entry_time = entry_time.replace(second=0, microsecond=0)
        # تحويل إلى توقيت تركيا (UTC+3)
        turkey_time = entry_time + timedelta(hours=3)
        entry_time_str = turkey_time.strftime('%H:%M')
        
        # تحديد المدة (1، 2، أو 3 دقائق) بناءً على نمط الإشارة
        if confidence >= 90:
            duration = 3  # إشارة قوية = مدة 3 دقائق
        elif confidence >= 80:
            duration = 2  # إشارة متوسطة = مدة 2 دقيقة
        else:
            duration = 1  # إشارة ضعيفة = مدة 1 دقيقة
        
        signal = {
            "pair": pair_symbol,
            "direction": direction,
            "entry_time": entry_time_str,
            "duration": f"{duration} دقيقة",
            "expiry": f"{duration} min",
            "probability": f"{int(confidence)}%",
            "analysis_notes": analysis_text,
            "technical_indicators": otc_analyzer.get_technical_indicators_summary(otc_analysis)
        }
        
        return signal
    
    def _enhance_signal(self, signal, quality, candles, pair_symbol, otc_analysis):
        """
        تحسين الإشارة بإضافة معلومات متقدمة
        
        Args:
            signal (dict): الإشارة الأولية
            quality (float): درجة الجودة
            candles (list): بيانات الشموع
            pair_symbol (str): رمز الزوج
            otc_analysis (dict): نتائج التحليل المتقدم
            
        Returns:
            dict: الإشارة المحسنة
        """
        enhanced_signal = signal.copy()
        
        # إضافة معلومات التصفية المتقدمة
        enhanced_signal["quality_score"] = f"{quality:.1f}%"
        
        # إضافة معلومات نقاط الدعم والمقاومة
        support_resistance = otc_analysis.get("support_resistance", {})
        if support_resistance:
            support_levels = support_resistance.get("support_levels", [])
            resistance_levels = support_resistance.get("resistance_levels", [])
            
            if support_levels:
                # تحويل مستويات الدعم إلى تنسيق مبسط
                simple_support = [round(level["price"], 6) for level in support_levels]
                enhanced_signal["support_levels"] = simple_support
            
            if resistance_levels:
                # تحويل مستويات المقاومة إلى تنسيق مبسط
                simple_resistance = [round(level["price"], 6) for level in resistance_levels]
                enhanced_signal["resistance_levels"] = simple_resistance
        
        # تحديد مستوى الثقة النهائي (استخدام الأعلى بين الإشارة الأصلية والتحليل المتقدم)
        original_confidence = int(signal.get("probability", "0").replace("%", ""))
        if quality > original_confidence:
            enhanced_signal["probability"] = f"{int(quality)}%"
        
        return enhanced_signal
    
    def _record_signal(self, signal, is_valid, quality):
        """
        تسجيل الإشارة في السجل
        
        Args:
            signal (dict): الإشارة
            is_valid (bool): ما إذا كانت الإشارة صالحة
            quality (float): درجة الجودة
        """
        # إضافة معلومات إضافية للسجل
        signal_record = {
            "signal": signal,
            "timestamp": datetime.utcnow().isoformat(),
            "is_valid": is_valid,
            "quality": quality
        }
        
        # إضافة إلى السجل
        self.signal_history.append(signal_record)
        
        # الاحتفاظ بآخر 100 إشارة فقط
        if len(self.signal_history) > 100:
            self.signal_history = self.signal_history[-100:]
    
    def get_signal_history(self):
        """
        الحصول على سجل الإشارات
        
        Returns:
            list: سجل الإشارات
        """
        return self.signal_history
    
    def get_statistics(self):
        """
        الحصول على إحصائيات النظام
        
        Returns:
            dict: إحصائيات النظام
        """
        return self.stats


# واجهة عامة لاستخدام النظام
_signal_system = None


def get_enhanced_signal(pair_symbol=None, force_generation=False):
    """
    الحصول على إشارة معززة عالية الجودة
    
    Args:
        pair_symbol (str, optional): رمز الزوج
        force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
        
    Returns:
        dict: معلومات الإشارة، أو None في حالة الفشل
    """
    global _signal_system
    
    if _signal_system is None:
        _signal_system = EnhancedSignalSystem()
    
    return _signal_system.generate_signal(pair_symbol, force_generation)


def get_signal_statistics():
    """
    الحصول على إحصائيات نظام الإشارات
    
    Returns:
        dict: إحصائيات النظام
    """
    global _signal_system
    
    if _signal_system is None:
        _signal_system = EnhancedSignalSystem()
    
    return _signal_system.get_statistics()


def get_signal_history():
    """
    الحصول على سجل الإشارات
    
    Returns:
        list: سجل الإشارات
    """
    global _signal_system
    
    if _signal_system is None:
        _signal_system = EnhancedSignalSystem()
    
    return _signal_system.get_signal_history()