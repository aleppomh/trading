"""
نظام تحليل أنماط الشموع اليابانية المتقدم
يستخدم للكشف عن أنماط انعكاس واستمرار الاتجاه في الشموع اليابانية
يساعد في تحسين دقة الإشارات وتصفية الإشارات الكاذبة
"""

import numpy as np
import logging

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CandlestickPatternAnalyzer:
    """محلل أنماط الشموع اليابانية المتقدم"""
    
    def __init__(self):
        """تهيئة محلل أنماط الشموع"""
        logger.info("تم تهيئة محلل أنماط الشموع اليابانية")
        
    def analyze_patterns(self, candles):
        """
        تحليل أنماط الشموع اليابانية في مجموعة من الشموع
        
        Args:
            candles: مصفوفة من الشموع، كل شمعة تحتوي على OHLC (الافتتاح، الأعلى، الأدنى، الإغلاق)
            
        Returns:
            dict: نتائج تحليل الأنماط، بما في ذلك الأنماط المكتشفة وقوتها واتجاهها
        """
        if len(candles) < 3:
            logger.warning("عدد الشموع غير كافٍ للتحليل، يجب توفير 3 شموع على الأقل")
            return {
                'patterns': [],
                'direction': 'NEUTRAL',
                'strength': 0,
                'description': 'بيانات غير كافية للتحليل'
            }
            
        # الحصول على الشموع الأخيرة للتحليل
        last_candle = candles[-1]  # آخر شمعة
        prev_candle = candles[-2]  # الشمعة قبل الأخيرة
        prev2_candle = candles[-3]  # الشمعة قبل قبل الأخيرة
        
        # تحليل الشموع
        patterns = []
        pattern_strength = 0
        pattern_direction = 'NEUTRAL'
        
        # حساب جسم وظلال الشمعة الأخيرة
        last_body_size = abs(last_candle['open'] - last_candle['close'])
        last_body_ratio = last_body_size / (last_candle['high'] - last_candle['low']) if (last_candle['high'] - last_candle['low']) > 0 else 0
        upper_shadow = last_candle['high'] - max(last_candle['open'], last_candle['close'])
        lower_shadow = min(last_candle['open'], last_candle['close']) - last_candle['low']
        
        # تحديد ما إذا كانت الشموع صاعدة أو هابطة
        is_last_bullish = last_candle['close'] > last_candle['open']
        is_prev_bullish = prev_candle['close'] > prev_candle['open']
        is_prev2_bullish = prev2_candle['close'] > prev2_candle['open']
        
        # تحديد الاتجاه العام للشموع الثلاث
        candle_trend = self._determine_candle_trend(candles[-5:] if len(candles) >= 5 else candles)
        
        # 1. نمط الابتلاع (Engulfing Pattern)
        engulfing = self._check_engulfing_pattern(last_candle, prev_candle, candle_trend)
        if engulfing['pattern_found']:
            patterns.append(engulfing)
            pattern_strength = max(pattern_strength, engulfing['strength'])
            pattern_direction = engulfing['direction']
        
        # 2. نمط المطرقة والمطرقة المقلوبة (Hammer & Inverted Hammer)
        hammer = self._check_hammer_pattern(last_candle, candle_trend)
        if hammer['pattern_found']:
            patterns.append(hammer)
            pattern_strength = max(pattern_strength, hammer['strength'])
            if pattern_direction == 'NEUTRAL':
                pattern_direction = hammer['direction']
        
        # 3. نمط نجمة المساء والصباح (Evening Star & Morning Star)
        star = self._check_star_pattern(last_candle, prev_candle, prev2_candle, candle_trend)
        if star['pattern_found']:
            patterns.append(star)
            pattern_strength = max(pattern_strength, star['strength'])
            pattern_direction = star['direction']  # نمط النجمة له أولوية أعلى
        
        # 4. نمط الدوجي (Doji)
        doji = self._check_doji_pattern(last_candle, candle_trend)
        if doji['pattern_found']:
            patterns.append(doji)
            if pattern_strength < doji['strength']:  # الدوجي له أولوية أقل
                pattern_strength = doji['strength']
                if pattern_direction == 'NEUTRAL':
                    pattern_direction = doji['direction']
        
        # 5. نمط الهاراكامي (Harami)
        harami = self._check_harami_pattern(last_candle, prev_candle, candle_trend)
        if harami['pattern_found']:
            patterns.append(harami)
            if pattern_strength < harami['strength']:  # الهاراكامي له أولوية متوسطة
                pattern_strength = harami['strength']
                if pattern_direction == 'NEUTRAL':
                    pattern_direction = harami['direction']
        
        # 6. نمط ثلاث جنود صاعد أو ثلاث غربان هابطة (Three White Soldiers / Three Black Crows)
        three_candles = self._check_three_candles_pattern(last_candle, prev_candle, prev2_candle)
        if three_candles['pattern_found']:
            patterns.append(three_candles)
            pattern_strength = max(pattern_strength, three_candles['strength'])
            pattern_direction = three_candles['direction']  # هذا النمط له أولوية عالية
        
        # إعداد النتيجة النهائية
        result = {
            'patterns': patterns,
            'direction': pattern_direction,
            'strength': pattern_strength,
            'description': self._generate_pattern_description(patterns)
        }
        
        return result
    
    def _determine_candle_trend(self, candles):
        """تحديد الاتجاه العام للشموع"""
        if len(candles) < 2:
            return 'NEUTRAL'
        
        closes = [candle['close'] for candle in candles]
        opens = [candle['open'] for candle in candles]
        
        # حساب متوسط أسعار الإغلاق والافتتاح
        avg_close = sum(closes) / len(closes)
        first_close = closes[0]
        last_close = closes[-1]
        
        # تحديد الاتجاه بناءً على الفرق بين أول وآخر سعر إغلاق
        if last_close > first_close * 1.002:  # اتجاه صاعد إذا كان الارتفاع أكثر من 0.2%
            return 'UPTREND'
        elif last_close < first_close * 0.998:  # اتجاه هابط إذا كان الانخفاض أكثر من 0.2%
            return 'DOWNTREND'
        else:
            return 'NEUTRAL'  # اتجاه محايد
    
    def _check_engulfing_pattern(self, current_candle, prev_candle, trend):
        """
        التحقق من نمط الابتلاع (Engulfing Pattern)
        
        Args:
            current_candle: الشمعة الحالية
            prev_candle: الشمعة السابقة
            trend: الاتجاه العام
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Engulfing Pattern',
            'arabic_name': 'نمط الابتلاع',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        current_body_size = abs(current_candle['close'] - current_candle['open'])
        prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
        
        is_current_bullish = current_candle['close'] > current_candle['open']
        is_prev_bullish = prev_candle['close'] > prev_candle['open']
        
        # شرط نمط الابتلاع الصاعد: الشمعة الحالية صاعدة والسابقة هابطة، وجسم الحالية يبتلع السابقة
        bullish_engulfing = (
            is_current_bullish and 
            not is_prev_bullish and
            current_candle['close'] > prev_candle['open'] and
            current_candle['open'] < prev_candle['close'] and
            current_body_size > prev_body_size * 1.1  # جسم الشمعة الحالية أكبر بنسبة 10% على الأقل
        )
        
        # شرط نمط الابتلاع الهابط: الشمعة الحالية هابطة والسابقة صاعدة، وجسم الحالية يبتلع السابقة
        bearish_engulfing = (
            not is_current_bullish and 
            is_prev_bullish and
            current_candle['close'] < prev_candle['open'] and
            current_candle['open'] > prev_candle['close'] and
            current_body_size > prev_body_size * 1.1  # جسم الشمعة الحالية أكبر بنسبة 10% على الأقل
        )
        
        if bullish_engulfing:
            result['pattern_found'] = True
            result['direction'] = 'BUY'
            # قوة النمط تزداد إذا كان في اتجاه عكس الاتجاه العام (انعكاس محتمل)
            result['strength'] = 80 if trend == 'DOWNTREND' else 60
            result['description'] = "نمط ابتلاع صاعد - إشارة محتملة للشراء"
        
        elif bearish_engulfing:
            result['pattern_found'] = True
            result['direction'] = 'SELL'
            # قوة النمط تزداد إذا كان في اتجاه عكس الاتجاه العام (انعكاس محتمل)
            result['strength'] = 80 if trend == 'UPTREND' else 60
            result['description'] = "نمط ابتلاع هابط - إشارة محتملة للبيع"
        
        return result
    
    def _check_hammer_pattern(self, candle, trend):
        """
        التحقق من نمط المطرقة والمطرقة المقلوبة (Hammer & Inverted Hammer)
        
        Args:
            candle: الشمعة المراد فحصها
            trend: الاتجاه العام
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Hammer Pattern',
            'arabic_name': 'نمط المطرقة',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        body_size = abs(candle['close'] - candle['open'])
        total_size = candle['high'] - candle['low']
        
        if total_size == 0:  # تجنب القسمة على صفر
            return result
            
        body_ratio = body_size / total_size
        
        is_bullish = candle['close'] > candle['open']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        upper_shadow_ratio = upper_shadow / total_size if total_size > 0 else 0
        lower_shadow_ratio = lower_shadow / total_size if total_size > 0 else 0
        
        # شروط المطرقة: جسم صغير، ظل سفلي طويل، ظل علوي قصير
        is_hammer = (
            body_ratio < 0.3 and  # جسم صغير
            lower_shadow_ratio > 0.6 and  # ظل سفلي طويل
            upper_shadow_ratio < 0.1  # ظل علوي قصير جداً
        )
        
        # شروط المطرقة المقلوبة: جسم صغير، ظل علوي طويل، ظل سفلي قصير
        is_inverted_hammer = (
            body_ratio < 0.3 and  # جسم صغير
            upper_shadow_ratio > 0.6 and  # ظل علوي طويل
            lower_shadow_ratio < 0.1  # ظل سفلي قصير جداً
        )
        
        if is_hammer and trend == 'DOWNTREND':
            result['pattern_found'] = True
            result['name'] = 'Hammer'
            result['arabic_name'] = 'نمط المطرقة'
            result['direction'] = 'BUY'
            result['strength'] = 75
            result['description'] = "نمط المطرقة - إشارة انعكاس محتملة للشراء بعد اتجاه هبوطي"
        
        elif is_inverted_hammer and trend == 'DOWNTREND':
            result['pattern_found'] = True
            result['name'] = 'Inverted Hammer'
            result['arabic_name'] = 'نمط المطرقة المقلوبة'
            result['direction'] = 'BUY'
            result['strength'] = 70
            result['description'] = "نمط المطرقة المقلوبة - إشارة انعكاس محتملة للشراء بعد اتجاه هبوطي"
        
        elif is_hammer and trend == 'UPTREND':
            result['pattern_found'] = True
            result['name'] = 'Hanging Man'
            result['arabic_name'] = 'نمط الرجل المشنوق'
            result['direction'] = 'SELL'
            result['strength'] = 75
            result['description'] = "نمط الرجل المشنوق - إشارة انعكاس محتملة للبيع بعد اتجاه صعودي"
        
        elif is_inverted_hammer and trend == 'UPTREND':
            result['pattern_found'] = True
            result['name'] = 'Shooting Star'
            result['arabic_name'] = 'نمط النجم الهابط'
            result['direction'] = 'SELL'
            result['strength'] = 75
            result['description'] = "نمط النجم الهابط - إشارة انعكاس محتملة للبيع بعد اتجاه صعودي"
        
        return result
    
    def _check_star_pattern(self, current_candle, prev_candle, prev2_candle, trend):
        """
        التحقق من نمط نجمة المساء والصباح (Evening Star & Morning Star)
        
        Args:
            current_candle: الشمعة الحالية
            prev_candle: الشمعة السابقة
            prev2_candle: الشمعة قبل السابقة
            trend: الاتجاه العام
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Star Pattern',
            'arabic_name': 'نمط النجمة',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        # حساب أحجام الأجسام
        current_body_size = abs(current_candle['close'] - current_candle['open'])
        prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
        prev2_body_size = abs(prev2_candle['close'] - prev2_candle['open'])
        
        # تحديد اتجاه الشموع
        is_current_bullish = current_candle['close'] > current_candle['open']
        is_prev_bullish = prev_candle['close'] > prev_candle['open']
        is_prev2_bullish = prev2_candle['close'] > prev2_candle['open']
        
        # شروط الشمعة الوسطى (يجب أن تكون صغيرة)
        prev_total_size = prev_candle['high'] - prev_candle['low']
        is_middle_small = prev_body_size < prev_total_size * 0.3
        
        # فحص نمط نجمة الصباح (Morning Star)
        is_morning_star = (
            # الشمعة الأولى هابطة وكبيرة
            not is_prev2_bullish and prev2_body_size > current_body_size * 0.7 and
            # الشمعة الوسطى صغيرة
            is_middle_small and
            # الشمعة الثالثة صاعدة وكبيرة
            is_current_bullish and
            # الفجوة بين الشموع
            max(prev_candle['open'], prev_candle['close']) < prev2_candle['close'] and
            min(prev_candle['open'], prev_candle['close']) > current_candle['open']
        )
        
        # فحص نمط نجمة المساء (Evening Star)
        is_evening_star = (
            # الشمعة الأولى صاعدة وكبيرة
            is_prev2_bullish and prev2_body_size > current_body_size * 0.7 and
            # الشمعة الوسطى صغيرة
            is_middle_small and
            # الشمعة الثالثة هابطة وكبيرة
            not is_current_bullish and
            # الفجوة بين الشموع
            min(prev_candle['open'], prev_candle['close']) > prev2_candle['close'] and
            max(prev_candle['open'], prev_candle['close']) < current_candle['open']
        )
        
        if is_morning_star and trend == 'DOWNTREND':
            result['pattern_found'] = True
            result['name'] = 'Morning Star'
            result['arabic_name'] = 'نجمة الصباح'
            result['direction'] = 'BUY'
            result['strength'] = 90  # هذا نمط قوي جدًا
            result['description'] = "نمط نجمة الصباح - إشارة قوية للانعكاس الصعودي بعد اتجاه هبوطي"
        
        elif is_evening_star and trend == 'UPTREND':
            result['pattern_found'] = True
            result['name'] = 'Evening Star'
            result['arabic_name'] = 'نجمة المساء'
            result['direction'] = 'SELL'
            result['strength'] = 90  # هذا نمط قوي جدًا
            result['description'] = "نمط نجمة المساء - إشارة قوية للانعكاس الهبوطي بعد اتجاه صعودي"
        
        return result
    
    def _check_doji_pattern(self, candle, trend):
        """
        التحقق من نمط الدوجي (Doji)
        
        Args:
            candle: الشمعة المراد فحصها
            trend: الاتجاه العام
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Doji Pattern',
            'arabic_name': 'نمط الدوجي',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        body_size = abs(candle['close'] - candle['open'])
        total_size = candle['high'] - candle['low']
        
        if total_size == 0:  # تجنب القسمة على صفر
            return result
            
        body_ratio = body_size / total_size
        
        # شروط الدوجي: جسم صغير جدًا
        is_doji = body_ratio < 0.1
        
        # دوجي نجمة المسائية (Gravestone Doji) - ظل علوي طويل بدون ظل سفلي
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        is_gravestone_doji = (
            is_doji and
            upper_shadow > 0.7 * total_size and
            lower_shadow < 0.1 * total_size
        )
        
        # دوجي شاهد القبر (Dragonfly Doji) - ظل سفلي طويل بدون ظل علوي
        is_dragonfly_doji = (
            is_doji and
            lower_shadow > 0.7 * total_size and
            upper_shadow < 0.1 * total_size
        )
        
        if is_gravestone_doji and trend == 'UPTREND':
            result['pattern_found'] = True
            result['name'] = 'Gravestone Doji'
            result['arabic_name'] = 'دوجي شاهد القبر'
            result['direction'] = 'SELL'
            result['strength'] = 65
            result['description'] = "نمط دوجي شاهد القبر - إشارة محتملة للانعكاس الهبوطي بعد اتجاه صعودي"
        
        elif is_dragonfly_doji and trend == 'DOWNTREND':
            result['pattern_found'] = True
            result['name'] = 'Dragonfly Doji'
            result['arabic_name'] = 'دوجي اليعسوب'
            result['direction'] = 'BUY'
            result['strength'] = 65
            result['description'] = "نمط دوجي اليعسوب - إشارة محتملة للانعكاس الصعودي بعد اتجاه هبوطي"
        
        elif is_doji:
            result['pattern_found'] = True
            result['name'] = 'Doji'
            result['arabic_name'] = 'دوجي'
            if trend == 'UPTREND':
                result['direction'] = 'SELL'
                result['strength'] = 50
                result['description'] = "نمط دوجي - إشارة محتملة للتردد والانعكاس الهبوطي"
            elif trend == 'DOWNTREND':
                result['direction'] = 'BUY'
                result['strength'] = 50
                result['description'] = "نمط دوجي - إشارة محتملة للتردد والانعكاس الصعودي"
            else:
                result['direction'] = 'NEUTRAL'
                result['strength'] = 40
                result['description'] = "نمط دوجي - إشارة للتردد وعدم وضوح الاتجاه"
        
        return result
    
    def _check_harami_pattern(self, current_candle, prev_candle, trend):
        """
        التحقق من نمط الهاراكامي (Harami)
        
        Args:
            current_candle: الشمعة الحالية
            prev_candle: الشمعة السابقة
            trend: الاتجاه العام
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Harami Pattern',
            'arabic_name': 'نمط الهاراكامي',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        current_body_size = abs(current_candle['close'] - current_candle['open'])
        prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
        
        is_current_bullish = current_candle['close'] > current_candle['open']
        is_prev_bullish = prev_candle['close'] > prev_candle['open']
        
        # شروط نمط الهاراكامي: الشمعة السابقة كبيرة والحالية صغيرة ومحتواة داخل جسم السابقة
        is_harami = (
            current_body_size < prev_body_size * 0.6 and  # الشمعة الحالية أصغر بكثير
            max(current_candle['open'], current_candle['close']) <= max(prev_candle['open'], prev_candle['close']) and
            min(current_candle['open'], current_candle['close']) >= min(prev_candle['open'], prev_candle['close'])
        )
        
        # هاراكامي صاعد: الشمعة السابقة هابطة والحالية صاعدة
        is_bullish_harami = is_harami and not is_prev_bullish and is_current_bullish
        
        # هاراكامي هابط: الشمعة السابقة صاعدة والحالية هابطة
        is_bearish_harami = is_harami and is_prev_bullish and not is_current_bullish
        
        if is_bullish_harami and trend == 'DOWNTREND':
            result['pattern_found'] = True
            result['direction'] = 'BUY'
            result['strength'] = 60
            result['description'] = "نمط هاراكامي صاعد - إشارة محتملة للانعكاس الصعودي"
        
        elif is_bearish_harami and trend == 'UPTREND':
            result['pattern_found'] = True
            result['direction'] = 'SELL'
            result['strength'] = 60
            result['description'] = "نمط هاراكامي هابط - إشارة محتملة للانعكاس الهبوطي"
        
        return result
    
    def _check_three_candles_pattern(self, c1, c2, c3):
        """
        التحقق من نمط ثلاث جنود صاعد أو ثلاث غربان هابطة
        
        Args:
            c1: الشمعة الأولى (الأحدث)
            c2: الشمعة الثانية
            c3: الشمعة الثالثة (الأقدم)
            
        Returns:
            dict: معلومات النمط
        """
        result = {
            'name': 'Three Candles Pattern',
            'arabic_name': 'نمط الشموع الثلاث',
            'pattern_found': False,
            'direction': 'NEUTRAL',
            'strength': 0
        }
        
        # تحديد اتجاه الشموع
        is_c1_bullish = c1['close'] > c1['open']
        is_c2_bullish = c2['close'] > c2['open']
        is_c3_bullish = c3['close'] > c3['open']
        
        # ثلاث جنود صاعد: ثلاث شموع صاعدة متتالية
        is_three_white_soldiers = (
            is_c1_bullish and is_c2_bullish and is_c3_bullish and
            c1['open'] > c2['open'] and c2['open'] > c3['open'] and
            c1['close'] > c2['close'] and c2['close'] > c3['close'] and
            # عدم وجود ظلال سفلية طويلة
            (c1['open'] - c1['low']) < 0.3 * (c1['high'] - c1['low']) and
            (c2['open'] - c2['low']) < 0.3 * (c2['high'] - c2['low']) and
            (c3['open'] - c3['low']) < 0.3 * (c3['high'] - c3['low'])
        )
        
        # ثلاث غربان هابطة: ثلاث شموع هابطة متتالية
        is_three_black_crows = (
            not is_c1_bullish and not is_c2_bullish and not is_c3_bullish and
            c1['open'] < c2['open'] and c2['open'] < c3['open'] and
            c1['close'] < c2['close'] and c2['close'] < c3['close'] and
            # عدم وجود ظلال علوية طويلة
            (c1['high'] - c1['open']) < 0.3 * (c1['high'] - c1['low']) and
            (c2['high'] - c2['open']) < 0.3 * (c2['high'] - c2['low']) and
            (c3['high'] - c3['open']) < 0.3 * (c3['high'] - c3['low'])
        )
        
        if is_three_white_soldiers:
            result['pattern_found'] = True
            result['name'] = 'Three White Soldiers'
            result['arabic_name'] = 'ثلاث جنود صاعد'
            result['direction'] = 'BUY'
            result['strength'] = 85
            result['description'] = "نمط ثلاث جنود صاعد - إشارة قوية لاستمرار الاتجاه الصعودي"
        
        elif is_three_black_crows:
            result['pattern_found'] = True
            result['name'] = 'Three Black Crows'
            result['arabic_name'] = 'ثلاث غربان هابطة'
            result['direction'] = 'SELL'
            result['strength'] = 85
            result['description'] = "نمط ثلاث غربان هابطة - إشارة قوية لاستمرار الاتجاه الهبوطي"
        
        return result
    
    def _generate_pattern_description(self, patterns):
        """
        إنشاء وصف مفصّل للأنماط المكتشفة
        
        Args:
            patterns: قائمة الأنماط المكتشفة
            
        Returns:
            str: وصف مفصّل للأنماط
        """
        if not patterns:
            return "لم يتم العثور على أنماط شموع مهمة"
        
        descriptions = []
        for pattern in patterns:
            descriptions.append(f"{pattern['arabic_name']}: {pattern['description']}")
        
        return " | ".join(descriptions)

# إنشاء مثيل عام من المحلل للاستخدام في جميع أنحاء التطبيق
candlestick_analyzer = CandlestickPatternAnalyzer()

def analyze_candlestick_patterns(candles):
    """
    تحليل أنماط الشموع اليابانية في مجموعة من الشموع
    
    Args:
        candles: مصفوفة من الشموع، كل شمعة تحتوي على OHLC
        
    Returns:
        dict: نتائج تحليل الأنماط
    """
    return candlestick_analyzer.analyze_patterns(candles)

def get_pattern_direction(candles):
    """
    الحصول على اتجاه الإشارة بناءً على أنماط الشموع
    
    Args:
        candles: مصفوفة من الشموع
        
    Returns:
        str: اتجاه الإشارة ('BUY', 'SELL', 'NEUTRAL')
    """
    result = analyze_candlestick_patterns(candles)
    return result['direction']

def get_pattern_strength(candles):
    """
    الحصول على قوة إشارة أنماط الشموع
    
    Args:
        candles: مصفوفة من الشموع
        
    Returns:
        int: قوة الإشارة (0-100)
    """
    result = analyze_candlestick_patterns(candles)
    return result['strength']

def get_pattern_description(candles):
    """
    الحصول على وصف أنماط الشموع المكتشفة
    
    Args:
        candles: مصفوفة من الشموع
        
    Returns:
        str: وصف الأنماط المكتشفة
    """
    result = analyze_candlestick_patterns(candles)
    return result['description']

def validate_signal_with_candlestick_patterns(signal_direction, candles, min_strength=60):
    """
    التحقق من صحة إشارة التداول بناءً على أنماط الشموع
    
    Args:
        signal_direction: اتجاه الإشارة المقترح ('BUY' أو 'SELL')
        candles: مصفوفة من الشموع للتحليل
        min_strength: الحد الأدنى لقوة النمط للتأكيد (0-100)
        
    Returns:
        tuple: (صحة الإشارة, سبب التأكيد أو الرفض)
    """
    pattern_result = analyze_candlestick_patterns(candles)
    pattern_direction = pattern_result['direction']
    pattern_strength = pattern_result['strength']
    
    # إذا كان اتجاه النمط محايدًا، لا نرفض الإشارة
    if pattern_direction == 'NEUTRAL':
        return True, "أنماط الشموع لا تتعارض مع الإشارة"
    
    # التحقق من توافق الاتجاه وقوة النمط
    if pattern_direction == signal_direction and pattern_strength >= min_strength:
        return True, f"الإشارة مؤكدة بواسطة {pattern_result['arabic_name']} بقوة {pattern_strength}%"
    
    # إذا كان الاتجاه متعارضًا، نرفض الإشارة إذا كان النمط قوياً
    if pattern_direction != signal_direction and pattern_strength >= min_strength:
        return False, f"الإشارة تتعارض مع {pattern_result['arabic_name']} (قوة النمط: {pattern_strength}%)"
    
    # إذا كان الاتجاه متعارضًا لكن النمط ضعيف، نقبل الإشارة مع تحذير
    return True, f"الإشارة مقبولة رغم وجود {pattern_result['arabic_name']} بقوة ضعيفة ({pattern_strength}%)"