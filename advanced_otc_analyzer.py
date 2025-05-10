"""
نظام تحليل متقدم لأزواج OTC
يجمع بين المؤشرات الفنية المتعددة ونظام فلترة متعدد المراحل لزيادة دقة الإشارات
"""

import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Constants for OTC pairs analysis
OTC_RSI_PERIOD = 9           # فترة مؤشر RSI قصيرة لأزواج OTC للحساسية العالية
OTC_EMA_SHORT_PERIOD = 5     # فترة المتوسط المتحرك الأسي القصير لأزواج OTC
OTC_EMA_MEDIUM_PERIOD = 13   # فترة المتوسط المتحرك الأسي المتوسط لأزواج OTC
OTC_MACD_FAST = 8            # فترة MACD السريع لأزواج OTC
OTC_MACD_SLOW = 17           # فترة MACD البطيء لأزواج OTC
OTC_BOLLINGER_STD = 2.2      # معامل الانحراف المعياري لمؤشر بولنجر لأزواج OTC

# Constants for regular pairs analysis
REGULAR_RSI_PERIOD = 14      # فترة مؤشر RSI التقليدية
REGULAR_EMA_SHORT_PERIOD = 9  # فترة المتوسط المتحرك الأسي القصير التقليدية
REGULAR_EMA_MEDIUM_PERIOD = 21  # فترة المتوسط المتحرك الأسي المتوسط التقليدية
REGULAR_MACD_FAST = 12        # فترة MACD السريع التقليدية
REGULAR_MACD_SLOW = 26        # فترة MACD البطيء التقليدية
REGULAR_BOLLINGER_STD = 2.0   # معامل الانحراف المعياري لمؤشر بولنجر التقليدي


class AdvancedOTCAnalyzer:
    """محلل متقدم لأزواج OTC مع مؤشرات فنية متعددة ونظام فلترة متعدد المراحل"""

    def __init__(self):
        """تهيئة المحلل المتقدم لأزواج OTC"""
        logger.info("تهيئة محلل أزواج OTC المتقدم")

    def analyze_pair(self, candles, pair_symbol, is_otc=False):
        """
        تحليل شامل للزوج باستخدام مؤشرات فنية متعددة ونظام فلترة متعدد المراحل
        
        Args:
            candles: بيانات الشموع
            pair_symbol: رمز الزوج
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            dict: نتائج التحليل الشامل
        """
        # استخراج بيانات السعر
        closes = self._extract_close_prices(candles)
        opens = self._extract_open_prices(candles)
        highs = self._extract_high_prices(candles)
        lows = self._extract_low_prices(candles)
        
        if len(closes) < 30:
            logger.warning(f"بيانات غير كافية لتحليل {pair_symbol}. نحتاج 30 شمعة على الأقل.")
            return {"error": "بيانات غير كافية للتحليل الدقيق"}
        
        # المرحلة 1: تحليل المؤشرات الفنية
        technical_indicators = self._analyze_technical_indicators(
            closes, opens, highs, lows, pair_symbol, is_otc
        )
        
        # المرحلة 2: تحليل اتجاه السوق
        market_trend = self._analyze_market_trend(closes, is_otc)
        
        # المرحلة 3: التحقق من أنماط الانعكاس
        reversal_patterns = self._check_reversal_patterns(
            candles, closes, opens, highs, lows, is_otc
        )
        
        # تحديد الاتجاه والثقة
        direction, confidence, signals_breakdown = self._determine_direction_and_confidence(
            technical_indicators, market_trend, reversal_patterns, is_otc
        )
        
        # تحديد نقاط الدعم والمقاومة
        support_resistance = self._identify_support_resistance(
            candles, closes, lows, highs, is_otc
        )
        
        # تحسين الثقة بناءً على خصائص الزوج
        confidence = self._enhance_pair_specific_confidence(
            pair_symbol, confidence, direction, is_otc
        )
        
        # تقييم جودة الإشارة النهائية
        signal_quality = self._evaluate_signal_quality(
            direction, confidence, technical_indicators, market_trend, reversal_patterns
        )
        
        # التشخيص النهائي
        analysis_details = {
            "direction": direction,
            "confidence": confidence,
            "market_trend": market_trend,
            "technical_indicators": technical_indicators,
            "reversal_patterns": reversal_patterns,
            "signal_quality": signal_quality,
            "signals_breakdown": signals_breakdown,
            "support_resistance": support_resistance
        }
        
        return analysis_details

    def _extract_close_prices(self, candles):
        """استخراج أسعار الإغلاق من بيانات الشموع"""
        return np.array([candle['close'] for candle in candles])
        
    def _extract_open_prices(self, candles):
        """استخراج أسعار الافتتاح من بيانات الشموع"""
        return np.array([candle['open'] for candle in candles])
        
    def _extract_high_prices(self, candles):
        """استخراج أعلى الأسعار من بيانات الشموع"""
        return np.array([candle['high'] for candle in candles])
        
    def _extract_low_prices(self, candles):
        """استخراج أدنى الأسعار من بيانات الشموع"""
        return np.array([candle['low'] for candle in candles])

    def _analyze_technical_indicators(self, closes, opens, highs, lows, pair_symbol, is_otc):
        """
        تحليل المؤشرات الفنية للزوج
        
        Args:
            closes: سلسلة أسعار الإغلاق
            opens: سلسلة أسعار الافتتاح
            highs: سلسلة أعلى الأسعار
            lows: سلسلة أدنى الأسعار
            pair_symbol: رمز الزوج
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            dict: نتائج تحليل المؤشرات الفنية
        """
        # تحديد معلمات المؤشرات بناءً على نوع الزوج
        rsi_period = OTC_RSI_PERIOD if is_otc else REGULAR_RSI_PERIOD
        ema_short_period = OTC_EMA_SHORT_PERIOD if is_otc else REGULAR_EMA_SHORT_PERIOD
        ema_medium_period = OTC_EMA_MEDIUM_PERIOD if is_otc else REGULAR_EMA_MEDIUM_PERIOD
        macd_fast = OTC_MACD_FAST if is_otc else REGULAR_MACD_FAST
        macd_slow = OTC_MACD_SLOW if is_otc else REGULAR_MACD_SLOW
        bollinger_std = OTC_BOLLINGER_STD if is_otc else REGULAR_BOLLINGER_STD
        
        # حساب المؤشرات
        rsi = self._calculate_rsi(closes, rsi_period)
        ema_short = self._calculate_ema(closes, ema_short_period)
        ema_medium = self._calculate_ema(closes, ema_medium_period)
        macd_line, signal_line, histogram = self._calculate_macd(closes, macd_fast, macd_slow)
        upper_band, middle_band, lower_band = self._calculate_bollinger_bands(closes, bollinger_std)
        
        # حساب نمط الشموع
        candle_pattern = self._identify_candle_pattern(opens, closes, highs, lows)
        
        # تحليل توزيع الحجم (إذا كان متاحًا)
        volume_analysis = {"available": False}
        
        return {
            "rsi": {
                "value": rsi[-1] if len(rsi) > 0 else None,
                "signal": "BUY" if rsi[-1] < 30 else "SELL" if rsi[-1] > 70 else "NEUTRAL",
                "strength": self._calculate_rsi_strength(rsi[-1])
            },
            "ema": {
                "short": ema_short[-1] if len(ema_short) > 0 else None,
                "medium": ema_medium[-1] if len(ema_medium) > 0 else None,
                "signal": "BUY" if ema_short[-1] > ema_medium[-1] else "SELL" if ema_short[-1] < ema_medium[-1] else "NEUTRAL",
                "strength": self._calculate_ema_strength(ema_short, ema_medium)
            },
            "macd": {
                "line": macd_line[-1] if len(macd_line) > 0 else None,
                "signal": signal_line[-1] if len(signal_line) > 0 else None,
                "histogram": histogram[-1] if len(histogram) > 0 else None,
                "signal": self._get_macd_signal(macd_line, signal_line, histogram),
                "strength": self._calculate_macd_strength(macd_line, signal_line, histogram)
            },
            "bollinger": {
                "upper": upper_band[-1] if len(upper_band) > 0 else None,
                "middle": middle_band[-1] if len(middle_band) > 0 else None,
                "lower": lower_band[-1] if len(lower_band) > 0 else None,
                "signal": self._get_bollinger_signal(closes[-1], upper_band[-1], lower_band[-1]),
                "strength": self._calculate_bollinger_strength(closes[-1], upper_band[-1], middle_band[-1], lower_band[-1])
            },
            "candle_pattern": candle_pattern,
            "volume_analysis": volume_analysis
        }
        
    def _calculate_rsi(self, prices, period):
        """
        حساب مؤشر القوة النسبية (RSI)
        
        Args:
            prices: سلسلة الأسعار
            period: الفترة
            
        Returns:
            np.array: قيم مؤشر RSI
        """
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down if down != 0 else float('inf')
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100./(1. + rs)

        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up/down if down != 0 else float('inf')
            rsi[i] = 100. - 100./(1. + rs)
            
        return rsi
    
    def _calculate_ema(self, prices, period):
        """
        حساب المتوسط المتحرك الأسي (EMA)
        
        Args:
            prices: سلسلة الأسعار
            period: الفترة
            
        Returns:
            np.array: قيم EMA
        """
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
            
        return ema
    
    def _calculate_macd(self, prices, fast_period, slow_period, signal_period=9):
        """
        حساب مؤشر MACD
        
        Args:
            prices: سلسلة الأسعار
            fast_period: فترة خط MACD السريع
            slow_period: فترة خط MACD البطيء
            signal_period: فترة خط الإشارة
            
        Returns:
            tuple: (خط MACD، خط الإشارة، الهيستوجرام)
        """
        ema_fast = self._calculate_ema(prices, fast_period)
        ema_slow = self._calculate_ema(prices, slow_period)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices, std_dev=2.0, period=20):
        """
        حساب مؤشر البولنجر باند
        
        Args:
            prices: سلسلة الأسعار
            std_dev: معامل الانحراف المعياري
            period: الفترة
            
        Returns:
            tuple: (النطاق العلوي، النطاق المتوسط، النطاق السفلي)
        """
        middle_band = np.zeros_like(prices)
        for i in range(len(prices)):
            if i < period - 1:
                middle_band[i] = np.mean(prices[:i+1])
            else:
                middle_band[i] = np.mean(prices[i-period+1:i+1])
        
        upper_band = np.zeros_like(prices)
        lower_band = np.zeros_like(prices)
        
        for i in range(len(prices)):
            if i < period - 1:
                std = np.std(prices[:i+1])
            else:
                std = np.std(prices[i-period+1:i+1])
                
            upper_band[i] = middle_band[i] + std_dev * std
            lower_band[i] = middle_band[i] - std_dev * std
            
        return upper_band, middle_band, lower_band
    
    def _identify_candle_pattern(self, opens, closes, highs, lows):
        """
        تحديد نمط الشموع
        
        Args:
            opens: أسعار الافتتاح
            closes: أسعار الإغلاق
            highs: أعلى الأسعار
            lows: أدنى الأسعار
            
        Returns:
            dict: معلومات نمط الشموع
        """
        n = len(opens)
        if n < 3:
            return {"pattern": "غير محدد", "signal": "NEUTRAL", "strength": 0}
        
        # تحقق من أنماط الشموع الانعكاسية
        # 1. نمط الدوجي
        last_candle_body = abs(closes[-1] - opens[-1])
        last_candle_range = highs[-1] - lows[-1]
        is_doji = last_candle_body < 0.1 * last_candle_range
        
        # 2. نمط المطرقة
        last_candle_lower_shadow = min(opens[-1], closes[-1]) - lows[-1]
        last_candle_upper_shadow = highs[-1] - max(opens[-1], closes[-1])
        is_hammer = (
            last_candle_lower_shadow > 2 * last_candle_body and
            last_candle_upper_shadow < 0.1 * last_candle_range
        )
        
        # 3. نمط المطرقة المقلوبة
        is_inverted_hammer = (
            last_candle_upper_shadow > 2 * last_candle_body and
            last_candle_lower_shadow < 0.1 * last_candle_range
        )
        
        # 4. نمط البلع
        is_bullish_engulfing = (
            opens[-2] > closes[-2] and  # شمعة هابطة
            closes[-1] > opens[-1] and  # شمعة صاعدة
            opens[-1] < closes[-2] and  # فتح أقل من الإغلاق السابق
            closes[-1] > opens[-2]      # إغلاق أكبر من الفتح السابق
        )
        
        is_bearish_engulfing = (
            opens[-2] < closes[-2] and  # شمعة صاعدة
            closes[-1] < opens[-1] and  # شمعة هابطة
            opens[-1] > closes[-2] and  # فتح أكبر من الإغلاق السابق
            closes[-1] < opens[-2]      # إغلاق أقل من الفتح السابق
        )
        
        # تحديد النمط والإشارة
        pattern = "غير محدد"
        signal = "NEUTRAL"
        strength = 0
        
        if is_doji:
            pattern = "دوجي"
            # الدوجي يشير عادة إلى تردد السوق وإمكانية الانعكاس
            prev_trend = "صعودي" if closes[-2] > opens[-2] else "هبوطي"
            signal = "SELL" if prev_trend == "صعودي" else "BUY"
            strength = 60
        elif is_hammer:
            pattern = "مطرقة"
            # المطرقة بعد ترند هبوطي تعتبر إشارة انعكاس صعودي
            prev_trend = all(closes[i] < opens[i] for i in range(-4, -1))
            signal = "BUY" if prev_trend else "NEUTRAL"
            strength = 80 if prev_trend else 40
        elif is_inverted_hammer:
            pattern = "مطرقة مقلوبة"
            # المطرقة المقلوبة بعد ترند هبوطي تعتبر إشارة انعكاس صعودي
            prev_trend = all(closes[i] < opens[i] for i in range(-4, -1))
            signal = "BUY" if prev_trend else "NEUTRAL"
            strength = 70 if prev_trend else 30
        elif is_bullish_engulfing:
            pattern = "ابتلاع صعودي"
            signal = "BUY"
            strength = 90
        elif is_bearish_engulfing:
            pattern = "ابتلاع هبوطي"
            signal = "SELL"
            strength = 90
        else:
            # فحص الترند العام من آخر 3 شموع
            bullish_candles = sum(1 for i in range(-3, 0) if closes[i] > opens[i])
            bearish_candles = 3 - bullish_candles
            
            if bullish_candles == 3:
                pattern = "3 شموع صاعدة متتالية"
                signal = "BUY"
                strength = 85
            elif bearish_candles == 3:
                pattern = "3 شموع هابطة متتالية"
                signal = "SELL"
                strength = 85
            elif bullish_candles > bearish_candles:
                pattern = "اتجاه صعودي قصير المدى"
                signal = "BUY"
                strength = 60
            elif bearish_candles > bullish_candles:
                pattern = "اتجاه هبوطي قصير المدى"
                signal = "SELL"
                strength = 60
            else:
                pattern = "متذبذب"
                signal = "NEUTRAL"
                strength = 20
        
        return {
            "pattern": pattern,
            "signal": signal,
            "strength": strength
        }

    def _analyze_market_trend(self, closes, is_otc):
        """
        تحليل اتجاه السوق
        
        Args:
            closes: سلسلة أسعار الإغلاق
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            dict: معلومات اتجاه السوق
        """
        # تحليل الاتجاه على المدى القصير (10 شموع)
        short_term_closes = closes[-10:] if len(closes) >= 10 else closes
        short_term_trend = "صعودي" if short_term_closes[-1] > short_term_closes[0] else "هبوطي"
        short_term_strength = abs(short_term_closes[-1] - short_term_closes[0]) / short_term_closes[0] * 100
        
        # تحليل الاتجاه على المدى المتوسط (20 شمعة)
        medium_term_closes = closes[-20:] if len(closes) >= 20 else closes
        medium_term_trend = "صعودي" if medium_term_closes[-1] > medium_term_closes[0] else "هبوطي"
        medium_term_strength = abs(medium_term_closes[-1] - medium_term_closes[0]) / medium_term_closes[0] * 100
        
        # للأزواج OTC، نركز أكثر على المدى القصير
        if is_otc:
            overall_signal = "BUY" if short_term_trend == "صعودي" else "SELL"
            overall_strength = short_term_strength * 0.7 + medium_term_strength * 0.3
        else:
            # للأزواج العادية، نمزج بين المدى القصير والمتوسط
            if short_term_trend == medium_term_trend:
                overall_signal = "BUY" if short_term_trend == "صعودي" else "SELL"
                overall_strength = (short_term_strength + medium_term_strength) / 2
            else:
                # في حالة اختلاف الاتجاهات، نعطي الأفضلية للمدى القصير
                overall_signal = "BUY" if short_term_trend == "صعودي" else "SELL"
                overall_strength = short_term_strength * 0.6 + medium_term_strength * 0.4
        
        # تحويل القوة إلى نسبة مئوية محدودة بـ 100
        overall_strength = min(100, overall_strength)
        
        return {
            "short_term": {
                "trend": short_term_trend,
                "strength": short_term_strength
            },
            "medium_term": {
                "trend": medium_term_trend,
                "strength": medium_term_strength
            },
            "overall": {
                "signal": overall_signal,
                "strength": overall_strength
            }
        }
    
    def _check_reversal_patterns(self, candles, closes, opens, highs, lows, is_otc):
        """
        التحقق من أنماط الانعكاس
        
        Args:
            candles: بيانات الشموع
            closes: سلسلة أسعار الإغلاق
            opens: سلسلة أسعار الافتتاح
            highs: سلسلة أعلى الأسعار
            lows: سلسلة أدنى الأسعار
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            dict: معلومات أنماط الانعكاس
        """
        # البحث عن انعكاسات محتملة بناءً على أنماط السعر
        patterns = []
        
        # 1. فحص نمط Double Top (قمة مزدوجة) - نمط انعكاس هبوطي
        if len(highs) >= 10:
            recent_highs = highs[-10:]
            high_points = [i for i in range(1, len(recent_highs)-1) if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]]
            if len(high_points) >= 2:
                highest_points = sorted(high_points, key=lambda i: recent_highs[i], reverse=True)[:2]
                if abs(recent_highs[highest_points[0]] - recent_highs[highest_points[1]]) < 0.001 * recent_highs[highest_points[0]]:
                    patterns.append({"pattern": "قمة مزدوجة", "signal": "SELL", "strength": 85})
        
        # 2. فحص نمط Double Bottom (قاع مزدوج) - نمط انعكاس صعودي
        if len(lows) >= 10:
            recent_lows = lows[-10:]
            low_points = [i for i in range(1, len(recent_lows)-1) if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]]
            if len(low_points) >= 2:
                lowest_points = sorted(low_points, key=lambda i: recent_lows[i])[:2]
                if abs(recent_lows[lowest_points[0]] - recent_lows[lowest_points[1]]) < 0.001 * recent_lows[lowest_points[0]]:
                    patterns.append({"pattern": "قاع مزدوج", "signal": "BUY", "strength": 85})
        
        # 3. فحص نمط Head and Shoulders (رأس وكتفين) - انعكاس هبوطي
        if len(highs) >= 15:
            # بحث مبسط عن نمط الرأس والكتفين
            # تحتاج إلى 3 قمم متتالية، القمة الوسطى أعلى من الاثنتين الأخريين
            peaks = [i for i in range(1, len(highs)-1) if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
            if len(peaks) >= 3:
                for i in range(len(peaks)-2):
                    left_shoulder = peaks[i]
                    head = peaks[i+1]
                    right_shoulder = peaks[i+2]
                    if highs[head] > highs[left_shoulder] and highs[head] > highs[right_shoulder] and abs(highs[left_shoulder] - highs[right_shoulder]) < 0.01 * highs[head]:
                        patterns.append({"pattern": "رأس وكتفين", "signal": "SELL", "strength": 90})
        
        # 4. فحص انعكاس المؤشرات الفنية
        # مثلاً، إذا كان RSI يظهر تشبعًا شرائيًا أو بيعيًا
        if len(closes) >= 14:
            rsi = self._calculate_rsi(closes, 14)
            
            if rsi[-1] > 70:  # تشبع شرائي
                patterns.append({"pattern": "تشبع شرائي في مؤشر RSI", "signal": "SELL", "strength": 75})
            elif rsi[-1] < 30:  # تشبع بيعي
                patterns.append({"pattern": "تشبع بيعي في مؤشر RSI", "signal": "BUY", "strength": 75})
        
        # 5. فحص نمط الانعكاس بناءً على شموع الدوجي أو نجمة المساء/الصباح
        if len(closes) >= 3 and len(opens) >= 3:
            # الشمعة 1: شمعة طويلة
            # الشمعة 2: دوجي (جسم صغير)
            # الشمعة 3: شمعة عكسية
            
            # حساب طول جسم الشموع
            body1 = abs(closes[-3] - opens[-3])
            body2 = abs(closes[-2] - opens[-2])
            body3 = abs(closes[-1] - opens[-1])
            
            # فحص نجمة المساء (انعكاس هبوطي)
            if (
                closes[-3] > opens[-3] and  # شمعة صاعدة
                body2 < 0.3 * body1 and     # شمعة صغيرة/دوجي
                closes[-1] < opens[-1] and  # شمعة هابطة
                closes[-1] < opens[-3]       # الإغلاق أقل من فتح الشمعة الأولى
            ):
                patterns.append({"pattern": "نجمة المساء", "signal": "SELL", "strength": 85})
            
            # فحص نجمة الصباح (انعكاس صعودي)
            if (
                closes[-3] < opens[-3] and  # شمعة هابطة
                body2 < 0.3 * body1 and     # شمعة صغيرة/دوجي
                closes[-1] > opens[-1] and  # شمعة صاعدة
                closes[-1] > opens[-3]       # الإغلاق أعلى من فتح الشمعة الأولى
            ):
                patterns.append({"pattern": "نجمة الصباح", "signal": "BUY", "strength": 85})
        
        # تحليل النمط الأكثر قوة وأهمية
        if patterns:
            strongest_pattern = max(patterns, key=lambda x: x["strength"])
            has_reversal = True
            reversal_signal = strongest_pattern["signal"]
            reversal_strength = strongest_pattern["strength"]
            pattern_description = strongest_pattern["pattern"]
        else:
            has_reversal = False
            reversal_signal = "NEUTRAL"
            reversal_strength = 0
            pattern_description = "لا يوجد نمط انعكاس"
        
        return {
            "has_reversal": has_reversal,
            "signal": reversal_signal,
            "strength": reversal_strength,
            "pattern": pattern_description,
            "all_patterns": patterns
        }
    
    def _determine_direction_and_confidence(self, technical_indicators, market_trend, reversal_patterns, is_otc):
        """
        تحديد الاتجاه ومستوى الثقة
        
        Args:
            technical_indicators: نتائج تحليل المؤشرات الفنية
            market_trend: نتائج تحليل اتجاه السوق
            reversal_patterns: نتائج فحص أنماط الانعكاس
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            tuple: (الاتجاه، مستوى الثقة، تفصيل الإشارات)
        """
        signals = []
        
        # جمع الإشارات من المؤشرات المختلفة مع الأوزان
        if technical_indicators["rsi"]["value"] is not None:
            signals.append({
                "source": "RSI",
                "signal": technical_indicators["rsi"]["signal"],
                "weight": 0.15,
                "strength": technical_indicators["rsi"]["strength"]
            })
        
        if technical_indicators["ema"]["short"] is not None and technical_indicators["ema"]["medium"] is not None:
            signals.append({
                "source": "EMA",
                "signal": technical_indicators["ema"]["signal"],
                "weight": 0.20,
                "strength": technical_indicators["ema"]["strength"]
            })
        
        if technical_indicators["macd"]["line"] is not None:
            signals.append({
                "source": "MACD",
                "signal": technical_indicators["macd"]["signal"],
                "weight": 0.20,
                "strength": technical_indicators["macd"]["strength"]
            })
        
        if technical_indicators["bollinger"]["upper"] is not None:
            signals.append({
                "source": "Bollinger Bands",
                "signal": technical_indicators["bollinger"]["signal"],
                "weight": 0.15,
                "strength": technical_indicators["bollinger"]["strength"]
            })
        
        # إضافة إشارة نمط الشموع
        signals.append({
            "source": "Candle Pattern",
            "signal": technical_indicators["candle_pattern"]["signal"],
            "weight": 0.15,
            "strength": technical_indicators["candle_pattern"]["strength"]
        })
        
        # إضافة إشارة اتجاه السوق
        signals.append({
            "source": "Market Trend",
            "signal": market_trend["overall"]["signal"],
            "weight": 0.25,
            "strength": market_trend["overall"]["strength"]
        })
        
        # التحقق من أنماط الانعكاس (تأثير قوي إذا وجدت)
        if reversal_patterns["has_reversal"]:
            signals.append({
                "source": "Reversal Pattern",
                "signal": reversal_patterns["signal"],
                "weight": 0.30,  # وزن أعلى لأنماط الانعكاس
                "strength": reversal_patterns["strength"]
            })
            # تعديل أوزان الإشارات الأخرى
            for signal in signals[:-1]:  # تجاهل الإشارة الأخيرة (نمط الانعكاس)
                signal["weight"] *= 0.7  # تخفيض وزن الإشارات الأخرى
        
        # حساب وزن كل اتجاه
        buy_weight = sum(signal["weight"] * signal["strength"] / 100 for signal in signals if signal["signal"] == "BUY")
        sell_weight = sum(signal["weight"] * signal["strength"] / 100 for signal in signals if signal["signal"] == "SELL")
        neutral_weight = sum(signal["weight"] * signal["strength"] / 100 for signal in signals if signal["signal"] == "NEUTRAL")
        
        # تطبيق المعامل الإضافي لأزواج OTC
        if is_otc:
            # زيادة وزن الإشارات قصيرة المدى للأزواج OTC
            buy_weight *= 1.1 if market_trend["short_term"]["trend"] == "صعودي" else 0.9
            sell_weight *= 1.1 if market_trend["short_term"]["trend"] == "هبوطي" else 0.9
        
        # تحديد الاتجاه النهائي
        total_weight = buy_weight + sell_weight + neutral_weight
        buy_percentage = 0
        sell_percentage = 0
        
        if total_weight > 0:
            buy_percentage = (buy_weight / total_weight) * 100
            sell_percentage = (sell_weight / total_weight) * 100
            
            if buy_percentage > sell_percentage and buy_percentage > 60:
                direction = "BUY"
                confidence = buy_percentage
            elif sell_percentage > buy_percentage and sell_percentage > 60:
                direction = "SELL"
                confidence = sell_percentage
            else:
                direction = "NEUTRAL"
                confidence = max(buy_percentage, sell_percentage)
        else:
            direction = "NEUTRAL"
            confidence = 50
        
        # تعديل الثقة لتكون بين 50 و100
        confidence = max(50, min(100, confidence))
        
        # تحضير تفصيل الإشارات للتقرير
        signals_breakdown = {
            "buy_weight": buy_weight,
            "sell_weight": sell_weight,
            "neutral_weight": neutral_weight,
            "buy_percentage": buy_percentage,
            "sell_percentage": sell_percentage,
            "signals": signals
        }
        
        return direction, confidence, signals_breakdown
    
    def _identify_support_resistance(self, candles, closes, lows, highs, is_otc):
        """
        تحديد نقاط الدعم والمقاومة
        
        Args:
            candles: بيانات الشموع
            closes: سلسلة أسعار الإغلاق
            lows: سلسلة أدنى الأسعار
            highs: سلسلة أعلى الأسعار
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            dict: معلومات نقاط الدعم والمقاومة
        """
        # طريقة مبسطة لحساب مستويات الدعم والمقاومة
        if len(candles) < 20:
            return {
                "support_levels": [],
                "resistance_levels": [],
                "current_price": closes[-1] if len(closes) > 0 else None
            }
        
        # استخدام الشموع الأخيرة فقط
        n = min(50, len(candles))
        recent_candles = candles[-n:]
        recent_lows = lows[-n:]
        recent_highs = highs[-n:]
        current_price = closes[-1]
        
        # العثور على نقاط القاع المحلية (الدعم)
        support_points = []
        for i in range(1, n-1):
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
                support_points.append({
                    "price": recent_lows[i],
                    "time": recent_candles[i].get('time', i),
                    "strength": self._calculate_level_strength(recent_lows, i, "support", is_otc)
                })
        
        # العثور على نقاط القمة المحلية (المقاومة)
        resistance_points = []
        for i in range(1, n-1):
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
                resistance_points.append({
                    "price": recent_highs[i],
                    "time": recent_candles[i].get('time', i),
                    "strength": self._calculate_level_strength(recent_highs, i, "resistance", is_otc)
                })
        
        # تجميع النقاط القريبة
        support_levels = self._cluster_price_levels(support_points, current_price, is_otc)
        resistance_levels = self._cluster_price_levels(resistance_points, current_price, is_otc)
        
        # ترتيب المستويات حسب القرب من السعر الحالي
        support_levels = sorted(support_levels, key=lambda x: abs(x["price"] - current_price))
        resistance_levels = sorted(resistance_levels, key=lambda x: abs(x["price"] - current_price))
        
        # تصفية المستويات البعيدة جداً عن السعر الحالي
        max_distance = 0.05 * current_price  # 5% كحد أقصى
        support_levels = [level for level in support_levels if level["price"] < current_price and abs(level["price"] - current_price) <= max_distance]
        resistance_levels = [level for level in resistance_levels if level["price"] > current_price and abs(level["price"] - current_price) <= max_distance]
        
        # الاحتفاظ بأقوى 3 مستويات فقط
        support_levels = sorted(support_levels, key=lambda x: x["strength"], reverse=True)[:3]
        resistance_levels = sorted(resistance_levels, key=lambda x: x["strength"], reverse=True)[:3]
        
        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "current_price": current_price
        }
    
    def _cluster_price_levels(self, price_points, current_price, is_otc):
        """
        تجميع مستويات الأسعار المتقاربة
        
        Args:
            price_points: نقاط الأسعار
            current_price: السعر الحالي
            is_otc: ما إذا كان زوج OTC
            
        Returns:
            list: مستويات الأسعار المجمعة
        """
        if not price_points:
            return []
        
        # تحديد عتبة التجميع (أصغر للأزواج OTC)
        clustering_threshold = 0.0005 if is_otc else 0.001
        threshold = current_price * clustering_threshold
        
        # فرز النقاط حسب السعر
        sorted_points = sorted(price_points, key=lambda x: x["price"])
        clusters = []
        current_cluster = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i]["price"] - current_cluster[-1]["price"] <= threshold:
                current_cluster.append(sorted_points[i])
            else:
                # إنشاء مستوى جديد من المجموعة الحالية
                avg_price = sum(point["price"] for point in current_cluster) / len(current_cluster)
                avg_strength = sum(point["strength"] for point in current_cluster) / len(current_cluster)
                # زيادة القوة بناءً على عدد النقاط في المجموعة
                combined_strength = avg_strength * (1 + 0.1 * (len(current_cluster) - 1))
                
                clusters.append({
                    "price": avg_price,
                    "strength": combined_strength,
                    "count": len(current_cluster),
                    "times": [point["time"] for point in current_cluster]
                })
                
                current_cluster = [sorted_points[i]]
        
        # إضافة المجموعة الأخيرة
        if current_cluster:
            avg_price = sum(point["price"] for point in current_cluster) / len(current_cluster)
            avg_strength = sum(point["strength"] for point in current_cluster) / len(current_cluster)
            combined_strength = avg_strength * (1 + 0.1 * (len(current_cluster) - 1))
            
            clusters.append({
                "price": avg_price,
                "strength": combined_strength,
                "count": len(current_cluster),
                "times": [point["time"] for point in current_cluster]
            })
        
        return clusters
    
    def _calculate_level_strength(self, prices, index, level_type, is_otc):
        """
        حساب قوة مستوى الدعم أو المقاومة
        
        Args:
            prices: سلسلة الأسعار
            index: موقع المستوى
            level_type: نوع المستوى (دعم أو مقاومة)
            is_otc: ما إذا كان زوج OTC
            
        Returns:
            float: قوة المستوى
        """
        price = prices[index]
        n = len(prices)
        
        # عدد المرات التي يتفاعل فيها السعر مع هذا المستوى
        touches = 0
        
        # نطاق البحث (أوسع للأزواج OTC)
        range_factor = 0.0005 if is_otc else 0.001
        price_range = price * range_factor
        
        for i in range(n):
            if abs(prices[i] - price) <= price_range:
                touches += 1
        
        # قوة المستوى تعتمد على عدد ملامسات السعر وقرب المستوى من السعر الحالي
        strength = touches * 10  # 10 نقاط لكل ملامسة
        
        # تعديل القوة للأزواج OTC
        if is_otc:
            strength *= 1.2  # زيادة 20% لأزواج OTC
        
        return min(100, strength)  # الحد الأقصى 100
    
    def _enhance_pair_specific_confidence(self, pair_symbol, confidence, direction, is_otc):
        """
        تعزيز الثقة بناءً على خصائص الزوج المحددة
        
        Args:
            pair_symbol: رمز الزوج
            confidence: مستوى الثقة الأولي
            direction: اتجاه الإشارة
            is_otc: ما إذا كان الزوج من أزواج OTC
            
        Returns:
            float: مستوى الثقة المعزز
        """
        # قاموس معلمات خاصة بكل زوج OTC
        pair_specific_params = {
            "EUR/JPY-OTC": {
                "confidence_boost": 8,
                "buy_bias": 1.0,  # لا تحيز
                "sell_bias": 1.0   # لا تحيز
            },
            "AUD/CAD-OTC": {
                "confidence_boost": 6,
                "buy_bias": 1.1,  # تحيز إيجابي للشراء
                "sell_bias": 0.9   # تحيز سلبي للبيع
            },
            "BHD/CNY-OTC": {
                "confidence_boost": 7,
                "buy_bias": 1.05,  # تحيز إيجابي قليل للشراء
                "sell_bias": 0.95   # تحيز سلبي قليل للبيع
            },
            # يمكن إضافة المزيد من الأزواج هنا
        }
        
        # المعلمات الافتراضية
        default_params = {
            "confidence_boost": 5,
            "buy_bias": 1.0,
            "sell_bias": 1.0
        }
        
        # الحصول على معلمات الزوج المحدد أو الافتراضية
        params = pair_specific_params.get(pair_symbol, default_params)
        
        # تطبيق التعزيز المعتمد على الزوج
        if is_otc:
            # زيادة الثقة للأزواج OTC
            confidence += params["confidence_boost"]
            
            # تطبيق التحيز حسب الاتجاه
            if direction == "BUY":
                confidence *= params["buy_bias"]
            elif direction == "SELL":
                confidence *= params["sell_bias"]
        
        # تأكد من أن الثقة في النطاق الصحيح
        confidence = max(50, min(100, confidence))
        
        return confidence
    
    def _evaluate_signal_quality(self, direction, confidence, technical_indicators, market_trend, reversal_patterns):
        """
        تقييم جودة الإشارة النهائية
        
        Args:
            direction: اتجاه الإشارة
            confidence: مستوى الثقة
            technical_indicators: نتائج تحليل المؤشرات الفنية
            market_trend: نتائج تحليل اتجاه السوق
            reversal_patterns: نتائج فحص أنماط الانعكاس
            
        Returns:
            dict: تقييم جودة الإشارة
        """
        # تحديد عوامل الجودة
        quality_factors = {}
        
        # 1. اتساق الإشارات
        consistent_signals = 0
        total_signals = 0
        
        # فحص المؤشرات الفنية
        for indicator in ["rsi", "ema", "macd", "bollinger"]:
            if technical_indicators[indicator]["signal"] != "NEUTRAL":
                total_signals += 1
                if technical_indicators[indicator]["signal"] == direction:
                    consistent_signals += 1
        
        # إضافة نمط الشموع
        if technical_indicators["candle_pattern"]["signal"] != "NEUTRAL":
            total_signals += 1
            if technical_indicators["candle_pattern"]["signal"] == direction:
                consistent_signals += 1
        
        # إضافة اتجاه السوق
        total_signals += 1
        if market_trend["overall"]["signal"] == direction:
            consistent_signals += 1
        
        # إضافة أنماط الانعكاس إذا وجدت
        if reversal_patterns["has_reversal"]:
            total_signals += 1
            if reversal_patterns["signal"] == direction:
                consistent_signals += 1
        
        consistency_score = (consistent_signals / total_signals * 100) if total_signals > 0 else 0
        quality_factors["consistency"] = consistency_score
        
        # 2. قوة الثقة
        confidence_score = confidence
        quality_factors["confidence"] = confidence_score
        
        # 3. قوة اتجاه السوق
        market_strength = market_trend["overall"]["strength"]
        quality_factors["market_strength"] = market_strength
        
        # 4. وجود أنماط انعكاس تدعم الاتجاه
        reversal_score = 0
        if reversal_patterns["has_reversal"] and reversal_patterns["signal"] == direction:
            reversal_score = reversal_patterns["strength"]
        quality_factors["reversal_support"] = reversal_score
        
        # حساب الجودة الإجمالية (وزن لكل عامل)
        overall_quality = (
            consistency_score * 0.35 +
            confidence_score * 0.3 +
            market_strength * 0.25 +
            reversal_score * 0.1
        )
        
        # تقييم لفظي للجودة
        if overall_quality >= 90:
            quality_rating = "ممتازة"
        elif overall_quality >= 80:
            quality_rating = "جيدة جداً"
        elif overall_quality >= 70:
            quality_rating = "جيدة"
        elif overall_quality >= 60:
            quality_rating = "متوسطة"
        else:
            quality_rating = "ضعيفة"
        
        return {
            "overall_quality": overall_quality,
            "quality_rating": quality_rating,
            "factors": quality_factors
        }
    
    def _calculate_rsi_strength(self, rsi_value):
        """حساب قوة إشارة مؤشر RSI"""
        if rsi_value is None:
            return 0
            
        if rsi_value <= 30:
            # تشبع بيعي، قوة إشارة شراء عالية
            return 100 - (rsi_value / 30 * 20)  # 80-100
        elif rsi_value >= 70:
            # تشبع شرائي، قوة إشارة بيع عالية
            return 80 + ((rsi_value - 70) / 30 * 20)  # 80-100
        elif rsi_value < 45:
            # منطقة بيع معتدلة
            return 50 + ((45 - rsi_value) / 15 * 30)  # 50-80
        elif rsi_value > 55:
            # منطقة شراء معتدلة
            return 50 + ((rsi_value - 55) / 15 * 30)  # 50-80
        else:
            # منطقة محايدة
            return 50 - abs(rsi_value - 50)  # 40-50
    
    def _calculate_ema_strength(self, ema_short, ema_medium):
        """حساب قوة إشارة المتوسطات المتحركة"""
        if len(ema_short) == 0 or len(ema_medium) == 0:
            return 0
            
        # حساب الفرق النسبي بين المتوسطين
        diff_percent = abs(ema_short[-1] - ema_medium[-1]) / ema_medium[-1] * 100
        
        # حساب اتجاه المتوسطات (هل المتوسط القصير في تسارع عن المتوسط المتوسط؟)
        if len(ema_short) >= 3 and len(ema_medium) >= 3:
            short_prev_diff = ema_short[-2] - ema_medium[-2]
            short_curr_diff = ema_short[-1] - ema_medium[-1]
            acceleration = short_curr_diff - short_prev_diff
            
            # إشارة قوية عندما يكون هناك تسارع في الاتجاه
            if (short_curr_diff > 0 and acceleration > 0) or (short_curr_diff < 0 and acceleration < 0):
                acceleration_factor = min(1.5, 1 + abs(acceleration) / abs(short_prev_diff) if abs(short_prev_diff) > 0 else 1)
            else:
                acceleration_factor = 1
        else:
            acceleration_factor = 1
        
        # القوة الأساسية تعتمد على الفرق النسبي
        base_strength = min(100, 50 + diff_percent * 10)
        
        # القوة النهائية مع عامل التسارع
        strength = min(100, base_strength * acceleration_factor)
        
        return strength
    
    def _get_macd_signal(self, macd_line, signal_line, histogram):
        """تحديد إشارة MACD"""
        if len(macd_line) < 2 or len(signal_line) < 2 or len(histogram) < 2:
            return "NEUTRAL"
            
        # إشارة الشراء: خط MACD يقطع خط الإشارة للأعلى
        if macd_line[-2] < signal_line[-2] and macd_line[-1] > signal_line[-1]:
            return "BUY"
        # إشارة البيع: خط MACD يقطع خط الإشارة للأسفل
        elif macd_line[-2] > signal_line[-2] and macd_line[-1] < signal_line[-1]:
            return "SELL"
        # إشارة شراء ضعيفة: الهيستوجرام يزداد في المنطقة الإيجابية
        elif histogram[-1] > 0 and histogram[-1] > histogram[-2]:
            return "BUY"
        # إشارة بيع ضعيفة: الهيستوجرام يزداد في المنطقة السلبية
        elif histogram[-1] < 0 and histogram[-1] < histogram[-2]:
            return "SELL"
        # لا إشارة واضحة
        else:
            return "NEUTRAL"
    
    def _calculate_macd_strength(self, macd_line, signal_line, histogram):
        """حساب قوة إشارة MACD"""
        if len(macd_line) < 2 or len(signal_line) < 2 or len(histogram) < 2:
            return 0
            
        # حساب الفرق النسبي بين خط MACD وخط الإشارة
        if abs(signal_line[-1]) > 0:
            diff_percent = abs(macd_line[-1] - signal_line[-1]) / abs(signal_line[-1]) * 100
        else:
            diff_percent = abs(macd_line[-1] - signal_line[-1]) * 100
        
        # قوة الإشارة الأساسية
        base_strength = min(100, 50 + diff_percent * 5)
        
        # تعديل القوة بناءً على حالة تقاطع MACD
        if (macd_line[-2] < signal_line[-2] and macd_line[-1] > signal_line[-1]) or (macd_line[-2] > signal_line[-2] and macd_line[-1] < signal_line[-1]):
            # تقاطع حديث - إشارة قوية
            crossing_factor = 1.2
        else:
            crossing_factor = 1
        
        # تعديل القوة بناءً على اتجاه الهيستوجرام
        if len(histogram) >= 3:
            if (histogram[-1] > histogram[-2] > histogram[-3] and histogram[-1] > 0) or (histogram[-1] < histogram[-2] < histogram[-3] and histogram[-1] < 0):
                # اتجاه قوي في الهيستوجرام
                histogram_factor = 1.2
            elif (histogram[-1] > histogram[-2] and histogram[-1] > 0) or (histogram[-1] < histogram[-2] and histogram[-1] < 0):
                # اتجاه معتدل في الهيستوجرام
                histogram_factor = 1.1
            else:
                histogram_factor = 1
        else:
            histogram_factor = 1
        
        # القوة النهائية
        strength = min(100, base_strength * crossing_factor * histogram_factor)
        
        return strength
    
    def _get_bollinger_signal(self, price, upper, lower):
        """تحديد إشارة بولنجر باند"""
        if price is None or upper is None or lower is None:
            return "NEUTRAL"
            
        # إشارة شراء: السعر يقترب من أو يلامس الحد السفلي
        if price <= lower * 1.005:  # بهامش 0.5%
            return "BUY"
        # إشارة بيع: السعر يقترب من أو يلامس الحد العلوي
        elif price >= upper * 0.995:  # بهامش 0.5%
            return "SELL"
        # لا إشارة واضحة
        else:
            return "NEUTRAL"
    
    def _calculate_bollinger_strength(self, price, upper, middle, lower):
        """حساب قوة إشارة بولنجر باند"""
        if price is None or upper is None or middle is None or lower is None:
            return 0
            
        # حساب النسبة المئوية من موقع السعر بين الحدين
        band_width = upper - lower
        if band_width > 0:
            position = (price - lower) / band_width
        else:
            return 50
        
        # إشارة شراء أقوى كلما اقترب السعر من الحد السفلي
        if position <= 0.3:
            buy_strength = 100 - position * 200  # 40-100
            return buy_strength
        # إشارة بيع أقوى كلما اقترب السعر من الحد العلوي
        elif position >= 0.7:
            sell_strength = 40 + (position - 0.7) * 200  # 40-100
            return sell_strength
        # قوة معتدلة في المنطقة الوسطى
        else:
            return 50 - abs(position - 0.5) * 20  # 40-50
    

def analyze_otc_pair(candles, pair_symbol):
    """
    تحليل زوج OTC باستخدام المحلل المتقدم
    
    Args:
        candles: بيانات الشموع
        pair_symbol: رمز الزوج
        
    Returns:
        dict: نتائج التحليل المتقدم
    """
    # تحديد ما إذا كان الزوج من أزواج OTC
    is_otc = "-OTC" in pair_symbol
    
    # إنشاء محلل أزواج OTC
    analyzer = AdvancedOTCAnalyzer()
    
    # تحليل الزوج
    analysis_results = analyzer.analyze_pair(candles, pair_symbol, is_otc)
    
    return analysis_results


def generate_trade_signal(analysis_results, pair_symbol, timeframe=1):
    """
    توليد إشارة تداول بناءً على نتائج التحليل
    
    Args:
        analysis_results: نتائج التحليل المتقدم
        pair_symbol: رمز الزوج
        timeframe: الإطار الزمني (بالدقائق)
        
    Returns:
        dict: إشارة التداول
    """
    # استخراج المعلومات الرئيسية من نتائج التحليل
    direction = analysis_results.get("direction", "NEUTRAL")
    confidence = analysis_results.get("confidence", 50)
    
    # إذا كانت الإشارة محايدة، نرجع None
    if direction == "NEUTRAL" or confidence < 60:
        return None
    
    # إنشاء التحليل النصي
    analysis_text = generate_analysis_text(analysis_results, pair_symbol)
    
    # إنشاء إشارة التداول
    from datetime import datetime, timedelta
    
    current_time = datetime.utcnow()
    entry_time = current_time + timedelta(minutes=2)
    # تقريب إلى أقرب دقيقة
    entry_time = entry_time.replace(second=0, microsecond=0)
    # تحويل إلى توقيت تركيا (UTC+3)
    turkey_time = entry_time + timedelta(hours=3)
    entry_time_str = turkey_time.strftime('%H:%M')
    
    signal = {
        "pair": pair_symbol,
        "direction": direction,
        "entry_time": entry_time_str,
        "duration": f"{timeframe} دقيقة",
        "expiry": f"{timeframe} min",
        "probability": f"{int(confidence)}%",
        "analysis_notes": analysis_text,
        "technical_indicators": get_technical_indicators_summary(analysis_results)
    }
    
    return signal


def generate_analysis_text(analysis_results, pair_symbol):
    """
    توليد نص تحليلي مفصل بناءً على نتائج التحليل
    
    Args:
        analysis_results: نتائج التحليل المتقدم
        pair_symbol: رمز الزوج
        
    Returns:
        str: النص التحليلي
    """
    # استخراج المعلومات الرئيسية
    direction = analysis_results.get("direction", "NEUTRAL")
    confidence = analysis_results.get("confidence", 50)
    market_trend = analysis_results.get("market_trend", {}).get("overall", {})
    signal_quality = analysis_results.get("signal_quality", {})
    technical_indicators = analysis_results.get("technical_indicators", {})
    reversal_patterns = analysis_results.get("reversal_patterns", {})
    
    # تحديد نوع الصياغة بناءً على الاتجاه
    if direction == "BUY":
        direction_ar = "شراء"
        color_ar = "أخضر"
    elif direction == "SELL":
        direction_ar = "بيع"
        color_ar = "أحمر"
    else:
        direction_ar = "محايد"
        color_ar = "رمادي"
    
    # تحديد قوة الإشارة
    quality_rating = signal_quality.get("quality_rating", "متوسطة")
    overall_quality = signal_quality.get("overall_quality", 50)
    
    # تحديد نمط السوق
    is_otc = "-OTC" in pair_symbol
    market_pattern = "أزواج OTC" if is_otc else "أزواج العملات الرئيسية"
    
    # بناء وصف المؤشرات الفنية
    indicators_description = ""
    
    # RSI
    if technical_indicators.get("rsi", {}).get("value") is not None:
        rsi_value = technical_indicators["rsi"]["value"]
        if rsi_value < 30:
            indicators_description += f"مؤشر القوة النسبية RSI في منطقة التشبع البيعي ({rsi_value:.1f}). "
        elif rsi_value > 70:
            indicators_description += f"مؤشر القوة النسبية RSI في منطقة التشبع الشرائي ({rsi_value:.1f}). "
    
    # EMA
    ema_signal = technical_indicators.get("ema", {}).get("signal")
    if ema_signal and ema_signal != "NEUTRAL":
        if ema_signal == "BUY":
            indicators_description += "المتوسط المتحرك الأسي القصير أعلى من المتوسط المتوسط. "
        else:
            indicators_description += "المتوسط المتحرك الأسي القصير أدنى من المتوسط المتوسط. "
    
    # MACD
    macd_signal = technical_indicators.get("macd", {}).get("signal")
    if macd_signal and macd_signal != "NEUTRAL":
        if macd_signal == "BUY":
            indicators_description += "مؤشر MACD يشير إلى قوة شرائية. "
        else:
            indicators_description += "مؤشر MACD يشير إلى قوة بيعية. "
    
    # نمط الشموع
    candle_pattern = technical_indicators.get("candle_pattern", {}).get("pattern")
    if candle_pattern and candle_pattern != "غير محدد":
        indicators_description += f"نمط الشموع: {candle_pattern}. "
    
    # أنماط الانعكاس
    reversal_pattern = reversal_patterns.get("pattern")
    if reversal_patterns.get("has_reversal", False):
        indicators_description += f"نمط انعكاس مكتشف: {reversal_pattern}. "
    
    # إنشاء النص التحليلي
    if overall_quality >= 80:
        strength_ar = "قوية جداً"
        pattern_ar = "ظهور إشارات قوية متعددة تدعم الاتجاه"
    elif overall_quality >= 70:
        strength_ar = "قوية"
        pattern_ar = "وجود عدة مؤشرات إيجابية تدعم الاتجاه"
    else:
        strength_ar = "معتدلة"
        pattern_ar = "تشكل اتجاه مع بعض الإشارات الداعمة"
    
    # تحديد مستوى الثقة
    if confidence >= 90:
        confidence_ar = "عالية جداً"
    elif confidence >= 80:
        confidence_ar = "عالية"
    elif confidence >= 70:
        confidence_ar = "متوسطة إلى عالية"
    else:
        confidence_ar = "متوسطة"
    
    # الجملة الأولى من التحليل
    analysis_text = f"إشارة {direction_ar} {strength_ar} مع نمط {pattern_ar}. "
    
    # إضافة وصف المؤشرات إذا وجد
    if indicators_description:
        analysis_text += f"{indicators_description}"
    
    # إضافة معلومات حول نمط الشموع
    is_oscillating = technical_indicators.get("candle_pattern", {}).get("pattern") == "متذبذب"
    if is_oscillating:
        analysis_text += f"السوق في حالة تذبذب، لكن الإشارة الأخيرة تشير إلى {direction_ar}. "
    else:
        analysis_text += f"تتشكل شموع {color_ar} على الرسم البياني تدل على اتجاه {direction_ar}. "
    
    # إضافة معلومات حول الاحتمالية
    market_trend_str = market_trend.get("signal", "NEUTRAL")
    if market_trend_str == direction:
        probability_ar = "مرتفعة جداً"
    else:
        probability_ar = "مرتفعة"
    
    analysis_text += f"الاحتمالية {probability_ar} بناءً على تحليل متعدد المؤشرات مع درجة ثقة {confidence_ar}."
    
    return analysis_text


def get_technical_indicators_summary(analysis_results):
    """
    الحصول على ملخص للمؤشرات الفنية
    
    Args:
        analysis_results: نتائج التحليل المتقدم
        
    Returns:
        dict: ملخص المؤشرات الفنية
    """
    technical_indicators = analysis_results.get("technical_indicators", {})
    
    # استخراج معلومات المؤشرات بتنسيق مختصر
    indicators_summary = {}
    
    # RSI
    if "rsi" in technical_indicators and technical_indicators["rsi"]["value"] is not None:
        rsi_value = technical_indicators["rsi"]["value"]
        rsi_signal = technical_indicators["rsi"]["signal"]
        indicators_summary["RSI"] = f"{rsi_value:.1f} ({rsi_signal})"
    
    # EMA
    if "ema" in technical_indicators and technical_indicators["ema"]["short"] is not None:
        ema_signal = technical_indicators["ema"]["signal"]
        indicators_summary["EMA"] = f"{ema_signal}"
    
    # MACD
    if "macd" in technical_indicators and technical_indicators["macd"]["line"] is not None:
        macd_signal = technical_indicators["macd"]["signal"]
        indicators_summary["MACD"] = f"{macd_signal}"
    
    # Bollinger Bands
    if "bollinger" in technical_indicators and technical_indicators["bollinger"]["upper"] is not None:
        bollinger_signal = technical_indicators["bollinger"]["signal"]
        indicators_summary["Bollinger"] = f"{bollinger_signal}"
    
    # Candle Pattern
    if "candle_pattern" in technical_indicators:
        pattern = technical_indicators["candle_pattern"]["pattern"]
        if pattern and pattern != "غير محدد":
            indicators_summary["Pattern"] = pattern
    
    return indicators_summary