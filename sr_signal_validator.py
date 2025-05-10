"""
نظام للتحقق من صحة الإشارات عند نقاط الدعم والمقاومة ونقاط التذبذب والتجميع
يستخدم هذا النظام لمنع الإشارات الخاطئة عند هذه النقاط المهمة
"""

import logging
from datetime import datetime
import numpy as np
from advanced_sr_analyzer import analyze_sr_levels
from pocket_option_otc_pairs import is_valid_otc_pair

# تهيئة نظام السجلات
logger = logging.getLogger(__name__)

class SRSignalValidator:
    """نظام التحقق من صحة الإشارات عند نقاط الدعم والمقاومة والتذبذب والتجميع"""
    
    def __init__(self):
        """تهيئة نظام التحقق من صحة الإشارات"""
        # معلمات التكوين
        self.price_proximity_threshold = 0.002  # حد القرب من مستويات الدعم والمقاومة (0.2%)
        self.bounce_confidence_threshold = 70  # الحد الأدنى لثقة الارتداد
        self.breakout_confidence_threshold = 80  # الحد الأدنى لثقة الاختراق
        self.volume_confirmation_needed = True  # اشتراط تأكيد حجم التداول
        self.min_touch_count = 2  # الحد الأدنى لعدد مرات لمس المستوى
        
        # معلمات خاصة بأزواج OTC من منصة Pocket Option
        self.otc_bounce_confidence_threshold = 65  # عتبة أقل للارتداد في أزواج OTC
        self.otc_breakout_confidence_threshold = 75  # عتبة أقل للاختراق في أزواج OTC
        self.otc_min_touch_count = 1  # عدد مرات لمس أقل لمستويات OTC
        self.otc_price_proximity_threshold = 0.0025  # حد أعلى للقرب من مستويات الدعم والمقاومة في أزواج OTC (0.25%)
        
        logger.info("✅ تم تهيئة نظام التحقق من صحة الإشارات في نقاط الدعم والمقاومة")
    
    def validate_signal(self, signal, candles):
        """
        التحقق من صحة الإشارة بناءً على تحليل نقاط الدعم والمقاومة
        
        Args:
            signal (dict): معلومات الإشارة المراد التحقق منها
            candles (list): بيانات الشموع للتحليل
            
        Returns:
            tuple: (صحة الإشارة، الثقة، السبب)
        """
        if not signal or not candles or len(candles) < 20:
            return True, 100, "عدد الشموع غير كافٍ للتحليل، تم قبول الإشارة افتراضياً"
        
        try:
            direction = signal.get('direction', '')
            current_price = candles[-1]['close']
            pair_symbol = signal.get('pair', '')
            
            # التحقق مما إذا كان الزوج من أزواج OTC
            is_otc = False
            # التحقق من معلومة الزوج في الإشارة أولاً
            if signal.get('is_otc_pair'):
                is_otc = True
                logger.info(f"⚠️ تحليل إشارة لزوج OTC (من متعدد الإطارات): {pair_symbol}")
            # إذا لم تكن المعلومة متوفرة في الإشارة، نتحقق من خلال وحدة pocket_option_otc_pairs
            elif pair_symbol and is_valid_otc_pair(pair_symbol):
                is_otc = True
                logger.info(f"⚠️ تحليل إشارة لزوج OTC من منصة Pocket Option: {pair_symbol}")
            else:
                logger.info(f"تحليل إشارة لزوج عادي: {pair_symbol}")
                
            # تعديل عتبات التحقق بناءً على نوع الزوج
            if is_otc:
                self.price_proximity_threshold = self.otc_price_proximity_threshold
                self.bounce_confidence_threshold = self.otc_bounce_confidence_threshold
                self.breakout_confidence_threshold = self.otc_breakout_confidence_threshold
                self.min_touch_count = self.otc_min_touch_count
            else:
                # إعادة العتبات إلى القيم الافتراضية للأزواج العادية
                self.price_proximity_threshold = 0.002
                self.bounce_confidence_threshold = 70
                self.breakout_confidence_threshold = 80
                self.min_touch_count = 2
            
            # تحليل نقاط الدعم والمقاومة - تمرير معلومة كون الزوج من أزواج OTC أم لا
            sr_analysis = analyze_sr_levels(candles, is_otc_pair=is_otc)
            
            # التحقق من الإشارة بناءً على تحليل نقاط الدعم والمقاومة
            if direction == 'BUY':
                return self._validate_buy_signal(signal, candles, sr_analysis, current_price)
            elif direction == 'SELL':
                return self._validate_sell_signal(signal, candles, sr_analysis, current_price)
            else:
                return True, 100, "اتجاه الإشارة غير محدد، تم قبول الإشارة افتراضياً"
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من صحة الإشارة: {e}")
            return True, 90, "حدث خطأ في التحليل، تم قبول الإشارة افتراضياً"
    
    def _validate_buy_signal(self, signal, candles, sr_analysis, current_price):
        """
        التحقق من صحة إشارة الشراء
        
        Args:
            signal (dict): معلومات الإشارة
            candles (list): بيانات الشموع
            sr_analysis (dict): نتائج تحليل نقاط الدعم والمقاومة
            current_price (float): السعر الحالي
            
        Returns:
            tuple: (صحة الإشارة، الثقة، السبب)
        """
        support_levels = sr_analysis.get('support_levels', [])
        resistance_levels = sr_analysis.get('resistance_levels', [])
        accumulation_zones = sr_analysis.get('accumulation_zones', [])
        breakout_points = sr_analysis.get('breakout_points', [])
        
        # تحديد ما إذا كان التحليل لزوج OTC (قدمته وظيفة تحليل SR)
        is_otc = sr_analysis.get('is_otc', False) or signal.get('is_otc_pair', False)
        
        # تعديل بعض المعلمات لتناسب أزواج OTC
        confidence_boost = 0
        if is_otc:
            # إضافة تعزيز الثقة لأزواج OTC
            confidence_boost = 10
            logger.info(f"💹 تطبيق تعزيز خاص لثقة تحليل زوج OTC بمقدار {confidence_boost}%")
        
        # 1. التحقق من القرب من مستوى دعم قوي (يفضل الشراء بالقرب من الدعم)
        close_to_support = False
        for support in support_levels:
            price_diff_percent = (current_price - support['price']) / support['price']
            if abs(price_diff_percent) < self.price_proximity_threshold and support['strength'] > 60:
                close_to_support = True
                
                # التحقق من أن السعر فوق مستوى الدعم (ارتد بالفعل)
                if current_price > support['price'] and price_diff_percent > 0:
                    base_confidence = min(100, support['strength'] + 20)
                    confidence = min(100, base_confidence + confidence_boost)
                    reason = f"إشارة شراء قوية: ارتداد من مستوى دعم قوي {support['price']:.5f}"
                    if is_otc:
                        reason += " (زوج OTC)"
                    return True, confidence, reason
                # التحقق من أن السعر تحت مستوى الدعم (احتمال إشارة خاطئة)
                elif current_price <= support['price']:
                    # قد تكون إشارة خاطئة - السعر أقل من مستوى الدعم
                    if self._is_support_broken(candles, support['price']):
                        reason = f"إشارة شراء ضعيفة: كسر مستوى الدعم {support['price']:.5f}"
                        if is_otc:
                            # أزواج OTC تكون أكثر تقلباً، لذا نعطي فرصة أكبر
                            return False, 30, reason + " (زوج OTC - تقلب عالٍ)"
                        return False, 20, reason
                    else:
                        # ربما يكون اختبار للدعم قبل الارتداد
                        base_confidence = 70
                        confidence = min(100, base_confidence + confidence_boost)
                        reason = f"إشارة شراء محتملة: اختبار لمستوى دعم {support['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
        
        # 2. التحقق من القرب من مستوى مقاومة قوي (لا يفضل الشراء بالقرب من المقاومة)
        close_to_resistance = False
        for resistance in resistance_levels:
            price_diff_percent = (resistance['price'] - current_price) / current_price
            if abs(price_diff_percent) < self.price_proximity_threshold and resistance['strength'] > 60:
                close_to_resistance = True
                
                # التحقق من اختراق المقاومة (إشارة إيجابية لاستمرار الصعود)
                if current_price > resistance['price']:
                    # تأكيد الاختراق بشمعة كاملة فوق المقاومة
                    if self._confirm_breakout(candles, resistance['price'], 'up'):
                        confidence = min(100, 90 + confidence_boost)
                        reason = f"إشارة شراء قوية: اختراق مستوى مقاومة {resistance['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
                    else:
                        # اختراق غير مؤكد
                        confidence = min(100, 60 + confidence_boost)
                        reason = f"إشارة شراء متوسطة: اختراق غير مؤكد لمستوى مقاومة {resistance['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
                else:
                    # السعر تحت المقاومة مباشرة (احتمال ارتداد لأسفل)
                    reason = f"إشارة شراء ضعيفة: قرب من مستوى مقاومة قوي {resistance['price']:.5f}"
                    if is_otc:
                        # أزواج OTC ذات قوة اختراق أعلى
                        return False, 35, reason + " (زوج OTC)"
                    return False, 30, reason
        
        # 3. التحقق من وجود منطقة تجميع (إيجابي للشراء)
        in_accumulation_zone = False
        for zone in accumulation_zones:
            if zone['type'] == 'accumulation' and abs(current_price - zone['price_level']) / zone['price_level'] < 0.01:
                in_accumulation_zone = True
                confidence = min(100, 60 + zone['strength'] + confidence_boost)
                reason = f"إشارة شراء قوية: السعر في منطقة تجميع"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
        
        # 4. التحقق من اختراق محتمل
        potential_breakout = False
        for point in breakout_points:
            if point['direction'] == 'UP' and point['type'] == 'resistance':
                potential_breakout = True
                confidence = min(100, 50 + point['strength'] + confidence_boost)
                reason = f"إشارة شراء قوية: اختراق محتمل لمستوى مقاومة {point['price']:.5f}"
                if is_otc:
                    reason += " (زوج OTC - تقلب أعلى)"
                return True, confidence, reason
        
        # 5. التحقق من المسافة بين السعر وأقرب مستويات الدعم والمقاومة
        risk_reward = self._evaluate_risk_reward(current_price, 'BUY', support_levels, resistance_levels)
        if risk_reward is not None:
            if risk_reward > 2.0:
                confidence = min(100, 80 + confidence_boost)
                reason = f"إشارة شراء قوية: نسبة المخاطرة/العائد مناسبة ({risk_reward:.2f})"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
            elif risk_reward < 1.0:
                # حتى في حالة المخاطرة السيئة، قد تكون أزواج OTC أكثر تقلباً وتحتاج تقديراً مختلفاً
                if is_otc:
                    return False, 45, f"إشارة شراء ضعيفة: نسبة المخاطرة/العائد غير مناسبة ({risk_reward:.2f}) لكن مع مراعاة تقلب زوج OTC"
                return False, 40, f"إشارة شراء ضعيفة: نسبة المخاطرة/العائد غير مناسبة ({risk_reward:.2f})"
            else:
                # حالة متوسطة
                pass
        
        # إذا لم يتم اتخاذ قرار محدد، نعود إلى التقييم العام
        # في حالة عدم القرب من مستويات دعم أو مقاومة، لا يوجد سبب لرفض الإشارة
        if not close_to_support and not close_to_resistance and not in_accumulation_zone and not potential_breakout:
            # التحقق من الاتجاه العام
            trend = self._analyze_trend(candles, 14)
            if trend == 'UP':
                confidence = min(100, 75 + confidence_boost)
                reason = "إشارة شراء جيدة: متوافقة مع الاتجاه العام الصاعد"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
            elif trend == 'DOWN':
                if is_otc:
                    # أزواج OTC قد تكون أكثر تقلباً، لذا نعطي تقديراً أقل سلبية
                    return False, 45, "إشارة شراء ضعيفة: معاكسة للاتجاه العام الهابط (زوج OTC - تقلب أعلى)"
                return False, 40, "إشارة شراء ضعيفة: معاكسة للاتجاه العام الهابط"
            else:
                confidence = min(100, 60 + confidence_boost)
                reason = "إشارة شراء متوسطة: لا توجد ملاحظات خاصة"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
        
        # الحالة الافتراضية (إذا لم يتم تحديد حالة خاصة)
        confidence = min(100, 60 + confidence_boost/2)  # نصف التعزيز للحالة الافتراضية
        reason = "إشارة شراء متوسطة: لا توجد مؤشرات قوية للرفض أو القبول"
        if is_otc:
            reason += " (زوج OTC)"
        return True, confidence, reason
    
    def _validate_sell_signal(self, signal, candles, sr_analysis, current_price):
        """
        التحقق من صحة إشارة البيع
        
        Args:
            signal (dict): معلومات الإشارة
            candles (list): بيانات الشموع
            sr_analysis (dict): نتائج تحليل نقاط الدعم والمقاومة
            current_price (float): السعر الحالي
            
        Returns:
            tuple: (صحة الإشارة، الثقة، السبب)
        """
        support_levels = sr_analysis.get('support_levels', [])
        resistance_levels = sr_analysis.get('resistance_levels', [])
        accumulation_zones = sr_analysis.get('accumulation_zones', [])
        breakout_points = sr_analysis.get('breakout_points', [])
        
        # تحديد ما إذا كان التحليل لزوج OTC (قدمته وظيفة تحليل SR)
        is_otc = sr_analysis.get('is_otc', False) or signal.get('is_otc_pair', False)
        
        # تعديل بعض المعلمات لتناسب أزواج OTC
        confidence_boost = 0
        if is_otc:
            # إضافة تعزيز الثقة لأزواج OTC
            confidence_boost = 10
            logger.info(f"💹 تطبيق تعزيز خاص لثقة تحليل زوج OTC بمقدار {confidence_boost}%")
        
        # 1. التحقق من القرب من مستوى مقاومة قوي (يفضل البيع بالقرب من المقاومة)
        close_to_resistance = False
        for resistance in resistance_levels:
            price_diff_percent = (resistance['price'] - current_price) / current_price
            if abs(price_diff_percent) < self.price_proximity_threshold and resistance['strength'] > 60:
                close_to_resistance = True
                
                # التحقق من أن السعر تحت مستوى المقاومة (ارتد بالفعل)
                if current_price < resistance['price'] and price_diff_percent > 0:
                    confidence = min(100, resistance['strength'] + 20 + confidence_boost)
                    reason = f"إشارة بيع قوية: ارتداد من مستوى مقاومة قوي {resistance['price']:.5f}"
                    if is_otc:
                        reason += " (زوج OTC)"
                    return True, confidence, reason
                # التحقق من أن السعر فوق مستوى المقاومة (احتمال إشارة خاطئة)
                elif current_price >= resistance['price']:
                    # قد تكون إشارة خاطئة - السعر أعلى من مستوى المقاومة
                    if self._is_resistance_broken(candles, resistance['price']):
                        reason = f"إشارة بيع ضعيفة: كسر مستوى المقاومة {resistance['price']:.5f}"
                        if is_otc:
                            # أزواج OTC تكون أكثر تقلباً، نعطي فرصة أكبر
                            return False, 30, reason + " (زوج OTC - تقلب عالٍ)"
                        return False, 20, reason
                    else:
                        # ربما يكون اختبار للمقاومة قبل الارتداد
                        confidence = min(100, 70 + confidence_boost)
                        reason = f"إشارة بيع محتملة: اختبار لمستوى مقاومة {resistance['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
        
        # 2. التحقق من القرب من مستوى دعم قوي (لا يفضل البيع بالقرب من الدعم)
        close_to_support = False
        for support in support_levels:
            price_diff_percent = (current_price - support['price']) / support['price']
            if abs(price_diff_percent) < self.price_proximity_threshold and support['strength'] > 60:
                close_to_support = True
                
                # التحقق من اختراق الدعم (إشارة إيجابية لاستمرار الهبوط)
                if current_price < support['price']:
                    # تأكيد الاختراق بشمعة كاملة تحت الدعم
                    if self._confirm_breakout(candles, support['price'], 'down'):
                        confidence = min(100, 90 + confidence_boost)
                        reason = f"إشارة بيع قوية: اختراق مستوى دعم {support['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
                    else:
                        # اختراق غير مؤكد
                        confidence = min(100, 60 + confidence_boost)
                        reason = f"إشارة بيع متوسطة: اختراق غير مؤكد لمستوى دعم {support['price']:.5f}"
                        if is_otc:
                            reason += " (زوج OTC)"
                        return True, confidence, reason
                else:
                    # السعر فوق الدعم مباشرة (احتمال ارتداد لأعلى)
                    reason = f"إشارة بيع ضعيفة: قرب من مستوى دعم قوي {support['price']:.5f}"
                    if is_otc:
                        # أزواج OTC تكون أكثر تقلباً، نعطي فرصة أكبر
                        return False, 35, reason + " (زوج OTC - تقلب عالٍ)"
                    return False, 30, reason
        
        # 3. التحقق من وجود منطقة توزيع (إيجابي للبيع)
        in_distribution_zone = False
        for zone in accumulation_zones:
            if zone['type'] == 'distribution' and abs(current_price - zone['price_level']) / zone['price_level'] < 0.01:
                in_distribution_zone = True
                confidence = min(100, 60 + zone['strength'] + confidence_boost)
                reason = f"إشارة بيع قوية: السعر في منطقة توزيع"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
        
        # 4. التحقق من اختراق محتمل
        potential_breakout = False
        for point in breakout_points:
            if point['direction'] == 'DOWN' and point['type'] == 'support':
                potential_breakout = True
                confidence = min(100, 50 + point['strength'] + confidence_boost)
                reason = f"إشارة بيع قوية: اختراق محتمل لمستوى دعم {point['price']:.5f}"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
        
        # 5. التحقق من المسافة بين السعر وأقرب مستويات الدعم والمقاومة
        risk_reward = self._evaluate_risk_reward(current_price, 'SELL', support_levels, resistance_levels)
        if risk_reward is not None:
            if risk_reward > 2.0:
                confidence = min(100, 80 + confidence_boost)
                reason = f"إشارة بيع قوية: نسبة المخاطرة/العائد مناسبة ({risk_reward:.2f})"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
            elif risk_reward < 1.0:
                confidence = min(100, 40 + (confidence_boost // 2))  # نصف التعزيز في الإشارات الضعيفة
                reason = f"إشارة بيع ضعيفة: نسبة المخاطرة/العائد غير مناسبة ({risk_reward:.2f})"
                if is_otc:
                    reason += " (زوج OTC)"
                return False, confidence, reason
            else:
                # حالة متوسطة
                pass
        
        # إذا لم يتم اتخاذ قرار محدد، نعود إلى التقييم العام
        # في حالة عدم القرب من مستويات دعم أو مقاومة، لا يوجد سبب لرفض الإشارة
        if not close_to_support and not close_to_resistance and not in_distribution_zone and not potential_breakout:
            # التحقق من الاتجاه العام
            trend = self._analyze_trend(candles, 14)
            if trend == 'DOWN':
                confidence = min(100, 75 + confidence_boost)
                reason = "إشارة بيع جيدة: متوافقة مع الاتجاه العام الهابط"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
            elif trend == 'UP':
                confidence = min(100, 40 + (confidence_boost // 2))  # نصف التعزيز في الإشارات الضعيفة
                reason = "إشارة بيع ضعيفة: معاكسة للاتجاه العام الصاعد"
                if is_otc:
                    reason += " (زوج OTC)"
                return False, confidence, reason
            else:
                confidence = min(100, 60 + confidence_boost)
                reason = "إشارة بيع متوسطة: لا توجد ملاحظات خاصة"
                if is_otc:
                    reason += " (زوج OTC)"
                return True, confidence, reason
        
        # الحالة الافتراضية (إذا لم يتم تحديد حالة خاصة)
        confidence = min(100, 60 + confidence_boost)
        reason = "إشارة بيع متوسطة: لا توجد مؤشرات قوية للرفض أو القبول"
        if is_otc:
            reason += " (زوج OTC)"
        return True, confidence, reason
    
    def _is_support_broken(self, candles, support_price):
        """
        التحقق مما إذا كان مستوى الدعم قد تم كسره
        
        Args:
            candles (list): بيانات الشموع
            support_price (float): سعر مستوى الدعم
            
        Returns:
            bool: ما إذا كان مستوى الدعم قد تم كسره
        """
        # نتحقق من آخر 3 شموع
        recent_candles = candles[-3:]
        
        # حساب عدد الشموع التي أغلقت تحت مستوى الدعم
        closed_below_count = sum(1 for candle in recent_candles if candle['close'] < support_price)
        
        # إذا كانت 2 من 3 شموع على الأقل أغلقت تحت مستوى الدعم، نعتبر أن الدعم قد كسر
        return closed_below_count >= 2
    
    def _is_resistance_broken(self, candles, resistance_price):
        """
        التحقق مما إذا كان مستوى المقاومة قد تم كسره
        
        Args:
            candles (list): بيانات الشموع
            resistance_price (float): سعر مستوى المقاومة
            
        Returns:
            bool: ما إذا كان مستوى المقاومة قد تم كسره
        """
        # نتحقق من آخر 3 شموع
        recent_candles = candles[-3:]
        
        # حساب عدد الشموع التي أغلقت فوق مستوى المقاومة
        closed_above_count = sum(1 for candle in recent_candles if candle['close'] > resistance_price)
        
        # إذا كانت 2 من 3 شموع على الأقل أغلقت فوق مستوى المقاومة، نعتبر أن المقاومة قد كسرت
        return closed_above_count >= 2
    
    def _confirm_breakout(self, candles, level_price, direction):
        """
        تأكيد اختراق مستوى دعم أو مقاومة
        
        Args:
            candles (list): بيانات الشموع
            level_price (float): سعر المستوى
            direction (str): اتجاه الاختراق ('up' أو 'down')
            
        Returns:
            bool: ما إذا كان الاختراق مؤكداً
        """
        if len(candles) < 3:
            return False
        
        # التحقق من حجم التداول إذا كان متاحاً
        recent_candles = candles[-3:]
        avg_volume = sum(candle.get('volume', 0) for candle in candles[-10:-3]) / 7 if len(candles) >= 10 else 0
        
        if direction == 'up':
            # شروط تأكيد اختراق المقاومة للأعلى:
            # 1. آخر شمعة أغلقت فوق المستوى
            breakout_confirmed = recent_candles[-1]['close'] > level_price
            
            # 2. شمعة قوية (جسم كبير)
            strong_candle = (recent_candles[-1]['close'] - recent_candles[-1]['open']) / recent_candles[-1]['open'] > 0.0015  # 0.15%
            
            # 3. حجم تداول مرتفع (إذا كان متاحاً)
            high_volume = recent_candles[-1].get('volume', 0) > avg_volume * 1.2 if avg_volume > 0 else True
            
            return breakout_confirmed and (strong_candle or high_volume)
            
        elif direction == 'down':
            # شروط تأكيد اختراق الدعم للأسفل:
            # 1. آخر شمعة أغلقت تحت المستوى
            breakout_confirmed = recent_candles[-1]['close'] < level_price
            
            # 2. شمعة قوية (جسم كبير)
            strong_candle = (recent_candles[-1]['open'] - recent_candles[-1]['close']) / recent_candles[-1]['open'] > 0.0015  # 0.15%
            
            # 3. حجم تداول مرتفع (إذا كان متاحاً)
            high_volume = recent_candles[-1].get('volume', 0) > avg_volume * 1.2 if avg_volume > 0 else True
            
            return breakout_confirmed and (strong_candle or high_volume)
            
        return False
    
    def _evaluate_risk_reward(self, current_price, direction, support_levels, resistance_levels):
        """
        تقييم نسبة المخاطرة/العائد
        
        Args:
            current_price (float): السعر الحالي
            direction (str): اتجاه الإشارة ('BUY' أو 'SELL')
            support_levels (list): مستويات الدعم
            resistance_levels (list): مستويات المقاومة
            
        Returns:
            float: نسبة المخاطرة/العائد، أو None إذا لم يمكن تقييمها
        """
        if not support_levels or not resistance_levels:
            return None
        
        # ترتيب مستويات الدعم والمقاومة
        sorted_supports = sorted(support_levels, key=lambda x: x['price'], reverse=True)
        sorted_resistances = sorted(resistance_levels, key=lambda x: x['price'])
        
        if direction == 'BUY':
            # أقرب مستوى دعم تحت السعر الحالي
            closest_support = None
            for support in sorted_supports:
                if support['price'] < current_price:
                    closest_support = support
                    break
            
            # أقرب مستوى مقاومة فوق السعر الحالي
            closest_resistance = None
            for resistance in sorted_resistances:
                if resistance['price'] > current_price:
                    closest_resistance = resistance
                    break
            
            if closest_support and closest_resistance:
                risk = current_price - closest_support['price']
                reward = closest_resistance['price'] - current_price
                
                if risk > 0:
                    return reward / risk
        
        elif direction == 'SELL':
            # أقرب مستوى مقاومة فوق السعر الحالي
            closest_resistance = None
            for resistance in sorted_resistances:
                if resistance['price'] > current_price:
                    closest_resistance = resistance
                    break
            
            # أقرب مستوى دعم تحت السعر الحالي
            closest_support = None
            for support in sorted_supports:
                if support['price'] < current_price:
                    closest_support = support
                    break
            
            if closest_support and closest_resistance:
                risk = closest_resistance['price'] - current_price
                reward = current_price - closest_support['price']
                
                if risk > 0:
                    return reward / risk
        
        return None
    
    def _analyze_trend(self, candles, period=14):
        """
        تحليل الاتجاه العام للسعر
        
        Args:
            candles (list): بيانات الشموع
            period (int): فترة التحليل
            
        Returns:
            str: الاتجاه العام ('UP', 'DOWN', أو 'SIDEWAYS')
        """
        if len(candles) < period:
            return 'SIDEWAYS'
        
        # استخراج أسعار الإغلاق
        closes = [candle['close'] for candle in candles[-period:]]
        
        # حساب الانحدار الخطي البسيط
        x = list(range(len(closes)))
        mean_x = sum(x) / len(x)
        mean_y = sum(closes) / len(closes)
        
        numerator = sum((x[i] - mean_x) * (closes[i] - mean_y) for i in range(len(x)))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # تحديد الاتجاه بناءً على الانحدار
        threshold = 0.0001 * mean_y  # عتبة لتحديد الاتجاه القوي
        
        if slope > threshold:
            return 'UP'
        elif slope < -threshold:
            return 'DOWN'
        else:
            return 'SIDEWAYS'

# إنشاء مثيل للاستخدام العالمي
sr_validator = SRSignalValidator()

def validate_signal_at_sr_levels(signal, candles):
    """
    التحقق من صحة الإشارة عند نقاط الدعم والمقاومة
    
    Args:
        signal (dict): معلومات الإشارة
        candles (list): بيانات الشموع
        
    Returns:
        tuple: (صحة الإشارة، الثقة، السبب)
    """
    # تحديد ما إذا كان الزوج من أزواج OTC
    is_otc_pair = signal.get('is_otc_pair', False)
    if is_otc_pair:
        # إضافة معلومات إضافية إلى السجل للتشخيص
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"💹 بدء التحقق من صحة إشارة لزوج OTC: {signal.get('pair', 'غير معروف')}")
    
    # إضافة معلومات OTC إلى الإشارة
    if is_otc_pair and not signal.get('is_otc', False):
        signal['is_otc'] = True
    
    return sr_validator.validate_signal(signal, candles)

def is_price_at_key_level(price, candles, is_otc_pair=False):
    """
    التحقق مما إذا كان السعر عند مستوى رئيسي (دعم أو مقاومة)
    
    Args:
        price (float): السعر المراد التحقق منه
        candles (list): بيانات الشموع
        is_otc_pair (bool): ما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
        
    Returns:
        tuple: (ما إذا كان السعر عند مستوى رئيسي، نوع المستوى، قوة المستوى)
    """
    # تحليل نقاط الدعم والمقاومة
    sr_analysis = analyze_sr_levels(candles, is_otc_pair=is_otc_pair)
    
    support_levels = sr_analysis.get('support_levels', [])
    resistance_levels = sr_analysis.get('resistance_levels', [])
    
    # التحقق من القرب من مستوى دعم
    for support in support_levels:
        price_diff_percent = abs(price - support['price']) / support['price']
        if price_diff_percent < sr_validator.price_proximity_threshold:
            return True, 'support', support['strength']
    
    # التحقق من القرب من مستوى مقاومة
    for resistance in resistance_levels:
        price_diff_percent = abs(price - resistance['price']) / resistance['price']
        if price_diff_percent < sr_validator.price_proximity_threshold:
            return True, 'resistance', resistance['strength']
    
    # ليس قريباً من أي مستوى رئيسي
    return False, None, 0

def forecast_price_movement(candles, is_otc_pair=False):
    """
    التنبؤ بحركة السعر المستقبلية بناءً على تحليل نقاط الدعم والمقاومة
    
    Args:
        candles (list): بيانات الشموع
        is_otc_pair (bool): ما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
        
    Returns:
        dict: توقعات حركة السعر
    """
    # تحليل نقاط الدعم والمقاومة
    sr_analysis = analyze_sr_levels(candles, is_otc_pair=is_otc_pair)
    current_price = sr_analysis.get('current_price')
    
    if not current_price:
        return {"error": "لا يمكن تحديد السعر الحالي"}
    
    support_levels = sr_analysis.get('support_levels', [])
    resistance_levels = sr_analysis.get('resistance_levels', [])
    breakout_points = sr_analysis.get('breakout_points', [])
    
    # تحديد أقرب مستويات الدعم والمقاومة
    sorted_supports = sorted(support_levels, key=lambda x: abs(x['price'] - current_price))
    sorted_resistances = sorted(resistance_levels, key=lambda x: abs(x['price'] - current_price))
    
    closest_support = sorted_supports[0] if sorted_supports else None
    closest_resistance = sorted_resistances[0] if sorted_resistances else None
    
    # تحليل الاتجاه العام
    trend = sr_validator._analyze_trend(candles, 14)
    
    # التحقق من القرب من مستويات الدعم أو المقاومة
    near_support = False
    near_resistance = False
    
    if closest_support:
        support_distance = (current_price - closest_support['price']) / current_price
        near_support = support_distance < 0.005  # 0.5%
    
    if closest_resistance:
        resistance_distance = (closest_resistance['price'] - current_price) / current_price
        near_resistance = resistance_distance < 0.005  # 0.5%
    
    # تحديد سيناريوهات الحركة المستقبلية
    scenarios = []
    
    # سيناريو 1: الارتداد من الدعم
    if near_support and trend != 'DOWN':
        scenarios.append({
            "direction": "UP",
            "type": "bounce_from_support",
            "target_price": closest_resistance['price'] if closest_resistance else current_price * 1.01,
            "probability": min(90, 60 + closest_support.get('strength', 0) // 2),
            "stop_loss": closest_support['price'] * 0.998
        })
    
    # سيناريو 2: الارتداد من المقاومة
    if near_resistance and trend != 'UP':
        scenarios.append({
            "direction": "DOWN",
            "type": "bounce_from_resistance",
            "target_price": closest_support['price'] if closest_support else current_price * 0.99,
            "probability": min(90, 60 + closest_resistance.get('strength', 0) // 2),
            "stop_loss": closest_resistance['price'] * 1.002
        })
    
    # سيناريو 3: كسر الدعم
    if near_support and trend == 'DOWN':
        # حساب الهدف بعد كسر الدعم (مقدار الانخفاض من آخر قمة إلى الدعم)
        recent_high = max(candle['high'] for candle in candles[-20:])
        projection = current_price - (recent_high - current_price)
        
        scenarios.append({
            "direction": "DOWN",
            "type": "break_support",
            "target_price": min(projection, closest_support['price'] * 0.99),
            "probability": min(80, 40 + closest_support.get('strength', 0) // 2),
            "stop_loss": closest_support['price'] * 1.002
        })
    
    # سيناريو 4: كسر المقاومة
    if near_resistance and trend == 'UP':
        # حساب الهدف بعد كسر المقاومة (مقدار الارتفاع من آخر قاع إلى المقاومة)
        recent_low = min(candle['low'] for candle in candles[-20:])
        projection = current_price + (current_price - recent_low)
        
        scenarios.append({
            "direction": "UP",
            "type": "break_resistance",
            "target_price": max(projection, closest_resistance['price'] * 1.01),
            "probability": min(80, 40 + closest_resistance.get('strength', 0) // 2),
            "stop_loss": closest_resistance['price'] * 0.998
        })
    
    # سيناريو 5: استمرار الاتجاه العام
    if not near_support and not near_resistance:
        if trend == 'UP':
            scenarios.append({
                "direction": "UP",
                "type": "trend_continuation",
                "target_price": current_price * 1.005,
                "probability": 70,
                "stop_loss": current_price * 0.997
            })
        elif trend == 'DOWN':
            scenarios.append({
                "direction": "DOWN",
                "type": "trend_continuation",
                "target_price": current_price * 0.995,
                "probability": 70,
                "stop_loss": current_price * 1.003
            })
        else:
            scenarios.append({
                "direction": "SIDEWAYS",
                "type": "range_bound",
                "upper_bound": current_price * 1.003,
                "lower_bound": current_price * 0.997,
                "probability": 60
            })
    
    # اختيار أفضل سيناريو
    if scenarios:
        scenarios.sort(key=lambda x: x.get('probability', 0), reverse=True)
        best_scenario = scenarios[0]
    else:
        best_scenario = {
            "direction": "UNKNOWN",
            "probability": 50,
            "message": "لا يمكن تحديد سيناريو واضح لحركة السعر"
        }
    
    return {
        "current_price": current_price,
        "trend": trend,
        "closest_support": closest_support,
        "closest_resistance": closest_resistance,
        "scenarios": scenarios,
        "best_scenario": best_scenario
    }