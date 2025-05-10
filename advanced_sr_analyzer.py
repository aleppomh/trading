"""
نظام تحليل متقدم لنقاط الدعم والمقاومة ونقاط التذبذب والتجميع للأزواج
يستخدم هذا النظام للكشف عن نقاط الدعم والمقاومة القوية ومناطق التذبذب والتجميع
لزيادة دقة الإشارات وتحديد افضل نقاط الدخول والخروج
"""

import logging
import numpy as np
from datetime import datetime, timedelta
import traceback

# تهيئة نظام السجلات
logger = logging.getLogger(__name__)

class AdvancedSRAnalyzer:
    """محلل متقدم لنقاط الدعم والمقاومة ومناطق التذبذب والتجميع"""
    
    def __init__(self, price_sensitivity=0.0005, time_window=200, clustering_threshold=0.002, is_otc_pair=False):
        """
        تهيئة نظام تحليل نقاط الدعم والمقاومة ومناطق التذبذب والتجميع
        
        Args:
            price_sensitivity: حساسية تحديد نقاط الدعم والمقاومة (بالنسبة للسعر)
            time_window: نافذة الوقت لتحليل البيانات التاريخية (عدد الشموع)
            clustering_threshold: عتبة تجميع نقاط السعر المتقاربة في مستوى واحد
            is_otc_pair: ما إذا كان الزوج المحلل من أزواج OTC الخاصة بمنصة Pocket Option
        """
        self.price_sensitivity = price_sensitivity
        self.time_window = time_window
        self.clustering_threshold = clustering_threshold
        self.is_otc_pair = is_otc_pair
        
        # ضبط المعاملات لتحليل التجميع والتذبذب
        # قيم مضبوطة خصيصاً لأزواج OTC
        if is_otc_pair:
            # أزواج OTC تتطلب حساسية أعلى لاكتشاف نقاط الدعم والمقاومة
            self.price_sensitivity = 0.0003  # حساسية أعلى للكشف عن نقاط أكثر
            self.clustering_threshold = 0.0015  # تجميع أقوى للنقاط المتقاربة
            self.volume_threshold = 1.3  # عتبة أقل لحجم التداول لتحديد مناطق التجميع
            self.accumulation_min_duration = 4  # عدد شموع أقل للكشف عن مناطق التجميع
            self.volatility_threshold = 1.8  # عتبة أقل للتذبذب لأزواج OTC
            self.volatility_window = 8  # نافذة حساب أصغر للتذبذب
            logger.info("⚠️ تم ضبط النظام خصيصاً لتحليل زوج OTC من منصة Pocket Option")
        else:
            self.volume_threshold = 1.5  # عتبة حجم التداول لتحديد مناطق التجميع (مقارنة بالمتوسط)
            self.accumulation_min_duration = 5  # الحد الأدنى لعدد الشموع لاعتبار المنطقة منطقة تجميع
            self.volatility_threshold = 2.0  # عتبة التذبذب (مقارنة بالمتوسط)
            self.volatility_window = 10  # نافذة حساب التذبذب
        
        logger.info("✅ تم تهيئة نظام تحليل نقاط الدعم والمقاومة ومناطق التذبذب والتجميع")
    
    def analyze(self, candles):
        """
        تحليل الشموع لاستخراج نقاط الدعم والمقاومة ومناطق التذبذب والتجميع
        
        Args:
            candles: قائمة بيانات الشموع للتحليل
            
        Returns:
            dict: نتائج التحليل المتكامل
        """
        if not candles or len(candles) < 20:
            logger.warning("⚠️ عدد الشموع غير كافٍ للتحليل المتقدم")
            return {
                "support_levels": [],
                "resistance_levels": [],
                "accumulation_zones": [],
                "volatility_zones": [],
                "breakout_points": []
            }
        
        try:
            # تحديد الشموع المستخدمة في التحليل (آخر time_window شمعة أو أقل إذا لم تتوفر)
            analysis_candles = candles[-min(self.time_window, len(candles)):]
            
            # استخراج الأسعار
            highs = np.array([candle['high'] for candle in analysis_candles])
            lows = np.array([candle['low'] for candle in analysis_candles])
            closes = np.array([candle['close'] for candle in analysis_candles])
            opens = np.array([candle['open'] for candle in analysis_candles])
            volumes = np.array([candle.get('volume', 1.0) for candle in analysis_candles])
            
            # 1. تحليل نقاط الدعم والمقاومة
            support_levels = self._find_support_levels(analysis_candles, lows, closes)
            resistance_levels = self._find_resistance_levels(analysis_candles, highs, closes)
            
            # 2. تحليل مناطق التجميع
            accumulation_zones = self._find_accumulation_zones(analysis_candles, closes, volumes)
            
            # 3. تحليل مناطق التذبذب
            volatility_zones = self._find_volatility_zones(analysis_candles, closes, highs, lows)
            
            # 4. تحديد نقاط الاختراق المحتملة
            breakout_points = self._find_breakout_points(analysis_candles, closes, support_levels, resistance_levels)
            
            # 5. تقييم قوة مستويات الدعم والمقاومة
            support_levels = self._evaluate_level_strength(support_levels, analysis_candles, "support")
            resistance_levels = self._evaluate_level_strength(resistance_levels, analysis_candles, "resistance")
            
            # تجميع النتائج
            return {
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "accumulation_zones": accumulation_zones,
                "volatility_zones": volatility_zones,
                "breakout_points": breakout_points,
                "current_price": closes[-1] if len(closes) > 0 else None
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل نقاط الدعم والمقاومة: {e}")
            logger.error(traceback.format_exc())
            return {
                "support_levels": [],
                "resistance_levels": [],
                "accumulation_zones": [],
                "volatility_zones": [],
                "breakout_points": [],
                "error": str(e)
            }
    
    def _find_support_levels(self, candles, lows, closes):
        """
        البحث عن نقاط الدعم في بيانات السعر
        
        Args:
            candles: بيانات الشموع الكاملة
            lows: مصفوفة الأسعار الدنيا
            closes: مصفوفة أسعار الإغلاق
            
        Returns:
            list: قائمة بنقاط الدعم المكتشفة مع معلوماتها
        """
        support_points = []
        current_price = closes[-1]
        
        # البحث عن القيعان المحلية (نقاط الدعم المحتملة)
        for i in range(2, len(lows) - 2):
            # نقطة تعتبر قاعًا محليًا إذا كانت أقل من النقطتين قبلها والنقطتين بعدها
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_points.append({
                    "price": lows[i],
                    "index": i,
                    "candle": candles[i],
                    "touches": 0,
                    "strength": 0
                })
        
        # تجميع نقاط الدعم القريبة من بعضها
        clustered_supports = self._cluster_price_levels(support_points)
        
        # تصفية نقاط الدعم والاحتفاظ بالنقاط القوية فقط
        valid_supports = [s for s in clustered_supports if s["price"] < current_price * (1 + self.price_sensitivity)]
        
        # فرز نقاط الدعم من الأعلى إلى الأدنى للتداول (من الأقرب إلى السعر الحالي إلى الأبعد)
        valid_supports.sort(key=lambda x: abs(current_price - x["price"]))
        
        return valid_supports[:5]  # الاحتفاظ بأفضل 5 نقاط دعم فقط
    
    def _find_resistance_levels(self, candles, highs, closes):
        """
        البحث عن نقاط المقاومة في بيانات السعر
        
        Args:
            candles: بيانات الشموع الكاملة
            highs: مصفوفة الأسعار العليا
            closes: مصفوفة أسعار الإغلاق
            
        Returns:
            list: قائمة بنقاط المقاومة المكتشفة مع معلوماتها
        """
        resistance_points = []
        current_price = closes[-1]
        
        # البحث عن القمم المحلية (نقاط المقاومة المحتملة)
        for i in range(2, len(highs) - 2):
            # نقطة تعتبر قمة محلية إذا كانت أعلى من النقطتين قبلها والنقطتين بعدها
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_points.append({
                    "price": highs[i],
                    "index": i,
                    "candle": candles[i],
                    "touches": 0,
                    "strength": 0
                })
        
        # تجميع نقاط المقاومة القريبة من بعضها
        clustered_resistances = self._cluster_price_levels(resistance_points)
        
        # تصفية نقاط المقاومة والاحتفاظ بالنقاط القوية فقط
        valid_resistances = [r for r in clustered_resistances if r["price"] > current_price * (1 - self.price_sensitivity)]
        
        # فرز نقاط المقاومة من الأدنى إلى الأعلى للتداول (من الأقرب إلى السعر الحالي إلى الأبعد)
        valid_resistances.sort(key=lambda x: abs(current_price - x["price"]))
        
        return valid_resistances[:5]  # الاحتفاظ بأفضل 5 نقاط مقاومة فقط
    
    def _cluster_price_levels(self, price_points):
        """
        تجميع مستويات الأسعار المتقاربة في مستويات موحدة
        
        Args:
            price_points: قائمة بنقاط الأسعار المكتشفة
            
        Returns:
            list: قائمة بمستويات الأسعار المجمعة
        """
        if not price_points:
            return []
        
        # فرز النقاط حسب السعر
        sorted_points = sorted(price_points, key=lambda x: x["price"])
        
        # تجميع النقاط المتقاربة
        clusters = []
        current_cluster = [sorted_points[0]]
        
        # استخدام عتبة تجميع مخصصة لأزواج OTC إذا كان الزوج من منصة Pocket Option
        clustering_threshold = self.clustering_threshold
        if self.is_otc_pair:
            # أزواج OTC تحتاج عتبة أقل للتجميع
            clustering_threshold = self.clustering_threshold * 0.8
            logger.debug(f"🔍 استخدام عتبة تجميع مخصصة لزوج OTC: {clustering_threshold}")
        
        for i in range(1, len(sorted_points)):
            current_point = sorted_points[i]
            prev_point = sorted_points[i-1]
            
            # إذا كان الفرق بين النقطتين أقل من العتبة، أضف النقطة إلى التجمع الحالي
            if (current_point["price"] - prev_point["price"]) / prev_point["price"] < clustering_threshold:
                current_cluster.append(current_point)
            else:
                # إنشاء مستوى للتجمع الحالي
                if current_cluster:
                    price_sum = sum(p["price"] for p in current_cluster)
                    avg_price = price_sum / len(current_cluster)
                    
                    # اختيار أقوى نقطة في التجمع
                    strongest_point = max(current_cluster, key=lambda x: x["index"])
                    strongest_point["price"] = avg_price
                    strongest_point["touches"] = len(current_cluster)
                    
                    # تعزيز وزن النقاط في أزواج OTC
                    if self.is_otc_pair:
                        strongest_point["strength"] = min(100, int(strongest_point.get("strength", 0) * 1.15))
                        strongest_point["is_otc"] = True
                        
                    clusters.append(strongest_point)
                
                # بدء تجمع جديد
                current_cluster = [current_point]
        
        # إضافة التجمع الأخير
        if current_cluster:
            price_sum = sum(p["price"] for p in current_cluster)
            avg_price = price_sum / len(current_cluster)
            
            strongest_point = max(current_cluster, key=lambda x: x["index"])
            strongest_point["price"] = avg_price
            strongest_point["touches"] = len(current_cluster)
            
            # تعزيز وزن النقاط في أزواج OTC
            if self.is_otc_pair:
                strongest_point["strength"] = min(100, int(strongest_point.get("strength", 0) * 1.15))
                strongest_point["is_otc"] = True
                
            clusters.append(strongest_point)
        
        return clusters
    
    def _find_accumulation_zones(self, candles, closes, volumes):
        """
        البحث عن مناطق التجميع في بيانات السعر
        
        Args:
            candles: بيانات الشموع الكاملة
            closes: مصفوفة أسعار الإغلاق
            volumes: مصفوفة أحجام التداول
            
        Returns:
            list: قائمة بمناطق التجميع المكتشفة مع معلوماتها
        """
        accumulation_zones = []
        
        # حساب المتوسط المتحرك لحجم التداول
        avg_volume = np.mean(volumes)
        
        # البحث عن التراكم: حجم تداول مرتفع مع تحرك سعري محدود
        for i in range(self.accumulation_min_duration, len(candles)):
            # فحص نافذة من الشموع
            window_closes = closes[i-self.accumulation_min_duration:i]
            window_volumes = volumes[i-self.accumulation_min_duration:i]
            
            # حساب التحرك السعري ضمن النافذة
            price_range = max(window_closes) - min(window_closes)
            price_range_percent = price_range / min(window_closes)
            
            # حساب متوسط حجم التداول ضمن النافذة
            window_avg_volume = np.mean(window_volumes)
            
            # شروط تحديد منطقة التجميع:
            # 1. حجم تداول أعلى من المتوسط العام
            # 2. تحرك سعري محدود (إشارة إلى التجميع/التوزيع)
            if (window_avg_volume > avg_volume * self.volume_threshold and
                price_range_percent < 0.015):  # تغير سعري أقل من 1.5%
                
                # تحديد نوع منطقة التجميع (تجميع قبل صعود أو توزيع قبل هبوط)
                accumulation_type = "accumulation" if closes[i] > closes[i-self.accumulation_min_duration] else "distribution"
                
                accumulation_zones.append({
                    "start_index": i-self.accumulation_min_duration,
                    "end_index": i,
                    "price_level": np.mean(window_closes),
                    "volume_ratio": window_avg_volume / avg_volume,
                    "type": accumulation_type,
                    "strength": min(100, int(window_avg_volume / avg_volume * 50))
                })
        
        # فرز مناطق التجميع حسب قوتها
        accumulation_zones.sort(key=lambda x: x["strength"], reverse=True)
        
        return accumulation_zones[:3]  # الاحتفاظ بأقوى 3 مناطق تجميع
    
    def _find_volatility_zones(self, candles, closes, highs, lows):
        """
        البحث عن مناطق التذبذب في بيانات السعر
        
        Args:
            candles: بيانات الشموع الكاملة
            closes: مصفوفة أسعار الإغلاق
            highs: مصفوفة الأسعار العليا
            lows: مصفوفة الأسعار الدنيا
            
        Returns:
            list: قائمة بمناطق التذبذب المكتشفة مع معلوماتها
        """
        volatility_zones = []
        
        # حساب متوسط المدى اليومي (الفرق بين الأعلى والأدنى)
        true_ranges = []
        for i in range(1, len(candles)):
            prev_close = closes[i-1]
            high = highs[i]
            low = lows[i]
            
            # حساب المدى الحقيقي
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # متوسط المدى الحقيقي
        atr = np.mean(true_ranges) if true_ranges else 0
        
        # البحث عن مناطق التذبذب العالي
        for i in range(self.volatility_window, len(candles)):
            # فحص نافذة من الشموع
            window_true_ranges = true_ranges[i-self.volatility_window:i]
            window_atr = np.mean(window_true_ranges)
            
            # شرط تحديد منطقة التذبذب: متوسط مدى حقيقي أعلى من متوسط المدى العام
            if window_atr > atr * self.volatility_threshold:
                volatility_zones.append({
                    "start_index": i-self.volatility_window,
                    "end_index": i,
                    "price_level": closes[i],
                    "atr_ratio": window_atr / atr,
                    "strength": min(100, int(window_atr / atr * 50))
                })
        
        # فرز مناطق التذبذب حسب قوتها
        volatility_zones.sort(key=lambda x: x["strength"], reverse=True)
        
        return volatility_zones[:3]  # الاحتفاظ بأقوى 3 مناطق تذبذب
    
    def _find_breakout_points(self, candles, closes, support_levels, resistance_levels):
        """
        تحديد نقاط الاختراق المحتملة
        
        Args:
            candles: بيانات الشموع الكاملة
            closes: مصفوفة أسعار الإغلاق
            support_levels: مستويات الدعم المكتشفة
            resistance_levels: مستويات المقاومة المكتشفة
            
        Returns:
            list: قائمة بنقاط الاختراق المحتملة مع معلوماتها
        """
        breakout_points = []
        current_price = closes[-1]
        
        # فحص اختراقات الدعم
        for support in support_levels:
            # حساب نسبة الاقتراب من مستوى الدعم
            distance_ratio = (current_price - support["price"]) / support["price"]
            
            # إذا كان السعر قريب جداً من مستوى الدعم (أو أقل منه قليلاً)
            if -0.005 < distance_ratio < 0.005:
                breakout_direction = "UP" if distance_ratio < 0 else "DOWN"
                
                breakout_points.append({
                    "price": support["price"],
                    "type": "support",
                    "direction": breakout_direction,
                    "distance_percent": abs(distance_ratio) * 100,
                    "strength": support.get("strength", 50)
                })
        
        # فحص اختراقات المقاومة
        for resistance in resistance_levels:
            # حساب نسبة الاقتراب من مستوى المقاومة
            distance_ratio = (resistance["price"] - current_price) / current_price
            
            # إذا كان السعر قريب جداً من مستوى المقاومة (أو أعلى منه قليلاً)
            if -0.005 < distance_ratio < 0.005:
                breakout_direction = "UP" if distance_ratio < 0 else "DOWN"
                
                breakout_points.append({
                    "price": resistance["price"],
                    "type": "resistance",
                    "direction": breakout_direction,
                    "distance_percent": abs(distance_ratio) * 100,
                    "strength": resistance.get("strength", 50)
                })
        
        # فرز نقاط الاختراق حسب القرب من السعر الحالي
        breakout_points.sort(key=lambda x: x["distance_percent"])
        
        return breakout_points[:3]  # الاحتفاظ بأقرب 3 نقاط اختراق محتملة
    
    def _evaluate_level_strength(self, levels, candles, level_type):
        """
        تقييم قوة مستويات الدعم أو المقاومة
        
        Args:
            levels: قائمة بمستويات الدعم أو المقاومة
            candles: بيانات الشموع الكاملة
            level_type: نوع المستوى ("support" أو "resistance")
            
        Returns:
            list: قائمة بمستويات الدعم أو المقاومة مع تقييم قوتها
        """
        for level in levels:
            price = level["price"]
            touches = 0
            bounces = 0
            
            # حساب عدد المرات التي تم فيها لمس المستوى والارتداد عنه
            for candle in candles:
                # نطاق السعر للمستوى (مع هامش)
                price_range = price * self.clustering_threshold
                
                # شروط لمس المستوى تختلف حسب نوع المستوى
                if level_type == "support":
                    if candle["low"] <= price + price_range and candle["low"] >= price - price_range:
                        touches += 1
                        # الارتداد: إذا ارتفع السعر بعد لمس مستوى الدعم
                        if candle["close"] > candle["open"] and candle["close"] > price:
                            bounces += 1
                else:  # resistance
                    if candle["high"] >= price - price_range and candle["high"] <= price + price_range:
                        touches += 1
                        # الارتداد: إذا انخفض السعر بعد لمس مستوى المقاومة
                        if candle["close"] < candle["open"] and candle["close"] < price:
                            bounces += 1
            
            # حساب معامل قوة المستوى (0-100)
            if touches > 0:
                # القوة تعتمد على عدد مرات اللمس وفعالية الارتداد
                bounce_effectiveness = bounces / touches if touches > 0 else 0
                recency_factor = 1 + (level["index"] / len(candles)) * 0.5  # المستويات الحديثة لها وزن أكبر
                
                # صيغة حساب القوة: تجمع بين عدد مرات اللمس، وفعالية الارتداد، وحداثة المستوى
                strength = min(100, int((touches * 10 + bounce_effectiveness * 50) * recency_factor))
                
                level["touches"] = touches
                level["bounces"] = bounces
                level["strength"] = strength
            else:
                # المستوى لم يتم لمسه (قد يكون ضعيفًا أو جديدًا جدًا)
                level["touches"] = 0
                level["bounces"] = 0
                level["strength"] = max(20, int(30 * (level["index"] / len(candles))))  # المستويات الحديثة لها أولوية أعلى
        
        # ترتيب المستويات حسب قوتها
        levels.sort(key=lambda x: x["strength"], reverse=True)
        
        return levels

# إنشاء مثيل للاستخدام العالمي لكل من الأزواج العادية وأزواج OTC
sr_analyzer = AdvancedSRAnalyzer()
sr_analyzer_otc = AdvancedSRAnalyzer(
    price_sensitivity=0.0006,  # حساسية أعلى للأسعار في أزواج OTC
    clustering_threshold=0.0025,  # عتبة تجميع أعلى للأزواج الخاصة
    is_otc_pair=True  # تحديد أن هذا المحلل مخصص لأزواج OTC
)

def analyze_sr_levels(candles, is_otc_pair=False):
    """
    تحليل مستويات الدعم والمقاومة ومناطق التذبذب والتجميع
    
    Args:
        candles: بيانات الشموع للتحليل
        is_otc_pair: ما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
    
    Returns:
        dict: نتائج التحليل المتكامل
    """
    # استخدام المحلل المناسب حسب نوع الزوج
    if is_otc_pair:
        logger.info("🔍 استخدام محلل متخصص لزوج OTC من منصة Pocket Option")
        return sr_analyzer_otc.analyze(candles)
    else:
        return sr_analyzer.analyze(candles)

def get_key_price_levels(candles, is_otc_pair=False):
    """
    الحصول على مستويات الأسعار الرئيسية للتداول
    
    Args:
        candles: بيانات الشموع للتحليل
        is_otc_pair: ما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
    
    Returns:
        dict: مستويات الأسعار الرئيسية مع توصيات التداول
    """
    # استخدام المحلل المناسب حسب نوع الزوج
    if is_otc_pair:
        analysis = sr_analyzer_otc.analyze(candles)
    else:
        analysis = sr_analyzer.analyze(candles)
    current_price = analysis.get("current_price")
    
    if not current_price:
        return {"error": "لا يمكن تحديد السعر الحالي"}
    
    # ترتيب مستويات الدعم من الأعلى إلى الأدنى
    support_levels = sorted(analysis.get("support_levels", []), 
                           key=lambda x: x["price"], reverse=True)
    
    # ترتيب مستويات المقاومة من الأدنى إلى الأعلى
    resistance_levels = sorted(analysis.get("resistance_levels", []), 
                              key=lambda x: x["price"])
    
    # تحديد أقرب مستويات الدعم والمقاومة للسعر الحالي
    closest_support = None
    for support in support_levels:
        if support["price"] < current_price:
            closest_support = support
            break
    
    closest_resistance = None
    for resistance in resistance_levels:
        if resistance["price"] > current_price:
            closest_resistance = resistance
            break
    
    # تحليل مناطق التجميع
    accumulation_zones = analysis.get("accumulation_zones", [])
    recent_accumulation = accumulation_zones[0] if accumulation_zones else None
    
    # توصيات التداول بناءً على التحليل
    trading_recommendations = []
    
    if closest_support and closest_resistance:
        # حساب نسبة المخاطرة/العائد
        risk = current_price - closest_support["price"]
        reward = closest_resistance["price"] - current_price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # تقييم موقع السعر الحالي بين الدعم والمقاومة
        price_position = (current_price - closest_support["price"]) / (closest_resistance["price"] - closest_support["price"])
        
        if price_position < 0.3 and closest_support["strength"] > 60:
            # قريب من الدعم القوي: فرصة شراء محتملة
            trading_recommendations.append({
                "action": "BUY",
                "confidence": min(90, closest_support["strength"]),
                "target": closest_resistance["price"],
                "stop_loss": closest_support["price"] * 0.995,
                "risk_reward": risk_reward_ratio
            })
        elif price_position > 0.7 and closest_resistance["strength"] > 60:
            # قريب من المقاومة القوية: فرصة بيع محتملة
            trading_recommendations.append({
                "action": "SELL",
                "confidence": min(90, closest_resistance["strength"]),
                "target": closest_support["price"],
                "stop_loss": closest_resistance["price"] * 1.005,
                "risk_reward": 1/risk_reward_ratio if risk_reward_ratio > 0 else 0
            })
    
    # تحليل مناطق الاختراق
    breakout_points = analysis.get("breakout_points", [])
    if breakout_points:
        potential_breakout = breakout_points[0]
        
        if potential_breakout["distance_percent"] < 0.2 and potential_breakout["strength"] > 50:
            direction = "BUY" if potential_breakout["direction"] == "UP" else "SELL"
            
            trading_recommendations.append({
                "action": f"{direction} (اختراق)",
                "confidence": min(80, potential_breakout["strength"]),
                "notes": f"اختراق محتمل لمستوى {potential_breakout['price']:.5f}"
            })
    
    return {
        "current_price": current_price,
        "closest_support": closest_support,
        "closest_resistance": closest_resistance,
        "accumulation_zone": recent_accumulation,
        "recommendations": trading_recommendations,
        "price_levels": {
            "strong_support": [s for s in support_levels if s["strength"] > 70],
            "strong_resistance": [r for r in resistance_levels if r["strength"] > 70],
        },
        "market_context": _get_market_context(candles, analysis)
    }

def _get_market_context(candles, analysis):
    """
    تحليل سياق السوق لتوفير نظرة شاملة
    
    Args:
        candles: بيانات الشموع للتحليل
        analysis: نتائج التحليل السابقة
        
    Returns:
        dict: سياق السوق ونظرة عامة
    """
    if not candles or len(candles) < 10:
        return {"trend": "غير محدد", "volatility": "غير محدد"}
    
    # تحليل الاتجاه
    closes = [candle["close"] for candle in candles[-20:]]
    opens = [candle["open"] for candle in candles[-20:]]
    
    # حساب عدد الشموع الصاعدة والهابطة
    bullish_count = sum(1 for i in range(len(closes)) if closes[i] > opens[i])
    bearish_count = sum(1 for i in range(len(closes)) if closes[i] < opens[i])
    
    # تحديد الاتجاه بناءً على نسبة الشموع الصاعدة/الهابطة
    if bullish_count > bearish_count * 1.5:
        trend = "صاعد قوي"
    elif bullish_count > bearish_count:
        trend = "صاعد"
    elif bearish_count > bullish_count * 1.5:
        trend = "هابط قوي"
    elif bearish_count > bullish_count:
        trend = "هابط"
    else:
        trend = "متعادل"
    
    # تقييم قوة الاتجاه
    trend_strength = abs(bullish_count - bearish_count) / len(closes) * 100
    
    # تقييم التذبذب
    volatility_zones = analysis.get("volatility_zones", [])
    if volatility_zones:
        volatility = "عالي" if volatility_zones[0]["strength"] > 70 else "متوسط" if volatility_zones[0]["strength"] > 40 else "منخفض"
    else:
        volatility = "متوسط"
    
    return {
        "trend": trend,
        "trend_strength": min(100, int(trend_strength)),
        "volatility": volatility,
    }