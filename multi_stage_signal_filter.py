"""
نظام تصفية متعدد المراحل للإشارات
يقوم بفلترة الإشارات عبر مراحل متعددة للوصول إلى دقة عالية
خاص بأزواج OTC ويدعم المؤشرات الفنية المتعددة

يدمج هذا النظام مع محلل الأزواج OTC المتقدم للحصول على نتائج دقيقة جداً
"""

import logging
import numpy as np
from datetime import datetime, timedelta
import advanced_otc_analyzer as otc_analyzer
from advanced_signal_filter import AdvancedSignalFilter, filter_trading_signal

logger = logging.getLogger(__name__)

# ثوابت ومعلمات النظام
MIN_MULTI_STAGE_SCORE = 75           # الحد الأدنى لدرجة الفلترة المتعددة (خفض الحد الأدنى للأزواج OTC)
MIN_CONFIRMATION_COUNT = 3           # الحد الأدنى لعدد المؤشرات المؤكدة للإشارة
MARKET_TREND_WEIGHT = 1.2            # وزن اتجاه السوق العام
TECHNICAL_INDICATORS_WEIGHT = 1.5    # وزن المؤشرات الفنية
SUPPORT_RESISTANCE_WEIGHT = 1.3      # وزن مستويات الدعم والمقاومة
OTC_BONUS_SCORE = 15                 # نقاط إضافية لأزواج OTC (زيادة المكافأة)


class MultiStageSignalFilter:
    """
    نظام فلترة متعدد المراحل للإشارات
    يقوم بفلترة الإشارات عبر مراحل متعددة للوصول إلى دقة عالية
    """
    
    def __init__(self):
        """تهيئة نظام الفلترة متعدد المراحل"""
        logger.info("تهيئة نظام الفلترة متعدد المراحل")
        self.advanced_filter = AdvancedSignalFilter()
        
    def filter_signal(self, signal, candles, pair_symbol, additional_analysis=None):
        """
        تصفية الإشارة باستخدام نظام متعدد المراحل

        Args:
            signal (dict): معلومات الإشارة المراد فلترتها
            candles (list): بيانات الشموع للتحليل
            pair_symbol (str): رمز الزوج
            additional_analysis (dict, optional): نتائج تحليل إضافية

        Returns:
            tuple: (قبول الإشارة, درجة الجودة, سبب القبول أو الرفض, التحليل المفصل)
        """
        logger.info(f"بدء تصفية الإشارة لزوج {pair_symbol} عبر النظام متعدد المراحل")
        
        # تحديد ما إذا كان الزوج من أزواج OTC
        is_otc = "-OTC" in pair_symbol
        
        # المرحلة الأولى: الفلترة التقليدية باستخدام AdvancedSignalFilter
        basic_accept, basic_quality, basic_reason = self.advanced_filter.filter_signal(signal, candles)
        
        if not basic_accept:
            logger.info(f"تم رفض الإشارة في المرحلة الأولى: {basic_reason}")
            return False, basic_quality, basic_reason, {"basic_filter": {"accepted": False, "quality": basic_quality, "reason": basic_reason}}
        
        logger.info(f"المرحلة الأولى: تم قبول الإشارة بدرجة جودة {basic_quality}")
        
        # المرحلة الثانية: تحليل متقدم لأزواج OTC
        try:
            if not additional_analysis:
                # إجراء تحليل الأزواج OTC المتقدم
                otc_analysis = otc_analyzer.analyze_otc_pair(candles, pair_symbol)
            else:
                otc_analysis = additional_analysis
            
            # المرحلة الثالثة: التأكد من اتساق اتجاه الإشارة مع نتائج التحليل المتقدم
            signal_direction = signal.get('direction', 'NEUTRAL')
            otc_direction = otc_analysis.get('direction', 'NEUTRAL')
            
            if signal_direction != otc_direction and otc_direction != 'NEUTRAL':
                logger.warning(f"تناقض في الاتجاه: إشارة أصلية={signal_direction}, تحليل متقدم={otc_direction}")
                return False, basic_quality * 0.7, "تناقض في اتجاه الإشارة مع التحليل المتقدم", {
                    "basic_filter": {"accepted": True, "quality": basic_quality},
                    "otc_analysis": {"accepted": False, "direction": otc_direction, "confidence": otc_analysis.get("confidence", 0)}
                }
            
            # المرحلة الرابعة: التحقق من التأكيدات المتعددة
            confirmations = self._calculate_confirmation_count(otc_analysis, signal_direction)
            
            if confirmations < MIN_CONFIRMATION_COUNT:
                logger.warning(f"عدد التأكيدات غير كافٍ: {confirmations} < {MIN_CONFIRMATION_COUNT}")
                return False, basic_quality * 0.8, f"تأكيدات غير كافية ({confirmations}/{MIN_CONFIRMATION_COUNT})", {
                    "basic_filter": {"accepted": True, "quality": basic_quality},
                    "otc_analysis": {"accepted": False, "confirmations": confirmations, "required": MIN_CONFIRMATION_COUNT}
                }
            
            # المرحلة الخامسة: التحقق من جودة الإشارة النهائية
            multi_stage_score = self._calculate_multi_stage_score(
                basic_quality, otc_analysis, signal_direction, is_otc
            )
            
            if multi_stage_score < MIN_MULTI_STAGE_SCORE:
                logger.warning(f"درجة جودة المراحل المتعددة غير كافية: {multi_stage_score} < {MIN_MULTI_STAGE_SCORE}")
                return False, multi_stage_score, f"جودة الإشارة غير كافية ({multi_stage_score:.1f}%)", {
                    "basic_filter": {"accepted": True, "quality": basic_quality},
                    "otc_analysis": {"accepted": False, "score": multi_stage_score, "required": MIN_MULTI_STAGE_SCORE}
                }
            
            # المرحلة السادسة: التحقق من توافق الإشارة مع نقاط الدعم والمقاومة
            sr_check = self._check_support_resistance_compatibility(
                otc_analysis, signal_direction, basic_quality
            )
            
            if not sr_check["compatible"]:
                logger.warning(f"الإشارة غير متوافقة مع نقاط الدعم والمقاومة: {sr_check['reason']}")
                return False, multi_stage_score * 0.9, sr_check["reason"], {
                    "basic_filter": {"accepted": True, "quality": basic_quality},
                    "otc_analysis": {"accepted": False, "sr_check": sr_check}
                }
            
            # تحسين درجة الجودة النهائية بناءً على خصائص الزوج
            final_quality = self._enhance_final_quality(multi_stage_score, pair_symbol, is_otc)
            
            logger.info(f"تم قبول الإشارة عبر النظام متعدد المراحل بدرجة نهائية {final_quality:.1f}%")
            
            detailed_analysis = {
                "basic_filter": {"accepted": True, "quality": basic_quality},
                "otc_analysis": {"accepted": True, "score": multi_stage_score},
                "final_quality": final_quality,
                "confirmations": confirmations,
                "direction": signal_direction,
                "otc_direction": otc_direction,
                "is_otc": is_otc
            }
            
            return True, final_quality, f"إشارة عالية الجودة ({final_quality:.1f}%) مع {confirmations} تأكيدات", detailed_analysis
            
        except Exception as e:
            logger.exception(f"خطأ في نظام الفلترة متعدد المراحل: {str(e)}")
            # في حالة حدوث خطأ، نعتمد على نتيجة الفلترة الأساسية
            return basic_accept, basic_quality, f"{basic_reason} (خطأ في التحليل المتقدم: {str(e)})", {
                "basic_filter": {"accepted": basic_accept, "quality": basic_quality, "reason": basic_reason},
                "error": str(e)
            }
    
    def _calculate_confirmation_count(self, otc_analysis, signal_direction):
        """
        حساب عدد المؤشرات التي تؤكد اتجاه الإشارة
        
        Args:
            otc_analysis (dict): نتائج تحليل OTC
            signal_direction (str): اتجاه الإشارة
            
        Returns:
            int: عدد التأكيدات
        """
        confirmations = 0
        
        # تحقق من المؤشرات الفنية
        technical_indicators = otc_analysis.get("technical_indicators", {})
        
        # تحقق من RSI
        if technical_indicators.get("rsi", {}).get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من EMA
        if technical_indicators.get("ema", {}).get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من MACD
        if technical_indicators.get("macd", {}).get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من Bollinger Bands
        if technical_indicators.get("bollinger", {}).get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من نمط الشموع
        if technical_indicators.get("candle_pattern", {}).get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من اتجاه السوق
        market_trend = otc_analysis.get("market_trend", {}).get("overall", {})
        if market_trend.get("signal") == signal_direction:
            confirmations += 1
        
        # تحقق من أنماط الانعكاس
        reversal_patterns = otc_analysis.get("reversal_patterns", {})
        if reversal_patterns.get("has_reversal", False) and reversal_patterns.get("signal") == signal_direction:
            confirmations += 1
        
        return confirmations
    
    def _calculate_multi_stage_score(self, basic_quality, otc_analysis, signal_direction, is_otc):
        """
        حساب درجة جودة الفلترة متعددة المراحل
        
        Args:
            basic_quality (float): درجة الجودة الأساسية
            otc_analysis (dict): نتائج تحليل OTC
            signal_direction (str): اتجاه الإشارة
            is_otc (bool): ما إذا كان الزوج من أزواج OTC
            
        Returns:
            float: درجة الجودة النهائية
        """
        # الوزن الأساسي من الفلترة الأولية
        score_components = [basic_quality * 0.4]  # 40% من الدرجة الأساسية
        
        # إضافة درجة الثقة من تحليل OTC
        confidence = otc_analysis.get("confidence", 50)
        score_components.append(confidence * 0.3)  # 30% من درجة الثقة
        
        # إضافة درجة من جودة الإشارة
        signal_quality = otc_analysis.get("signal_quality", {}).get("overall_quality", 50)
        score_components.append(signal_quality * 0.3)  # 30% من جودة الإشارة
        
        # تعديل الدرجة بناءً على اتجاه السوق
        market_trend = otc_analysis.get("market_trend", {}).get("overall", {})
        market_strength = market_trend.get("strength", 0)
        
        if market_trend.get("signal") == signal_direction:
            # اتجاه السوق يتوافق مع اتجاه الإشارة - زيادة الدرجة
            market_factor = MARKET_TREND_WEIGHT
        else:
            # اتجاه السوق يتعارض مع اتجاه الإشارة - تخفيض الدرجة
            market_factor = 1.0 / MARKET_TREND_WEIGHT
        
        # إضافة معامل اتجاه السوق
        score_components.append(market_strength * 0.1 * market_factor)
        
        # تعديل الدرجة بناءً على المؤشرات الفنية
        confirmations = self._calculate_confirmation_count(otc_analysis, signal_direction)
        technical_factor = min(1.5, 1 + (confirmations - MIN_CONFIRMATION_COUNT) * 0.1)
        
        # إضافة معامل المؤشرات الفنية
        for component in score_components:
            component *= technical_factor
        
        # إضافة نقاط إضافية للأزواج OTC
        if is_otc:
            score_components.append(OTC_BONUS_SCORE)
        
        # حساب الدرجة النهائية
        final_score = sum(score_components)
        
        # التأكد من أن الدرجة في النطاق المناسب
        return min(100, max(0, final_score))
    
    def _check_support_resistance_compatibility(self, otc_analysis, signal_direction, basic_quality):
        """
        التحقق من توافق الإشارة مع نقاط الدعم والمقاومة
        
        Args:
            otc_analysis (dict): نتائج تحليل OTC
            signal_direction (str): اتجاه الإشارة
            basic_quality (float): درجة الجودة الأساسية
            
        Returns:
            dict: نتيجة التحقق
        """
        # استخراج معلومات الدعم والمقاومة
        support_resistance = otc_analysis.get("support_resistance", {})
        support_levels = support_resistance.get("support_levels", [])
        resistance_levels = support_resistance.get("resistance_levels", [])
        current_price = support_resistance.get("current_price")
        
        if not current_price or (not support_levels and not resistance_levels):
            # لا توجد معلومات كافية - نعتبر متوافقة افتراضياً
            return {"compatible": True, "reason": "لا توجد معلومات دعم ومقاومة كافية"}
        
        # التحقق من التوافق مع اتجاه الإشارة
        if signal_direction == "BUY":
            # نبحث عن نقاط دعم قوية قريبة من السعر الحالي
            if support_levels:
                closest_support = min(support_levels, key=lambda x: abs(x["price"] - current_price))
                support_distance = (current_price - closest_support["price"]) / current_price * 100
                
                # إذا كان السعر قريب جداً من الدعم، فهذه إشارة جيدة للشراء
                if support_distance <= 0.5:  # أقل من 0.5% من السعر الحالي
                    return {"compatible": True, "reason": f"السعر قريب من مستوى دعم قوي ({support_distance:.2f}%)", "level": closest_support}
                
                # إذا كان السعر يرتد من مستوى دعم، فهذه إشارة جيدة للشراء
                if 0.5 < support_distance <= 2.0 and closest_support["strength"] >= 70:
                    return {"compatible": True, "reason": f"السعر يرتد من مستوى دعم قوي ({closest_support['strength']:.0f}%)", "level": closest_support}
            
            # التحقق من المسافة إلى المقاومة
            if resistance_levels:
                closest_resistance = min(resistance_levels, key=lambda x: abs(x["price"] - current_price))
                resistance_distance = (closest_resistance["price"] - current_price) / current_price * 100
                
                # إذا كان السعر قريب جداً من المقاومة، فهذه إشارة سيئة للشراء
                if float(resistance_distance) <= 0.5:  # أقل من 0.5% من السعر الحالي
                    return {"compatible": False, "reason": f"السعر قريب جداً من مستوى مقاومة ({resistance_distance:.2f}%)", "level": closest_resistance}
            
        elif signal_direction == "SELL":
            # نبحث عن نقاط مقاومة قوية قريبة من السعر الحالي
            if resistance_levels:
                closest_resistance = min(resistance_levels, key=lambda x: abs(x["price"] - current_price))
                resistance_distance = (closest_resistance["price"] - current_price) / current_price * 100
                
                # إذا كان السعر قريب جداً من المقاومة، فهذه إشارة جيدة للبيع
                if float(resistance_distance) <= 0.5:  # أقل من 0.5% من السعر الحالي
                    return {"compatible": True, "reason": f"السعر قريب من مستوى مقاومة قوي ({resistance_distance:.2f}%)", "level": closest_resistance}
                
                # إذا كان السعر يرتد من مستوى مقاومة، فهذه إشارة جيدة للبيع
                if 0.5 < float(resistance_distance) <= 2.0 and closest_resistance["strength"] >= 70:
                    return {"compatible": True, "reason": f"السعر يرتد من مستوى مقاومة قوي ({closest_resistance['strength']:.0f}%)", "level": closest_resistance}
            
            # التحقق من المسافة إلى الدعم
            if support_levels:
                closest_support = min(support_levels, key=lambda x: abs(x["price"] - current_price))
                support_distance = (current_price - closest_support["price"]) / current_price * 100
                
                # إذا كان السعر قريب جداً من الدعم، فهذه إشارة سيئة للبيع
                if float(support_distance) <= 0.5:  # أقل من 0.5% من السعر الحالي
                    return {"compatible": False, "reason": f"السعر قريب جداً من مستوى دعم ({support_distance:.2f}%)", "level": closest_support}
        
        # لم نجد تعارضاً واضحاً، نعتبر الإشارة متوافقة
        return {"compatible": True, "reason": "الإشارة متوافقة مع مستويات الدعم والمقاومة"}
    
    def _enhance_final_quality(self, multi_stage_score, pair_symbol, is_otc):
        """
        تحسين درجة الجودة النهائية بناءً على خصائص الزوج
        
        Args:
            multi_stage_score (float): درجة جودة المراحل المتعددة
            pair_symbol (str): رمز الزوج
            is_otc (bool): ما إذا كان الزوج من أزواج OTC
            
        Returns:
            float: درجة الجودة النهائية المحسنة
        """
        # قاموس تحسينات خاصة بأزواج محددة
        pair_enhancements = {
            "EUR/JPY-OTC": 5,
            "EUR/USD-OTC": 4,
            "AUD/CAD-OTC": 3,
            "GBP/JPY-OTC": 4,
            "USD/CHF-OTC": 3,
            "BHD/CNY-OTC": 2,
        }
        
        final_quality = multi_stage_score
        
        # إضافة تحسين خاص بالزوج المحدد
        if pair_symbol in pair_enhancements:
            final_quality += pair_enhancements[pair_symbol]
            logger.info(f"إضافة {pair_enhancements[pair_symbol]} نقاط لزوج {pair_symbol}")
        
        # تحسين عام للأزواج OTC
        if is_otc and final_quality < 98:  # لا نتجاوز 100
            final_quality = min(98, final_quality + 2)
            logger.info(f"تحسين عام للأزواج OTC: +2 نقاط")
        
        return final_quality


def filter_signal_multi_stage(signal, candles, pair_symbol, additional_analysis=None):
    """
    تصفية الإشارة باستخدام نظام متعدد المراحل (واجهة عامة)
    
    Args:
        signal (dict): معلومات الإشارة المراد فلترتها
        candles (list): بيانات الشموع للتحليل
        pair_symbol (str): رمز الزوج
        additional_analysis (dict, optional): نتائج تحليل إضافية
    
    Returns:
        tuple: (قبول الإشارة, درجة الجودة, سبب القبول أو الرفض)
    """
    filter_instance = MultiStageSignalFilter()
    accept, quality, reason, detailed_analysis = filter_instance.filter_signal(
        signal, candles, pair_symbol, additional_analysis
    )
    return accept, quality, reason


def enhance_signal_with_advanced_analysis(signal, candles, pair_symbol):
    """
    تحسين الإشارة بإضافة التحليل المتقدم
    
    Args:
        signal (dict): معلومات الإشارة الأصلية
        candles (list): بيانات الشموع للتحليل
        pair_symbol (str): رمز الزوج
    
    Returns:
        dict: الإشارة المحسنة مع التحليل المتقدم
    """
    try:
        # تحليل الزوج باستخدام محلل OTC المتقدم
        otc_analysis = otc_analyzer.analyze_otc_pair(candles, pair_symbol)
        
        # استخراج المؤشرات الفنية
        technical_indicators = otc_analyzer.get_technical_indicators_summary(otc_analysis)
        
        # إضافة التحليل المتقدم إلى الإشارة
        enhanced_signal = signal.copy()
        enhanced_signal["technical_indicators"] = technical_indicators
        
        # إضافة درجة الثقة من التحليل المتقدم إذا كانت أعلى
        advanced_confidence = otc_analysis.get("confidence", 0)
        original_confidence_str = signal.get("probability", "0").replace("%", "")
        original_confidence = int(original_confidence_str) if original_confidence_str.isdigit() else 0
        
        if int(advanced_confidence) > original_confidence:
            enhanced_signal["probability"] = f"{int(advanced_confidence)}%"
            logger.info(f"تحسين درجة الثقة من {original_confidence}% إلى {int(advanced_confidence)}%")
        
        # تصفية الإشارة المحسنة
        is_valid, quality, reason = filter_signal_multi_stage(
            enhanced_signal, candles, pair_symbol, otc_analysis
        )
        
        if is_valid:
            # إضافة معلومات التصفية
            enhanced_signal["multi_stage_quality"] = quality
            enhanced_signal["filter_reason"] = reason
            return enhanced_signal
        else:
            logger.warning(f"تم رفض الإشارة المحسنة: {reason}")
            return None
            
    except Exception as e:
        logger.exception(f"خطأ في تحسين الإشارة: {str(e)}")
        return signal  # إرجاع الإشارة الأصلية في حالة الخطأ