"""
نظام معايرة مدة الإشارات بشكل ديناميكي
يقوم بتحديد المدة المثالية للإشارة بناءً على خصائص الزوج والوقت وحالة السوق
لتحسين دقة التوقيت وزيادة نسبة الربح
"""

import logging
from datetime import datetime, time, timedelta
import random
import math

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicDurationCalibrator:
    """نظام لمعايرة مدة الإشارات بشكل ديناميكي حسب الزوج والوقت وحالة السوق"""
    
    def __init__(self):
        """تهيئة نظام معايرة المدة الديناميكي"""
        logger.info("تم تهيئة نظام معايرة مدة الإشارات الديناميكي")
        
        # المدد الأساسية المتاحة (بالدقائق)
        # بناءً على طلب المستخدم، تم تحديد المدد المسموحة فقط: 1, 2, 3 دقائق
        self.available_durations = [1, 2, 3]
        
        # المدد المفضلة لكل زوج
        # تم ضبطها بناءً على تحليل سلوك الأزواج المختلفة
        # تم تحديث جميع القيم لتكون ضمن نطاق المدد المسموحة فقط (1، 2، 3 دقائق)
        self.pair_optimal_durations = {
            # أزواج اليورو
            'EURUSD': {'default': 3, 'volatile': 2, 'stable': 3},
            'EURJPY': {'default': 3, 'volatile': 2, 'stable': 3},
            'EURGBP': {'default': 3, 'volatile': 3, 'stable': 3},
            'EURAUD': {'default': 3, 'volatile': 2, 'stable': 3},
            'EURCHF': {'default': 3, 'volatile': 2, 'stable': 3},
            'EURCAD': {'default': 3, 'volatile': 2, 'stable': 3},
            # أزواج الدولار
            'USDJPY': {'default': 2, 'volatile': 1, 'stable': 3},
            'GBPUSD': {'default': 3, 'volatile': 2, 'stable': 3},
            'AUDUSD': {'default': 3, 'volatile': 2, 'stable': 3},
            'NZDUSD': {'default': 3, 'volatile': 2, 'stable': 3},
            'USDCAD': {'default': 3, 'volatile': 2, 'stable': 3},
            'USDCHF': {'default': 3, 'volatile': 2, 'stable': 3},
            # أزواج الكروس
            'GBPJPY': {'default': 2, 'volatile': 1, 'stable': 3},
            'AUDJPY': {'default': 2, 'volatile': 1, 'stable': 3},
            'CHFJPY': {'default': 3, 'volatile': 2, 'stable': 3},
            'GBPAUD': {'default': 3, 'volatile': 2, 'stable': 3},
            'AUDNZD': {'default': 3, 'volatile': 2, 'stable': 3},
            'CADCHF': {'default': 3, 'volatile': 2, 'stable': 3},
        }
        
        # المدد المفضلة لأزواج OTC (نضيف اللاحقة تلقائياً)
        for pair in list(self.pair_optimal_durations.keys()):
            otc_pair = f"{pair}-OTC"
            if otc_pair not in self.pair_optimal_durations:
                self.pair_optimal_durations[otc_pair] = self.pair_optimal_durations[pair].copy()
        
        # المدد المفضلة حسب وقت اليوم
        self.time_optimal_durations = {
            'morning': {'default': 3, 'priority': 2},  # 06:00 - 10:00
            'london_open': {'default': 2, 'priority': 3},  # 10:00 - 12:00
            'london_ny_overlap': {'default': 1, 'priority': 5},  # 12:00 - 16:00
            'ny_session': {'default': 2, 'priority': 4},  # 16:00 - 20:00
            'evening': {'default': 3, 'priority': 2},  # 20:00 - 00:00
            'night': {'default': 3, 'priority': 1},  # 00:00 - 06:00 (تم تغيير القيمة من 5 إلى 3)
        }
        
        # معلمات تقييم حالة السوق
        self.market_conditions = {
            'trending': {'weight': 1.0, 'prefer_longer': False},
            'ranging': {'weight': 1.2, 'prefer_longer': True},
            'volatile': {'weight': 0.8, 'prefer_longer': False},
            'stable': {'weight': 1.5, 'prefer_longer': True},
            'support_resistance': {'weight': 1.2, 'prefer_longer': False},
        }
    
    def calibrate_duration(self, signal, candles=None, multi_timeframe_analysis=None):
        """
        معايرة مدة الإشارة بشكل ديناميكي
        
        Args:
            signal (dict): معلومات الإشارة الأصلية
            candles (list, optional): بيانات الشموع للتحليل الإضافي
            multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
            
        Returns:
            int: المدة المعايرة للإشارة (بالدقائق)
        """
        if not signal:
            logger.warning("لا يمكن معايرة مدة إشارة فارغة")
            return 3  # مدة افتراضية
        
        pair = signal.get('pair', '')
        direction = signal.get('direction', '')
        entry_time_str = signal.get('entry_time', '')
        current_duration = signal.get('duration', 3)
        
        # 1. تحديد المدة الأساسية بناءً على الزوج
        base_duration = self._get_pair_base_duration(pair)
        logger.info(f"المدة الأساسية للزوج {pair}: {base_duration} دقائق")
        
        # 2. تقييم حالة السوق
        market_condition, volatility_score = self._evaluate_market_condition(candles, multi_timeframe_analysis)
        logger.info(f"حالة السوق للزوج {pair}: {market_condition}, درجة التقلب: {volatility_score:.2f}")
        
        # 3. تعديل المدة بناءً على حالة السوق
        market_adjusted_duration = self._adjust_for_market_condition(base_duration, market_condition, volatility_score)
        logger.info(f"المدة المعدلة حسب حالة السوق: {market_adjusted_duration} دقائق")
        
        # 4. تعديل المدة بناءً على الوقت
        time_of_day = self._determine_time_of_day(entry_time_str)
        time_adjusted_duration = self._adjust_for_time_of_day(market_adjusted_duration, time_of_day)
        logger.info(f"المدة المعدلة حسب الوقت ({time_of_day}): {time_adjusted_duration} دقائق")
        
        # 5. تعديل المدة بناءً على القرب من مناطق الدعم والمقاومة
        sr_adjusted_duration = self._adjust_for_support_resistance(time_adjusted_duration, direction, multi_timeframe_analysis)
        logger.info(f"المدة المعدلة حسب مناطق الدعم والمقاومة: {sr_adjusted_duration} دقائق")
        
        # 6. تطبيق القيود والتقريب إلى المدد المتاحة
        final_duration = self._round_to_available_duration(sr_adjusted_duration)
        
        # 7. تسجيل التغيير
        if final_duration != current_duration:
            change_type = "أطول" if final_duration > current_duration else "أقصر"
            logger.info(f"تم تغيير مدة الإشارة من {current_duration} إلى {final_duration} دقائق ({change_type})")
        else:
            logger.info(f"تم الإبقاء على مدة الإشارة: {final_duration} دقائق")
        
        return final_duration
    
    def _get_pair_base_duration(self, pair):
        """
        الحصول على المدة الأساسية للزوج
        
        Args:
            pair (str): رمز الزوج
            
        Returns:
            int: المدة الأساسية للزوج
        """
        # محاولة العثور على الزوج بالضبط
        if pair in self.pair_optimal_durations:
            return self.pair_optimal_durations[pair]['default']
        
        # محاولة العثور على الزوج بدون لاحقة OTC
        base_pair = pair.replace('-OTC', '')
        if base_pair in self.pair_optimal_durations:
            return self.pair_optimal_durations[base_pair]['default']
        
        # محاولة العثور على الزوج الأساسي (أول 6 أحرف)
        if len(pair) >= 6:
            base_pair = pair[:6]
            if base_pair in self.pair_optimal_durations:
                return self.pair_optimal_durations[base_pair]['default']
        
        # إذا لم نجد تطابقاً، استخدم مدة افتراضية
        return 3
    
    def _evaluate_market_condition(self, candles, multi_timeframe_analysis):
        """
        تقييم حالة السوق لتحديد المدة المناسبة
        
        Args:
            candles (list): بيانات الشموع
            multi_timeframe_analysis (dict): نتائج تحليل الإطارات الزمنية المتعددة
            
        Returns:
            tuple: (حالة السوق, درجة التقلب)
        """
        if not candles or len(candles) < 10:
            return 'normal', 0.5  # حالة افتراضية
        
        # حساب درجة التقلب
        volatility_score = self._calculate_volatility(candles)
        
        # تحديد ما إذا كان السوق في اتجاه
        is_trending = self._is_market_trending(candles)
        
        # التحقق من القرب من مناطق الدعم والمقاومة
        is_near_sr = False
        if multi_timeframe_analysis and 'support_resistance' in multi_timeframe_analysis:
            sr_zones = multi_timeframe_analysis['support_resistance']
            current_price = candles[-1]['close']
            is_near_sr = self._is_near_support_resistance(current_price, sr_zones)
        
        # تحديد حالة السوق
        if is_near_sr:
            market_condition = 'support_resistance'
        elif is_trending and volatility_score > 0.7:
            market_condition = 'trending'
        elif not is_trending and volatility_score > 0.7:
            market_condition = 'volatile'
        elif not is_trending and volatility_score < 0.3:
            market_condition = 'stable'
        elif not is_trending and volatility_score >= 0.3:
            market_condition = 'ranging'
        else:
            market_condition = 'normal'
        
        return market_condition, volatility_score
    
    def _calculate_volatility(self, candles):
        """
        حساب درجة تقلب السوق
        
        Args:
            candles (list): بيانات الشموع
            
        Returns:
            float: درجة التقلب (0-1)
        """
        if not candles or len(candles) < 5:
            return 0.5  # قيمة افتراضية
        
        try:
            # حساب نطاق كل شمعة (أعلى - أدنى)
            ranges = [candle['high'] - candle['low'] for candle in candles[-10:]]
            avg_range = sum(ranges) / len(ranges) if ranges else 0
            
            # حساب المتوسط المتحرك للأسعار
            closes = [candle['close'] for candle in candles[-10:]]
            avg_price = sum(closes) / len(closes) if closes else 0
            
            # حساب النسبة المئوية للنطاق مقارنة بالسعر المتوسط
            relative_range = avg_range / avg_price if avg_price > 0 else 0
            
            # تحويل إلى درجة تقلب (0-1)
            # تم ضبط القيم بحيث تعطي نتائج منطقية للعملات
            volatility_score = min(1.0, relative_range * 500)
            
            return volatility_score
        except Exception as e:
            logger.warning(f"خطأ في حساب درجة التقلب: {e}")
            return 0.5
    
    def _is_market_trending(self, candles):
        """
        تحديد ما إذا كان السوق في اتجاه
        
        Args:
            candles (list): بيانات الشموع
            
        Returns:
            bool: هل السوق في اتجاه
        """
        if not candles or len(candles) < 10:
            return False
        
        try:
            # حساب المتوسط المتحرك لـ 5 و 10 فترات
            closes = [candle['close'] for candle in candles]
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else 0
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0
            
            # حساب الاتجاه باستخدام المتوسطات المتحركة
            current_price = closes[-1]
            
            # هناك اتجاه صعودي إذا كان السعر > MA5 > MA10
            uptrend = current_price > ma5 > ma10
            
            # هناك اتجاه هبوطي إذا كان السعر < MA5 < MA10
            downtrend = current_price < ma5 < ma10
            
            # هناك اتجاه إذا كان هناك اتجاه صعودي أو هبوطي
            is_trending = uptrend or downtrend
            
            return is_trending
        except Exception as e:
            logger.warning(f"خطأ في تحديد اتجاه السوق: {e}")
            return False
    
    def _is_near_support_resistance(self, price, sr_zones):
        """
        التحقق مما إذا كان السعر قريباً من منطقة دعم أو مقاومة
        
        Args:
            price (float): السعر الحالي
            sr_zones (dict): مناطق الدعم والمقاومة
            
        Returns:
            bool: هل السعر قريب من منطقة دعم أو مقاومة
        """
        if not sr_zones:
            return False
        
        try:
            resistance_levels = sr_zones.get('resistance', [])
            support_levels = sr_zones.get('support', [])
            
            # حساب أقرب مستوى مقاومة
            nearest_resistance = None
            min_resistance_dist = float('inf')
            for level in resistance_levels:
                dist = level['price'] - price
                if dist > 0 and dist < min_resistance_dist:
                    min_resistance_dist = dist
                    nearest_resistance = level
            
            # حساب أقرب مستوى دعم
            nearest_support = None
            min_support_dist = float('inf')
            for level in support_levels:
                dist = price - level['price']
                if dist > 0 and dist < min_support_dist:
                    min_support_dist = dist
                    nearest_support = level
            
            # تحديد ما إذا كان السعر قريباً من الدعم أو المقاومة
            # نعتبر السعر قريباً إذا كانت المسافة أقل من 0.2% من السعر
            price_threshold = price * 0.002
            
            near_resistance = nearest_resistance and min_resistance_dist < price_threshold
            near_support = nearest_support and min_support_dist < price_threshold
            
            return near_resistance or near_support
        except Exception as e:
            logger.warning(f"خطأ في التحقق من القرب من مناطق الدعم والمقاومة: {e}")
            return False
    
    def _adjust_for_market_condition(self, base_duration, market_condition, volatility_score):
        """
        تعديل المدة بناءً على حالة السوق
        
        Args:
            base_duration (int): المدة الأساسية
            market_condition (str): حالة السوق
            volatility_score (float): درجة التقلب
            
        Returns:
            float: المدة المعدلة (قبل التقريب)
        """
        if market_condition not in self.market_conditions:
            return base_duration
        
        condition_info = self.market_conditions[market_condition]
        weight = condition_info['weight']
        prefer_longer = condition_info['prefer_longer']
        
        if prefer_longer:
            # زيادة المدة للأسواق المستقرة أو المتراوحة
            adjustment_factor = 1.0 + (weight - 1.0) * (1.0 - volatility_score)
        else:
            # تقليل المدة للأسواق المتقلبة أو في اتجاه
            adjustment_factor = 1.0 - (1.0 - weight) * volatility_score
        
        adjusted_duration = base_duration * adjustment_factor
        
        return adjusted_duration
    
    def _determine_time_of_day(self, entry_time_str):
        """
        تحديد فترة اليوم بناءً على وقت الدخول
        
        Args:
            entry_time_str (str): وقت الدخول (HH:MM)
            
        Returns:
            str: فترة اليوم
        """
        if not entry_time_str or ':' not in entry_time_str:
            # إذا لم يكن هناك وقت محدد، استخدم الوقت الحالي
            current_hour = datetime.now().hour
        else:
            hour, _ = map(int, entry_time_str.split(':'))
            current_hour = hour
        
        # تحديد فترة اليوم بناءً على الساعة
        if 6 <= current_hour < 10:
            return 'morning'
        elif 10 <= current_hour < 12:
            return 'london_open'
        elif 12 <= current_hour < 16:
            return 'london_ny_overlap'
        elif 16 <= current_hour < 20:
            return 'ny_session'
        elif 20 <= current_hour < 24:
            return 'evening'
        else:  # 0 <= current_hour < 6
            return 'night'
    
    def _adjust_for_time_of_day(self, duration, time_of_day):
        """
        تعديل المدة بناءً على فترة اليوم
        
        Args:
            duration (float): المدة المعدلة حسب حالة السوق
            time_of_day (str): فترة اليوم
            
        Returns:
            float: المدة المعدلة حسب فترة اليوم
        """
        if time_of_day not in self.time_optimal_durations:
            return duration
        
        time_info = self.time_optimal_durations[time_of_day]
        time_default = time_info['default']
        priority = time_info['priority']
        
        # حساب المتوسط المرجح بين المدة المعدلة حسب السوق والمدة المفضلة للوقت
        weight_market = 10 - priority  # عكس الأولوية لتحديد وزن حالة السوق
        weight_time = priority
        total_weight = weight_market + weight_time
        
        weighted_duration = (duration * weight_market + time_default * weight_time) / total_weight
        
        return weighted_duration
    
    def _adjust_for_support_resistance(self, duration, direction, multi_timeframe_analysis):
        """
        تعديل المدة بناءً على القرب من مناطق الدعم والمقاومة
        
        Args:
            duration (float): المدة المعدلة حسب الوقت
            direction (str): اتجاه الإشارة ('BUY' أو 'SELL')
            multi_timeframe_analysis (dict): نتائج تحليل الإطارات الزمنية المتعددة
            
        Returns:
            float: المدة المعدلة حسب مناطق الدعم والمقاومة
        """
        if not multi_timeframe_analysis or 'support_resistance' not in multi_timeframe_analysis:
            return duration
        
        try:
            sr_zones = multi_timeframe_analysis['support_resistance']
            current_price = None
            
            # الحصول على السعر الحالي
            if 'current_price' in multi_timeframe_analysis:
                current_price = multi_timeframe_analysis['current_price']
            elif 'timeframes' in multi_timeframe_analysis and 'M1' in multi_timeframe_analysis['timeframes']:
                m1_data = multi_timeframe_analysis['timeframes']['M1']
                if 'candles' in m1_data and len(m1_data['candles']) > 0:
                    current_price = m1_data['candles'][-1]['close']
            
            if not current_price:
                return duration
            
            # البحث عن أقرب دعم ومقاومة
            resistance_levels = sr_zones.get('resistance', [])
            support_levels = sr_zones.get('support', [])
            
            nearest_resistance = None
            min_resistance_dist = float('inf')
            for level in resistance_levels:
                dist = level['price'] - current_price
                if dist > 0 and dist < min_resistance_dist:
                    min_resistance_dist = dist
                    nearest_resistance = level
            
            nearest_support = None
            min_support_dist = float('inf')
            for level in support_levels:
                dist = current_price - level['price']
                if dist > 0 and dist < min_support_dist:
                    min_support_dist = dist
                    nearest_support = level
            
            # تعديل المدة بناءً على القرب من الدعم والمقاومة واتجاه الإشارة
            if direction == 'BUY':
                if nearest_resistance:
                    # للإشارات الصاعدة، قرب المقاومة يعني تقليل المدة
                    resistance_factor = 1.0 - min(0.5, min_resistance_dist / current_price * 100)
                    duration *= max(0.5, resistance_factor)
                
                if nearest_support and min_support_dist < current_price * 0.005:
                    # إذا كانت الإشارة عند الدعم مباشرة، زيادة المدة قليلاً
                    duration *= 1.1
            
            elif direction == 'SELL':
                if nearest_support:
                    # للإشارات الهابطة، قرب الدعم يعني تقليل المدة
                    support_factor = 1.0 - min(0.5, min_support_dist / current_price * 100)
                    duration *= max(0.5, support_factor)
                
                if nearest_resistance and min_resistance_dist < current_price * 0.005:
                    # إذا كانت الإشارة عند المقاومة مباشرة، زيادة المدة قليلاً
                    duration *= 1.1
            
            return duration
        except Exception as e:
            logger.warning(f"خطأ في تعديل المدة حسب مناطق الدعم والمقاومة: {e}")
            return duration
    
    def _round_to_available_duration(self, duration):
        """
        تقريب المدة إلى أقرب مدة متاحة
        
        Args:
            duration (float): المدة المعدلة
            
        Returns:
            int: المدة النهائية
        """
        # تقريب إلى المدة المتاحة الأقرب
        closest_duration = min(self.available_durations, key=lambda x: abs(x - duration))
        
        return closest_duration
    
    def get_recommended_duration_for_pair(self, pair, market_condition='normal'):
        """
        الحصول على المدة الموصى بها لزوج معين في حالة سوق محددة
        
        Args:
            pair (str): رمز الزوج
            market_condition (str): حالة السوق
            
        Returns:
            int: المدة الموصى بها
        """
        # محاولة العثور على الزوج بالضبط
        if pair in self.pair_optimal_durations:
            durations = self.pair_optimal_durations[pair]
            if market_condition in durations:
                return durations[market_condition]
            else:
                return durations['default']
        
        # محاولة العثور على الزوج بدون لاحقة OTC
        base_pair = pair.replace('-OTC', '')
        if base_pair in self.pair_optimal_durations:
            durations = self.pair_optimal_durations[base_pair]
            if market_condition in durations:
                return durations[market_condition]
            else:
                return durations['default']
        
        # محاولة العثور على الزوج الأساسي (أول 6 أحرف)
        if len(pair) >= 6:
            base_pair = pair[:6]
            if base_pair in self.pair_optimal_durations:
                durations = self.pair_optimal_durations[base_pair]
                if market_condition in durations:
                    return durations[market_condition]
                else:
                    return durations['default']
        
        # إذا لم نجد تطابقاً، استخدم مدة افتراضية
        return 3
    
    def get_recommended_duration_for_time(self, time_str):
        """
        الحصول على المدة الموصى بها لوقت معين
        
        Args:
            time_str (str): الوقت بتنسيق "HH:MM"
            
        Returns:
            int: المدة الموصى بها
        """
        time_of_day = self._determine_time_of_day(time_str)
        if time_of_day in self.time_optimal_durations:
            return self.time_optimal_durations[time_of_day]['default']
        else:
            return 3

# إنشاء مثيل عام من المعاير للاستخدام في جميع أنحاء التطبيق
duration_calibrator = DynamicDurationCalibrator()

def calibrate_signal_duration(signal, candles=None, multi_timeframe_analysis=None):
    """
    معايرة مدة الإشارة بشكل ديناميكي
    
    Args:
        signal (dict): معلومات الإشارة
        candles (list, optional): بيانات الشموع للتحليل الإضافي
        multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
        
    Returns:
        int: المدة المعايرة للإشارة (بالدقائق)
    """
    return duration_calibrator.calibrate_duration(signal, candles, multi_timeframe_analysis)

def get_optimal_duration(pair, market_condition='normal'):
    """
    الحصول على المدة المثالية لزوج معين في حالة سوق محددة
    
    Args:
        pair (str): رمز الزوج
        market_condition (str): حالة السوق
        
    Returns:
        int: المدة المثالية
    """
    return duration_calibrator.get_recommended_duration_for_pair(pair, market_condition)

def get_optimal_duration_for_time(time_str):
    """
    الحصول على المدة المثالية لوقت معين
    
    Args:
        time_str (str): الوقت بتنسيق "HH:MM"
        
    Returns:
        int: المدة المثالية
    """
    return duration_calibrator.get_recommended_duration_for_time(time_str)