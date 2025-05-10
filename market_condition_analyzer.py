"""
محلل حالة السوق
يقوم بتحليل حالة السوق وتحديد ما إذا كانت مناسبة للتداول أم لا
ويستخدم مجموعة من المؤشرات المتقدمة لتقييم حالة السوق بدقة عالية
"""
import logging
import math
import random
import time
from datetime import datetime, timedelta

from technical_analyzer import TechnicalAnalyzer
# استيراد دوال أزواج OTC وأزواج البورصة العادية
from pocket_option_otc_pairs import get_all_valid_pairs as get_otc_pairs, is_valid_pair as is_valid_otc_pair
from market_pairs import get_all_valid_pairs as get_market_pairs, is_valid_pair as is_valid_market_pair

# إعداد سجل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketConditionAnalyzer:
    """محلل حالة السوق لتحديد مدى ملاءمتها للتداول"""
    
    def __init__(self):
        """تهيئة محلل حالة السوق"""
        self.technical_analyzer = TechnicalAnalyzer()
        
        # عتبات تقييم السوق
        self.volatility_thresholds = {
            'extreme_high': 3.0,  # تذبذب عالٍ جداً
            'high': 2.0,          # تذبذب عالٍ
            'normal': 1.0,         # تذبذب طبيعي
            'low': 0.5            # تذبذب منخفض
        }
        
        # درجات صعوبة التداول في ظروف مختلفة
        self.market_difficulty = {
            'extreme': 95,      # صعب جداً
            'high': 80,         # صعب
            'moderate': 60,     # متوسط الصعوبة
            'normal': 40,       # عادي
            'favorable': 20     # مناسب
        }
        
        # المعايير التي تجعل السوق غير مناسب للتداول تماماً
        self.critical_factors = {
            'extreme_volatility': False,    # تذبذب شديد جداً
            'abnormal_patterns': False,     # أنماط غير طبيعية
            'liquidity_issues': False,      # مشاكل في السيولة
            'price_manipulation': False     # تلاعب بالأسعار
        }
        
        # تاريخ آخر تحليل وتحذير
        self.last_analysis_time = None
        self.last_warning_time = None
        self.analysis_interval_minutes = 15  # تحليل كل 15 دقيقة
        self.warning_interval_minutes = 60   # تحذير كل ساعة على الأكثر
    
    def analyze_market_condition(self, pair_symbol=None):
        """
        تحليل حالة السوق لزوج معين أو عموماً
        
        Args:
            pair_symbol (str, optional): رمز الزوج المراد تحليله، أو None لتحليل عام
            
        Returns:
            dict: معلومات حالة السوق
        """
        # التحقق من وقت آخر تحليل
        current_time = datetime.now()
        
        if self.last_analysis_time:
            time_since_last = (current_time - self.last_analysis_time).total_seconds() / 60
            if time_since_last < self.analysis_interval_minutes:
                logger.info(f"Using cached market analysis (updated {time_since_last:.1f} minutes ago)")
                # إعادة المعلومات المخزنة مسبقاً
                return self._get_cached_analysis()
        
        # تحديث وقت آخر تحليل
        self.last_analysis_time = current_time
        
        logger.info(f"Analyzing market conditions for {pair_symbol or 'general market'}")
        
        # اختيار الأزواج للتحليل (مع دعم كل من أزواج OTC وأزواج البورصة العادية)
        if pair_symbol:
            # التحقق مما إذا كان الزوج المحدد صالحًا (سواء كان زوج OTC أو زوج بورصة عادية)
            if is_valid_otc_pair(pair_symbol) or is_valid_market_pair(pair_symbol):
                pairs_to_analyze = [pair_symbol]
            else:
                logger.warning(f"زوج غير صالح: {pair_symbol}, سيتم اختيار أزواج عشوائية بدلاً منه")
                pairs_to_analyze = []
        else:
            # إذا لم يتم تحديد زوج، نختار عينة عشوائية من كلا النوعين
            pairs_to_analyze = []
        
        # إذا كان قائمة الأزواج للتحليل فارغة، نحصل على أزواج من كلا النوعين
        if not pairs_to_analyze:
            # الحصول على أزواج OTC وأزواج البورصة العادية
            otc_pairs = get_otc_pairs()
            market_pairs = get_market_pairs()
            
            # دمج القائمتين مع تفضيل أزواج البورصة العادية (70%)
            combined_pairs = []
            
            # تحديد عدد الأزواج من كل نوع بناءً على التفضيل
            # نريد 5 أزواج في المجموع، 70% منها من البورصة العادية
            market_count = min(4, len(market_pairs))  # 70% من 5 تقريبًا 4
            otc_count = min(5 - market_count, len(otc_pairs))
            
            # إضافة أزواج البورصة العادية
            if market_pairs:
                combined_pairs.extend(random.sample(market_pairs, market_count))
            
            # إضافة أزواج OTC
            if otc_pairs:
                combined_pairs.extend(random.sample(otc_pairs, otc_count))
            
            logger.info(f"تم اختيار {len(combined_pairs)} أزواج للتحليل ({market_count} من البورصة العادية, {otc_count} من OTC)")
            
            # تخزين الأزواج المختارة
            pairs_to_analyze = combined_pairs
        
        # جمع نتائج التحليل لكل زوج
        pairs_analysis = {}
        overall_volatility = 0
        overall_difficulty = 0
        overall_trend_clarity = 0
        overall_pattern_quality = 0
        valid_pairs_count = 0
        
        # إعادة تعيين العوامل الحرجة
        for factor in self.critical_factors:
            self.critical_factors[factor] = False
        
        for pair in pairs_to_analyze:
            pair_condition = self._analyze_single_pair(pair)
            if pair_condition:
                pairs_analysis[pair] = pair_condition
                
                # تجميع البيانات للتقييم الشامل
                overall_volatility += pair_condition.get('volatility', 0)
                overall_difficulty += pair_condition.get('trading_difficulty', 0)
                overall_trend_clarity += pair_condition.get('trend_clarity', 0)
                overall_pattern_quality += pair_condition.get('pattern_quality', 0)
                valid_pairs_count += 1
                
                # التحقق من العوامل الحرجة
                if pair_condition.get('volatility', 0) > self.volatility_thresholds['extreme_high']:
                    self.critical_factors['extreme_volatility'] = True
                if pair_condition.get('abnormal_pattern', False):
                    self.critical_factors['abnormal_patterns'] = True
                if pair_condition.get('low_liquidity', False):
                    self.critical_factors['liquidity_issues'] = True
                if pair_condition.get('price_manipulation', False):
                    self.critical_factors['price_manipulation'] = True
        
        # حساب المتوسطات
        if valid_pairs_count > 0:
            avg_volatility = overall_volatility / valid_pairs_count
            avg_difficulty = overall_difficulty / valid_pairs_count
            avg_trend_clarity = overall_trend_clarity / valid_pairs_count
            avg_pattern_quality = overall_pattern_quality / valid_pairs_count
        else:
            # قيم افتراضية في حالة عدم وجود أزواج صالحة
            avg_volatility = 1.0
            avg_difficulty = 50
            avg_trend_clarity = 50
            avg_pattern_quality = 50
        
        # تحديد حالة السوق الإجمالية
        market_status = self._determine_market_status(
            avg_volatility, avg_difficulty, avg_trend_clarity, avg_pattern_quality
        )
        
        # تحديد ما إذا كان السوق مناسباً للتداول أم لا
        is_suitable = market_status.get('is_suitable_for_trading', True)
        
        # تحديد ما إذا كان يجب إرسال تحذير أم لا
        should_warn = not is_suitable and self._should_send_warning(current_time)
        
        # تجميع النتائج النهائية
        result = {
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'market_status': market_status,
            'pairs_analysis': pairs_analysis,
            'is_suitable_for_trading': is_suitable,
            'should_send_warning': should_warn,
            'warning_message': self._generate_warning_message(market_status) if should_warn else None
        }
        
        # تخزين النتائج للاستخدام اللاحق
        self._cache_analysis(result)
        
        return result
    
    def _analyze_single_pair(self, pair):
        """
        تحليل حالة زوج واحد
        
        Args:
            pair (str): رمز الزوج
            
        Returns:
            dict: معلومات حالة الزوج
        """
        # الحصول على بيانات السوق
        market_data = self.technical_analyzer.price_data.get(pair, {})
        if not market_data or 'candles' not in market_data or len(market_data['candles']) < 20:
            # لا توجد بيانات كافية للتحليل
            logger.warning(f"Insufficient data for pair {pair}")
            return None
        
        candles = market_data['candles']
        
        # حساب مؤشرات حالة السوق
        volatility = self._calculate_volatility(candles)
        liquidity = self._estimate_liquidity(candles)
        trend = self._analyze_trend(candles)
        pattern_quality = self._analyze_patterns(candles)
        abnormal = self._detect_abnormal_patterns(candles)
        manipulation = self._detect_price_manipulation(candles)
        
        # تحديد صعوبة التداول
        trading_difficulty = self._calculate_trading_difficulty(
            volatility, liquidity, trend['clarity'], pattern_quality, abnormal, manipulation
        )
        
        return {
            'volatility': volatility,
            'liquidity': liquidity,
            'trend': trend['direction'],
            'trend_clarity': trend['clarity'],
            'pattern_quality': pattern_quality,
            'trading_difficulty': trading_difficulty,
            'abnormal_pattern': abnormal,
            'price_manipulation': manipulation,
            'low_liquidity': liquidity < 0.5
        }
    
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
        variance = sum([(p - mean_price) ** 2 for p in closes]) / len(closes)
        std_dev = math.sqrt(variance)
        
        # حساب معامل الاختلاف (CV) كمقياس للتذبذب
        cv = (std_dev / mean_price) * 100
        
        # مؤشر التذبذب المركب
        volatility = (avg_height + cv) / 2
        
        logger.info(f"  - Volatility: {volatility:.2f}%")
        
        return volatility
    
    def _estimate_liquidity(self, candles, lookback=20):
        """
        تقدير السيولة من خلال حجم الشموع ومعدل التغير
        
        Args:
            candles (list): بيانات الشموع
            lookback (int): عدد الشموع للحساب
            
        Returns:
            float: مؤشر السيولة النسبي (0-2 حيث 1 يعني سيولة طبيعية)
        """
        if len(candles) < lookback:
            return 1.0  # قيمة افتراضية متوسطة
        
        # استخدام آخر N شمعة
        recent_candles = candles[-lookback:]
        
        # حساب متوسط فرق السعر بين الشموع المتتالية
        price_changes = []
        for i in range(1, len(recent_candles)):
            change = abs(recent_candles[i]['close'] - recent_candles[i-1]['close'])
            relative_change = change / recent_candles[i-1]['close'] * 100
            price_changes.append(relative_change)
        
        avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # حساب متوسط نطاق الشموع
        ranges = [(c['high'] - c['low']) / c['close'] * 100 for c in recent_candles]
        avg_range = sum(ranges) / len(ranges)
        
        # مؤشر السيولة المركب
        # السيولة العالية: تغيرات سعرية متوسطة ونطاقات معقولة
        # السيولة المنخفضة: تغيرات حادة أو تغيرات قليلة جداً
        
        if avg_price_change < 0.01 or avg_range < 0.02:
            # سيولة منخفضة جداً - سوق غير متحرك
            liquidity = 0.3
        elif avg_price_change > 0.5 and avg_range > 1.0:
            # سيولة منخفضة - تغيرات حادة
            liquidity = 0.5
        elif 0.05 <= avg_price_change <= 0.2 and 0.1 <= avg_range <= 0.5:
            # سيولة عالية - تغيرات متوسطة ونطاقات معقولة
            liquidity = 1.5
        else:
            # سيولة عادية
            liquidity = 1.0
        
        logger.info(f"  - Liquidity: {liquidity:.2f}")
        
        return liquidity
    
    def _analyze_trend(self, candles, lookback=30):
        """
        تحليل اتجاه السوق
        
        Args:
            candles (list): بيانات الشموع
            lookback (int): عدد الشموع للحساب
            
        Returns:
            dict: معلومات الاتجاه
        """
        if len(candles) < lookback:
            return {'direction': 'UNKNOWN', 'clarity': 50}
        
        # استخدام آخر N شمعة
        recent_candles = candles[-lookback:]
        
        # حساب خط الاتجاه باستخدام الانحدار الخطي
        closes = [c['close'] for c in recent_candles]
        x = list(range(len(closes)))
        
        # حساب معاملات الانحدار a و b في المعادلة y = a + bx
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(closes)
        sum_xx = sum(xi*xi for xi in x)
        sum_xy = sum(xi*yi for xi, yi in zip(x, closes))
        
        # تجنب القسمة على صفر
        if n * sum_xx - sum_x * sum_x == 0:
            slope = 0
        else:
            # حساب الميل b
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        
        # تحديد الاتجاه
        if slope > 0.0005:
            direction = "UP"
        elif slope < -0.0005:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"
        
        # حساب قوة الميل للحصول على وضوح الاتجاه
        slope_strength = abs(slope) * 10000
        
        # حساب تناسق الاتجاه (مدى توافق حركة السعر مع خط الاتجاه)
        # حساب المتوسط a
        a = (sum_y - slope * sum_x) / n
        
        # حساب القيم المتوقعة
        predicted = [a + slope * xi for xi in x]
        
        # حساب مجموع مربعات الخطأ
        sse = sum((actual - pred) ** 2 for actual, pred in zip(closes, predicted))
        
        # حساب إجمالي مجموع المربعات
        mean_y = sum_y / n
        sst = sum((yi - mean_y) ** 2 for yi in closes)
        
        # حساب معامل التحديد R^2
        r_squared = 1 - (sse / sst) if sst != 0 else 0
        
        # حساب وضوح الاتجاه (0-100)
        if direction == "SIDEWAYS":
            clarity = 20  # اتجاه غير واضح
        else:
            # الاعتماد على R^2 وقوة الميل
            clarity = min(100, max(0, int(r_squared * 70 + slope_strength * 30)))
        
        logger.info(f"  - Trend: {direction}, Clarity: {clarity}%")
        
        return {'direction': direction, 'clarity': clarity}
    
    def _analyze_patterns(self, candles):
        """
        تحليل جودة الأنماط في السوق
        
        Args:
            candles (list): بيانات الشموع
            
        Returns:
            int: مؤشر جودة الأنماط (0-100)
        """
        if len(candles) < 10:
            return 50  # قيمة متوسطة افتراضية
        
        # حساب التناغم بين المؤشرات الفنية المختلفة
        # هنا نفترض أن جودة الأنماط متوسطة
        quality = 50
        
        # في نموذج حقيقي، يمكن حساب هذا بناءً على توافق المؤشرات الفنية
        # وتكرار أنماط الشموع المعروفة ووضوحها
        
        return quality
    
    def _detect_abnormal_patterns(self, candles):
        """
        اكتشاف أنماط غير طبيعية في السوق
        
        Args:
            candles (list): بيانات الشموع
            
        Returns:
            bool: True إذا تم اكتشاف أنماط غير طبيعية
        """
        if len(candles) < 20:
            return False
        
        # البحث عن تغيرات سعرية كبيرة جداً في فترة قصيرة
        recent_candles = candles[-10:]
        
        # حساب التغير النسبي بين الشموع المتتالية
        changes = []
        for i in range(1, len(recent_candles)):
            change = abs(recent_candles[i]['close'] - recent_candles[i-1]['close'])
            relative_change = change / recent_candles[i-1]['close'] * 100
            changes.append(relative_change)
        
        # البحث عن تغيرات شديدة (أكثر من 2% في شمعة واحدة للأزواج OTC)
        abnormal_changes = [change for change in changes if change > 2.0]
        
        # البحث عن انعكاسات مفاجئة في الاتجاه
        direction_changes = 0
        for i in range(1, len(changes)):
            if (changes[i] > 0.5 and changes[i-1] > 0.5 and
                recent_candles[i+1]['close'] > recent_candles[i]['close'] and
                recent_candles[i]['close'] < recent_candles[i-1]['close']):
                direction_changes += 1
            elif (changes[i] > 0.5 and changes[i-1] > 0.5 and
                  recent_candles[i+1]['close'] < recent_candles[i]['close'] and
                  recent_candles[i]['close'] > recent_candles[i-1]['close']):
                direction_changes += 1
        
        # تحديد وجود أنماط غير طبيعية
        has_abnormal_patterns = len(abnormal_changes) >= 2 or direction_changes >= 3
        
        if has_abnormal_patterns:
            logger.warning(f"  - Detected abnormal market patterns")
        
        return has_abnormal_patterns
    
    def _detect_price_manipulation(self, candles):
        """
        اكتشاف تلاعب محتمل بالأسعار
        
        Args:
            candles (list): بيانات الشموع
            
        Returns:
            bool: True إذا تم اكتشاف تلاعب محتمل
        """
        if len(candles) < 20:
            return False
        
        # بعض المؤشرات للتلاعب المحتمل بالأسعار:
        # 1. وجود ظلال طويلة جداً بشكل غير عادي
        # 2. تغيرات سعرية كبيرة تليها عودة مباشرة للسعر السابق
        # 3. أنماط متكررة بشكل غير طبيعي
        
        # التركيز على مؤشر واحد فقط هنا: الظلال الطويلة جداً
        recent_candles = candles[-15:]
        
        long_shadows_count = 0
        for candle in recent_candles:
            body_size = abs(candle['open'] - candle['close'])
            upper_shadow = candle['high'] - max(candle['open'], candle['close'])
            lower_shadow = min(candle['open'], candle['close']) - candle['low']
            
            # إذا كان الظل أكبر من 5 أضعاف حجم الجسم، فقد يكون هناك تلاعب
            if (body_size > 0 and
                (upper_shadow > 5 * body_size or lower_shadow > 5 * body_size)):
                long_shadows_count += 1
        
        # اعتبار وجود 3 شموع أو أكثر بظلال طويلة غير عادية مؤشراً للتلاعب
        has_manipulation = long_shadows_count >= 3
        
        if has_manipulation:
            logger.warning(f"  - Detected potential price manipulation")
        
        return has_manipulation
    
    def _calculate_trading_difficulty(self, volatility, liquidity, trend_clarity, pattern_quality, 
                                      has_abnormal, has_manipulation):
        """
        حساب صعوبة التداول في ظروف السوق الحالية
        
        Returns:
            int: مستوى صعوبة التداول (0-100)
        """
        # الصعوبة الأساسية بناءً على التذبذب
        if volatility > self.volatility_thresholds['extreme_high']:
            base_difficulty = self.market_difficulty['extreme']  # صعب جداً
        elif volatility > self.volatility_thresholds['high']:
            base_difficulty = self.market_difficulty['high']  # صعب
        elif volatility > self.volatility_thresholds['normal']:
            base_difficulty = self.market_difficulty['moderate']  # متوسط
        elif volatility < self.volatility_thresholds['low']:
            base_difficulty = self.market_difficulty['moderate']  # متوسط (التذبذب المنخفض يمكن أن يكون صعباً أيضاً)
        else:
            base_difficulty = self.market_difficulty['normal']  # عادي
        
        # تعديلات بناءً على العوامل الأخرى
        
        # السيولة
        if liquidity < 0.5:
            # السيولة المنخفضة تزيد الصعوبة
            liquidity_adjustment = +15
        elif liquidity > 1.5:
            # السيولة العالية تقلل الصعوبة
            liquidity_adjustment = -10
        else:
            liquidity_adjustment = 0
        
        # وضوح الاتجاه
        if trend_clarity > 80:
            # اتجاه واضح جداً يقلل الصعوبة
            trend_adjustment = -15
        elif trend_clarity < 30:
            # اتجاه غير واضح يزيد الصعوبة
            trend_adjustment = +10
        else:
            trend_adjustment = 0
        
        # جودة الأنماط
        if pattern_quality > 70:
            # أنماط واضحة تقلل الصعوبة
            pattern_adjustment = -10
        elif pattern_quality < 30:
            # أنماط غير واضحة تزيد الصعوبة
            pattern_adjustment = +5
        else:
            pattern_adjustment = 0
        
        # عوامل حرجة
        critical_adjustment = 0
        if has_abnormal:
            critical_adjustment += 20
        if has_manipulation:
            critical_adjustment += 30
        
        # حساب الصعوبة النهائية
        difficulty = base_difficulty + liquidity_adjustment + trend_adjustment + pattern_adjustment + critical_adjustment
        
        # تقييد القيمة بين 0 و 100
        difficulty = min(100, max(0, difficulty))
        
        logger.info(f"  - Trading difficulty: {difficulty}/100")
        
        return difficulty
    
    def _determine_market_status(self, volatility, difficulty, trend_clarity, pattern_quality):
        """
        تحديد حالة السوق الإجمالية
        
        Returns:
            dict: معلومات حالة السوق
        """
        # تحديد مستوى خطورة السوق بناءً على الصعوبة
        if difficulty >= 90:
            risk_level = "شديد الخطورة"
            risk_description = "سوق متذبذب جداً مع أنماط غير طبيعية"
            is_suitable = False
        elif difficulty >= 75:
            risk_level = "خطر عالي"
            risk_description = "سوق متذبذب مع صعوبة كبيرة في التنبؤ"
            is_suitable = False
        elif difficulty >= 60:
            risk_level = "خطر متوسط"
            risk_description = "سوق متذبذب مع إمكانية التنبؤ المحدودة"
            is_suitable = True
        elif difficulty >= 40:
            risk_level = "خطر معتدل"
            risk_description = "سوق طبيعي مع فرص تداول معقولة"
            is_suitable = True
        else:
            risk_level = "خطر منخفض"
            risk_description = "سوق مستقر مع فرص تداول جيدة"
            is_suitable = True
        
        # تحديد مستوى مناسبة السوق للتداول
        # إذا كان هناك عامل حرج واحد على الأقل، السوق غير مناسب للتداول
        any_critical_factor = any(self.critical_factors.values())
        if any_critical_factor:
            is_suitable = False
        
        # تحديد ما إذا كانت هناك ظروف خاصة
        special_conditions = []
        
        if volatility > self.volatility_thresholds['extreme_high']:
            special_conditions.append("تذبذب شديد جداً")
        if volatility < self.volatility_thresholds['low'] / 2:
            special_conditions.append("سوق هادئ جداً")
        if trend_clarity > 90:
            special_conditions.append("اتجاه قوي وواضح")
        if pattern_quality > 85:
            special_conditions.append("أنماط واضحة جداً")
        
        # المؤشرات والنصائح
        indicators = []
        if volatility > self.volatility_thresholds['high']:
            indicators.append("التذبذب عالٍ جداً (مؤشر: {:.1f}%)".format(volatility))
        
        # النصائح بناءً على حالة السوق
        trading_advice = ""
        if not is_suitable:
            trading_advice = "ينصح بتجنب التداول حالياً وانتظار ظروف سوق أفضل"
        elif difficulty >= 60:
            trading_advice = "ينصح بالتداول بحذر وتقليل حجم الصفقات"
        else:
            trading_advice = "ظروف سوق مواتية للتداول مع مراعاة إدارة المخاطر"
        
        return {
            'risk_level': risk_level,
            'risk_description': risk_description,
            'is_suitable_for_trading': is_suitable,
            'trading_difficulty': difficulty,
            'volatility': volatility,
            'special_conditions': special_conditions,
            'indicators': indicators,
            'trading_advice': trading_advice
        }
    
    def _generate_warning_message(self, market_status):
        """
        إنشاء رسالة التحذير بناءً على حالة السوق
        
        Args:
            market_status (dict): معلومات حالة السوق
            
        Returns:
            str: رسالة التحذير
        """
        # تحديث وقت آخر تحذير
        self.last_warning_time = datetime.now()
        
        # إنشاء رسالة التحذير
        message = "⚠️ *تحذير حالة السوق* ⚠️\n\n"
        
        # إضافة معلومات المخاطر
        message += f"*مستوى الخطر:* {market_status['risk_level']}\n"
        message += f"*وصف الحالة:* {market_status['risk_description']}\n\n"
        
        # إضافة المؤشرات
        if market_status['indicators']:
            message += "*المؤشرات:*\n"
            for indicator in market_status['indicators']:
                message += f"• {indicator}\n"
            message += "\n"
        
        # إضافة الظروف الخاصة
        if market_status['special_conditions']:
            message += "*ظروف خاصة:*\n"
            for condition in market_status['special_conditions']:
                message += f"• {condition}\n"
            message += "\n"
        
        # إضافة النصيحة
        message += f"*النصيحة:* {market_status['trading_advice']}\n\n"
        
        # التوقيت
        message += f"_تم تحديث هذا التحذير في {datetime.now().strftime('%H:%M')} بتوقيت GMT+3_"
        
        return message
    
    def _should_send_warning(self, current_time):
        """
        تحديد ما إذا كان يجب إرسال تحذير أم لا
        
        Args:
            current_time (datetime): الوقت الحالي
            
        Returns:
            bool: True إذا كان يجب إرسال تحذير
        """
        if not self.last_warning_time:
            return True
        
        time_since_last = (current_time - self.last_warning_time).total_seconds() / 60
        return time_since_last >= self.warning_interval_minutes
    
    def _cache_analysis(self, analysis):
        """
        تخزين نتائج التحليل للاستخدام اللاحق
        
        Args:
            analysis (dict): نتائج التحليل
        """
        self._cached_analysis = analysis
    
    def _get_cached_analysis(self):
        """
        الحصول على نتائج التحليل المخزنة
        
        Returns:
            dict: نتائج التحليل المخزنة
        """
        if hasattr(self, '_cached_analysis'):
            return self._cached_analysis
        return None

# محلل حالة السوق العالمي للاستخدام في جميع أنحاء التطبيق
market_analyzer = MarketConditionAnalyzer()

def analyze_market_condition(pair_symbol=None):
    """
    تحليل حالة السوق الحالية
    
    Args:
        pair_symbol (str, optional): رمز الزوج للتحليل، أو None لتحليل عام
        
    Returns:
        dict: معلومات حالة السوق
    """
    return market_analyzer.analyze_market_condition(pair_symbol)

def should_stop_trading():
    """
    تحديد ما إذا كان يجب إيقاف إرسال الإشارات نظراً لظروف السوق
    
    Returns:
        bool: True إذا كان يجب إيقاف التداول
    """
    market_condition = analyze_market_condition()
    if market_condition is None:
        return False
    
    return not market_condition.get('is_suitable_for_trading', True)

def get_market_warning_message():
    """
    الحصول على رسالة تحذير عن حالة السوق، إذا كان هناك داعٍ لذلك
    
    Returns:
        str: رسالة التحذير، أو None إذا لم تكن هناك حاجة للتحذير
    """
    market_condition = analyze_market_condition()
    if market_condition and market_condition.get('should_send_warning', False):
        return market_condition.get('warning_message')
    return None