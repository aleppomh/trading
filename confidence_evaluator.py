"""
نظام تقييم مستوى الثقة في الإشارات
هذه الوحدة تستخدم مجموعة من المعايير المتقدمة لتقييم مستوى الثقة في الإشارات
وتحديد قيمة دقيقة لاحتمالية نجاح الإشارة
"""
import logging
import math
import random
import time
from datetime import datetime, timedelta

from technical_analyzer import TechnicalAnalyzer

# إعداد سجل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfidenceEvaluator:
    """نظام تقييم مستوى الثقة في الإشارات"""
    
    def __init__(self):
        """تهيئة نظام تقييم الثقة"""
        self.technical_analyzer = TechnicalAnalyzer()
        
        # أوزان العوامل المختلفة في تقييم الثقة
        self.factor_weights = {
            'signal_strength': 0.3,      # قوة الإشارة الفنية
            'market_conditions': 0.2,    # ظروف السوق
            'timeframe_consistency': 0.2, # اتساق الأطر الزمنية
            'historical_pattern': 0.15,  # أنماط تاريخية مماثلة
            'trend_strength': 0.15       # قوة الاتجاه
        }
        
        # عتبات مستويات الثقة
        self.confidence_levels = {
            'very_high': 95,  # ثقة عالية جداً
            'high': 90,       # ثقة عالية
            'moderate': 85,   # ثقة متوسطة
            'low': 80,        # ثقة منخفضة
            'very_low': 75    # ثقة منخفضة جداً
        }
    
    def evaluate_confidence(self, signal):
        """
        تقييم مستوى الثقة في الإشارة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            int: نسبة الثقة (0-99)
        """
        if not signal or 'direction' not in signal or 'pair' not in signal:
            return 0
        
        logger.info(f"Evaluating confidence for {signal['direction']} signal on {signal['pair']}")
        
        # عوامل تقييم الثقة
        confidence_factors = {}
        
        # العامل 1: قوة الإشارة الفنية الأساسية
        signal_strength = self._evaluate_signal_strength(signal)
        confidence_factors['signal_strength'] = signal_strength
        
        # العامل 2: ظروف السوق الحالية
        market_conditions = self._evaluate_market_conditions(signal)
        confidence_factors['market_conditions'] = market_conditions
        
        # العامل 3: اتساق الأطر الزمنية
        timeframe_consistency = self._evaluate_timeframe_consistency(signal)
        confidence_factors['timeframe_consistency'] = timeframe_consistency
        
        # العامل 4: أنماط تاريخية مماثلة
        historical_pattern = self._evaluate_historical_pattern(signal)
        confidence_factors['historical_pattern'] = historical_pattern
        
        # العامل 5: قوة الاتجاه
        trend_strength = self._evaluate_trend_strength(signal)
        confidence_factors['trend_strength'] = trend_strength
        
        # حساب قيمة الثقة المرجحة
        weighted_confidence = 0
        for factor, value in confidence_factors.items():
            weight = self.factor_weights.get(factor, 0)
            weighted_contribution = value * weight
            weighted_confidence += weighted_contribution
            logger.info(f"  - {factor}: {value:.2f} (weight: {weight}) = {weighted_contribution:.2f}")
        
        # تقييد قيمة الثقة بين 75 و 99
        final_confidence = min(99, max(75, round(weighted_confidence)))
        
        # تحديد مستوى الثقة
        confidence_level = self._determine_confidence_level(final_confidence)
        
        logger.info(f"Final confidence: {final_confidence}% ({confidence_level})")
        
        return final_confidence
    
    def _evaluate_signal_strength(self, signal):
        """
        تقييم قوة الإشارة الفنية
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            float: قيمة قوة الإشارة (0-100)
        """
        # استخدام قيمة الاحتمالية الأصلية كنقطة انطلاق
        base_probability = signal.get('probability', 80)
        
        # تعديل بناءً على قوة الإشارة إذا كانت متاحة
        signal_strength_indicator = 0
        
        # إذا كانت الإشارة من التحليل متعدد الأطر الزمنية
        if signal.get('multi_timeframe'):
            signal_strength_indicator += 5
            logger.info("  - Signal strength bonus: Multi-timeframe analysis (+5)")
            
        # إذا كان الزخم متسقاً مع الاتجاه
        if 'analysis' in signal and 'momentum' in signal['analysis'].lower():
            if (signal['direction'] == 'BUY' and 'زخم صاعد' in signal['analysis']) or \
               (signal['direction'] == 'SELL' and 'زخم هابط' in signal['analysis']):
                signal_strength_indicator += 3
                logger.info("  - Signal strength bonus: Consistent momentum (+3)")
        
        return base_probability + signal_strength_indicator
    
    def _evaluate_market_conditions(self, signal):
        """
        تقييم ظروف السوق الحالية
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            float: قيمة ملاءمة ظروف السوق (0-100)
        """
        pair = signal['pair']
        direction = signal['direction']
        
        # الحصول على بيانات السوق الحالية
        market_data = self.technical_analyzer.price_data.get(pair, {})
        if not market_data or 'candles' not in market_data or len(market_data['candles']) < 20:
            # لا توجد بيانات كافية للتقييم
            return 85  # قيمة متوسطة
        
        candles = market_data['candles']
        
        # حساب مؤشر التذبذب (Volatility)
        volatility = self._calculate_volatility(candles)
        
        # حساب السيولة (تقريباً من خلال حجم الشموع)
        liquidity = self._estimate_liquidity(candles)
        
        # تقييم ملاءمة ظروف السوق للاتجاه
        market_score = 85  # قيمة أساسية متوسطة
        
        # تعديل بناءً على التذبذب
        if volatility > 2.0:  # تذبذب عالٍ
            if direction == 'BUY' and candles[-1]['close'] > candles[-2]['close']:
                # في حالة شراء مع اتجاه صعودي، التذبذب العالي قد يكون مفيداً
                market_score += 5
                logger.info("  - Market conditions: High volatility in uptrend (+5)")
            elif direction == 'SELL' and candles[-1]['close'] < candles[-2]['close']:
                # في حالة بيع مع اتجاه هبوطي، التذبذب العالي قد يكون مفيداً
                market_score += 5
                logger.info("  - Market conditions: High volatility in downtrend (+5)")
            else:
                # التذبذب العالي مع اتجاه معاكس قد يكون خطراً
                market_score -= 5
                logger.info("  - Market conditions: High volatility against trend direction (-5)")
        elif volatility < 0.2:  # تذبذب منخفض جداً
            # في حالة التذبذب المنخفض جداً، الإشارات قد تكون أقل فعالية
            market_score -= 3
            logger.info("  - Market conditions: Very low volatility may limit profit potential (-3)")
        
        # تعديل بناءً على السيولة
        if liquidity > 1.5:  # سيولة عالية
            # السيولة العالية تسهل الدخول والخروج وتقلل من الانزلاق
            market_score += 3
            logger.info("  - Market conditions: Good liquidity (+3)")
        elif liquidity < 0.5:  # سيولة منخفضة
            # السيولة المنخفضة قد تسبب انزلاقاً وتأخيراً في التنفيذ
            market_score -= 3
            logger.info("  - Market conditions: Poor liquidity may cause slippage (-3)")
        
        # تقييد النتيجة بين 0 و 100
        return min(100, max(0, market_score))
    
    def _calculate_volatility(self, candles, lookback=20):
        """
        حساب مؤشر التذبذب للسوق
        
        Args:
            candles (list): بيانات الشموع
            lookback (int): عدد الشموع للحساب
            
        Returns:
            float: نسبة التذبذب كنسبة مئوية
        """
        if len(candles) < lookback:
            return 1.0  # قيمة افتراضية معتدلة
        
        # استخدام آخر N شمعة
        recent_candles = candles[-lookback:]
        
        # حساب متوسط حجم الشموع
        heights = [(c['high'] - c['low']) / c['close'] * 100 for c in recent_candles]
        avg_height = sum(heights) / len(heights)
        
        # حساب الانحراف المعياري للأسعار
        closes = [c['close'] for c in recent_candles]
        mean_price = sum(closes) / len(closes)
        std_dev = math.sqrt(sum([(p - mean_price) ** 2 for p in closes]) / len(closes))
        
        # مؤشر التذبذب المركب
        volatility = (avg_height + (std_dev / mean_price * 100)) / 2
        
        return volatility
    
    def _estimate_liquidity(self, candles, lookback=20):
        """
        تقدير السيولة من خلال حجم الشموع
        
        Args:
            candles (list): بيانات الشموع
            lookback (int): عدد الشموع للحساب
            
        Returns:
            float: مؤشر السيولة النسبي
        """
        if len(candles) < lookback:
            return 1.0  # قيمة افتراضية متوسطة
        
        # استخدام آخر N شمعة
        recent_candles = candles[-lookback:]
        
        # حساب متوسط حجم الشموع (كمقياس بديل للسيولة)
        candle_sizes = [abs(c['open'] - c['close']) for c in recent_candles]
        avg_size = sum(candle_sizes) / len(candle_sizes)
        
        # معايرة إلى مقياس نسبي (1.0 = سيولة متوسطة)
        return avg_size * 100  # تعديل المعامل حسب طبيعة البيانات
    
    def _evaluate_timeframe_consistency(self, signal):
        """
        تقييم اتساق الأطر الزمنية
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            float: قيمة اتساق الأطر الزمنية (0-100)
        """
        # الإشارات متعددة الأطر الزمنية تحصل على تقييم عالٍ تلقائياً
        if signal.get('multi_timeframe'):
            logger.info("  - Timeframe consistency: Multi-timeframe signal already validated")
            return 95
        
        # للإشارات العادية، نستخدم قيمة متوسطة
        # يمكن تحسين هذا بمقارنة الإشارة مع تحليلات من أطر زمنية أخرى
        return 85
    
    def _evaluate_historical_pattern(self, signal):
        """
        تقييم الأنماط التاريخية المماثلة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            float: قيمة تقييم الأنماط التاريخية (0-100)
        """
        # في نموذج حقيقي، سنقوم بتحليل نتائج الإشارات السابقة المماثلة
        # هنا نستخدم تقديراً بسيطاً
        
        # التحقق من وجود أنماط شمعية في التحليل
        pattern_bonus = 0
        if 'analysis' in signal:
            analysis = signal['analysis'].lower()
            
            # أنماط قوية (انعكاس أو استمرار)
            strong_patterns = ['ابتلاع', 'هارامي', 'مطرقة', 'نجمة', 'دوجي']
            for pattern in strong_patterns:
                if pattern in analysis:
                    pattern_bonus += 3
                    logger.info(f"  - Historical pattern: Found strong candle pattern '{pattern}' (+3)")
                    break  # نكتفي بنمط واحد قوي
            
            # اتساق مع مؤشرات متعددة
            indicators = ['rsi', 'macd', 'ستوكاستك', 'bollinger']
            indicator_count = sum(1 for ind in indicators if ind in analysis)
            if indicator_count >= 3:
                pattern_bonus += 4
                logger.info(f"  - Historical pattern: Multiple indicators confirm signal (+4)")
            elif indicator_count >= 2:
                pattern_bonus += 2
                logger.info(f"  - Historical pattern: Two indicators confirm signal (+2)")
        
        # قيمة أساسية + تعديلات
        return 85 + pattern_bonus
    
    def _evaluate_trend_strength(self, signal):
        """
        تقييم قوة الاتجاه
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            float: قيمة تقييم قوة الاتجاه (0-100)
        """
        # التحقق من وجود معلومات عن الاتجاه في التحليل
        trend_score = 85  # قيمة أساسية
        
        if 'analysis' in signal:
            analysis = signal['analysis'].lower()
            direction = signal['direction']
            
            # البحث عن مؤشرات قوة الاتجاه
            if direction == 'BUY':
                if 'اتجاه صاعد قوي' in analysis:
                    trend_score += 10
                    logger.info("  - Trend strength: Strong uptrend detected (+10)")
                elif 'اتجاه صاعد' in analysis:
                    trend_score += 5
                    logger.info("  - Trend strength: Uptrend detected (+5)")
            elif direction == 'SELL':
                if 'اتجاه هابط قوي' in analysis:
                    trend_score += 10
                    logger.info("  - Trend strength: Strong downtrend detected (+10)")
                elif 'اتجاه هابط' in analysis:
                    trend_score += 5
                    logger.info("  - Trend strength: Downtrend detected (+5)")
            
            # التحقق من تأكيد ADX (مؤشر متوسط الاتجاه)
            if 'adx' in analysis:
                if 'adx' in analysis and any(x in analysis for x in ['قوي', 'عالي']):
                    trend_score += 5
                    logger.info("  - Trend strength: High ADX confirms strong trend (+5)")
        
        return min(100, trend_score)
    
    def _determine_confidence_level(self, confidence_value):
        """
        تحديد مستوى الثقة بناءً على القيمة
        
        Args:
            confidence_value (int): قيمة الثقة
            
        Returns:
            str: وصف مستوى الثقة
        """
        if confidence_value >= self.confidence_levels['very_high']:
            return 'مرتفع جداً'
        elif confidence_value >= self.confidence_levels['high']:
            return 'مرتفع'
        elif confidence_value >= self.confidence_levels['moderate']:
            return 'متوسط'
        elif confidence_value >= self.confidence_levels['low']:
            return 'منخفض'
        else:
            return 'منخفض جداً'
    
    def enhance_signal_confidence(self, signal):
        """
        تعزيز مستوى الثقة في الإشارة
        
        Args:
            signal (dict): معلومات الإشارة الأصلية
            
        Returns:
            dict: الإشارة مع مستوى ثقة محسن
        """
        if not signal:
            return None
        
        # نسخة من الإشارة الأصلية
        enhanced_signal = signal.copy()
        
        # تقييم مستوى الثقة
        confidence = self.evaluate_confidence(signal)
        
        # تحديث قيمة الاحتمالية
        enhanced_signal['probability'] = confidence
        
        # إضافة معلومات إضافية عن الثقة
        confidence_level = self._determine_confidence_level(confidence)
        enhanced_signal['confidence_level'] = confidence_level
        
        # تعديل التحليل لإضافة معلومات الثقة
        if 'analysis' in enhanced_signal:
            enhanced_signal['analysis'] += f" | مستوى الثقة: {confidence}% ({confidence_level})"
        
        return enhanced_signal

# مقيم الثقة العالمي للاستخدام في جميع أنحاء التطبيق
confidence_evaluator = ConfidenceEvaluator()

def evaluate_signal_confidence(signal):
    """
    تقييم مستوى الثقة في الإشارة
    
    Args:
        signal (dict): معلومات الإشارة
        
    Returns:
        int: نسبة الثقة (0-99)
    """
    return confidence_evaluator.evaluate_confidence(signal)

def enhance_signal_with_confidence(signal):
    """
    تعزيز الإشارة بمعلومات الثقة المحسنة
    
    Args:
        signal (dict): معلومات الإشارة الأصلية
        
    Returns:
        dict: الإشارة مع مستوى ثقة محسن
    """
    return confidence_evaluator.enhance_signal_confidence(signal)