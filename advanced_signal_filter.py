"""
نظام تصفية متقدم للإشارات
يقوم بتقييم جودة الإشارات وتصفيتها بناءً على معايير متعددة
لزيادة دقة الإشارات وتحسين نسبة الربح
"""

import logging
import numpy as np
from datetime import datetime, time
import importlib

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedSignalFilter:
    """نظام تصفية متقدم للإشارات لتحسين جودة الإشارات المرسلة"""
    
    def __init__(self):
        """تهيئة نظام التصفية المتقدم والمحسن"""
        logger.info("تم تهيئة نظام تصفية الإشارات المتقدم والمحسن")
        
        # معايير التصفية المحسنة للحصول على إشارات أكثر دقة
        self.min_quality_score = 75  # تخفيض الحد الأدنى لدرجة الجودة لزيادة عدد الإشارات OTC (0-100)
        self.min_probability = 75  # تخفيض الحد الأدنى للاحتمالية المقبولة لأزواج OTC (%)
        self.min_pattern_strength = 65  # تخفيض الحد الأدنى لقوة نمط الشموع لأزواج OTC (%)
        self.risk_reward_threshold = 1.5  # تخفيض الحد الأدنى لنسبة المخاطرة/العائد
        
        # معايير إضافية للتصفية المحسنة
        self.min_sr_validation_score = 60  # تخفيض الحد الأدنى لتأكيد مستويات الدعم والمقاومة للسماح بمزيد من إشارات OTC
        self.max_market_volatility = 85  # الحد الأقصى لتقلب السوق المقبول
        self.min_consecutive_candles = 2  # تخفيض الحد الأدنى لعدد الشموع المتتالية لأزواج OTC
        
        # أوزان معايير التقييم المحسنة
        self.weights = {
            'probability': 0.22,  # وزن احتمالية النجاح
            'sr_validation': 0.25,  # وزن التحقق من مناطق الدعم والمقاومة
            'pattern_strength': 0.20,  # وزن قوة نمط الشموع
            'timeframe_alignment': 0.15,  # وزن توافق الإطارات الزمنية
            'risk_reward': 0.10,  # وزن نسبة المخاطرة/العائد
            'market_volatility': 0.05,  # وزن تقلب السوق
            'consecutive_pattern': 0.08,  # إضافة وزن لنمط الشموع المتتالية
            'divergence': 0.10  # إضافة وزن للانحراف بين السعر والمؤشرات
        }
        
        # قائمة الأوقات ذات الجودة العالية والمنخفضة
        self.high_quality_hours = [
            (time(8, 0), time(11, 0)),  # جلسة لندن الصباحية 8-11 صباحًا
            (time(13, 0), time(16, 0)),  # جلسة نيويورك النشطة 1-4 مساءً
            (time(19, 0), time(22, 0))   # جلسة آسيا المبكرة 7-10 مساءً
        ]
        
        self.low_quality_hours = [
            (time(0, 0), time(2, 0)),   # ساعات منتصف الليل 12-2 صباحًا
            (time(12, 0), time(13, 0))  # فترة الغداء الأوروبية 12-1 ظهرًا
        ]
        
        # الأزواج OTC الموثوقة ذات العائد الجيد - تم توسيع القائمة لتشمل المزيد من أزواج Pocket Option
        self.high_reliability_pairs = [
            # أزواج OTC الأساسية ذات الموثوقية العالية جداً
            'EURUSD-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'GBPUSD-OTC',
            'EURGBP-OTC', 'AUDJPY-OTC', 'USDCAD-OTC', 'GBPJPY-OTC',
            # أزواج OTC إضافية ذات أداء جيد
            'AUDUSD-OTC', 'NZDUSD-OTC', 'USDCHF-OTC', 'CADCHF-OTC',
            'GBPCAD-OTC', 'EURAUD-OTC', 'AUDCAD-OTC', 'AUDNZD-OTC',
            # أزواج OTC للسلع
            'XAUUSD-OTC', 'XAGUSD-OTC'
        ]
        
        # الأوزان المخصصة للإطارات الزمنية المختلفة - تم تخصيصها لأزواج OTC
        self.timeframe_weights = {
            'default': {  # الأوزان الافتراضية للأزواج العادية
                'M1': 0.5,    # الإطار الزمني 1 دقيقة
                'M5': 0.3,    # الإطار الزمني 5 دقائق
                'M15': 0.2    # الإطار الزمني 15 دقيقة
            },
            'otc': {      # أوزان مخصصة لأزواج OTC
                'M1': 0.6,    # زيادة وزن الإطار الزمني 1 دقيقة للأزواج OTC
                'M5': 0.3,    # وزن الإطار الزمني 5 دقائق
                'M15': 0.1    # تقليل وزن الإطار الزمني 15 دقيقة للأزواج OTC
            }
        }
    
    def filter_signal(self, signal, candles=None, multi_timeframe_analysis=None):
        """
        تصفية الإشارة بناءً على معايير الجودة المتعددة ونقاط الدعم والمقاومة
        
        Args:
            signal (dict): معلومات الإشارة المقترحة للتصفية
            candles (list, optional): بيانات الشموع للتحليل الإضافي
            multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
            
        Returns:
            tuple: (قبول الإشارة, درجة الجودة, سبب القبول أو الرفض)
        """
        if not signal:
            return False, 0, "لا توجد إشارة للتصفية"
            
        # التحقق مما إذا كان الزوج من أزواج OTC
        is_otc_pair = False
        pair_symbol = signal.get('pair_symbol', '')
        try:
            from pocket_option_otc_pairs import is_otc_pair as check_is_otc
            is_otc_pair = check_is_otc(pair_symbol)
            if is_otc_pair:
                logger.info(f"🎯 تمت اكتشاف إشارة خاصة بزوج OTC: {pair_symbol}")
        except ImportError:
            # التحقق بناءً على اسم الزوج إذا لم تكن وحدة التحقق متاحة
            is_otc_pair = pair_symbol.endswith('-OTC') if isinstance(pair_symbol, str) else False
        
        # 1. الفحص المتقدم لنقاط الدعم والمقاومة في حالة توفر الشموع
        sr_validation_result = None
        if candles and len(candles) >= 20:
            try:
                # محاولة استيراد وحدة فحص نقاط الدعم والمقاومة
                sr_validator_module = importlib.import_module('sr_signal_validator')
                validate_sr_func = getattr(sr_validator_module, 'validate_signal_at_sr_levels', None)
                
                if validate_sr_func:
                    is_valid, sr_confidence, sr_reason = validate_sr_func(signal, candles)
                    sr_validation_result = {
                        'is_valid': is_valid,
                        'confidence': sr_confidence,
                        'reason': sr_reason
                    }
                    
                    logger.info(f"تحقق من نقاط الدعم والمقاومة: {is_valid}, ثقة: {sr_confidence}, سبب: {sr_reason}")
                    
                    # إذا كانت الإشارة غير صالحة بناءً على تحليل نقاط الدعم والمقاومة وبثقة عالية (>75)
                    # نرفض الإشارة فوراً
                    if not is_valid and sr_confidence > 75:
                        return False, sr_confidence, f"إشارة غير صالحة عند نقاط الدعم/المقاومة: {sr_reason}"
                
            except (ImportError, AttributeError) as e:
                logger.warning(f"لم يتم العثور على نظام تحقق نقاط الدعم والمقاومة: {e}")
        
        # 2. تقييم الإشارة بالمعايير القياسية
        quality_score, criteria_scores = self.evaluate_signal_quality(signal, candles, multi_timeframe_analysis)
        
        # تحديث درجة التحقق من مناطق الدعم والمقاومة إذا كانت متوفرة من التحليل المتقدم
        if sr_validation_result:
            if sr_validation_result['is_valid']:
                # رفع درجة التحقق من الدعم والمقاومة إذا كان التحليل المتقدم إيجابيًا
                criteria_scores['sr_validation'] = max(criteria_scores['sr_validation'], sr_validation_result['confidence'])
            else:
                # خفض درجة التحقق إذا كان التحليل المتقدم سلبيًا
                criteria_scores['sr_validation'] = min(criteria_scores['sr_validation'], 100 - sr_validation_result['confidence'])
            
            # إعادة حساب درجة الجودة الإجمالية بعد تحديث درجة التحقق
            weighted_sum = sum(criteria_scores[criterion] * self.weights[criterion] for criterion in self.weights if criterion in criteria_scores)
            quality_score = weighted_sum
        
        # تقديم تفاصيل التقييم في السجلات
        logger.info(f"تقييم جودة الإشارة للزوج {signal.get('pair', 'غير معروف')}: {quality_score:.2f}/100")
        for criterion, score in criteria_scores.items():
            logger.info(f"  - {criterion}: {score:.2f}/100")
        
        # التحقق ما إذا كان الزوج من أزواج OTC
        pair_symbol = signal.get('pair', '')
        is_otc_pair = "-OTC" in pair_symbol

        # تعديل حد الجودة المطلوب للأزواج OTC (تخفيض بنسبة 10% للسماح بمزيد من إشارات OTC)
        min_quality_required = self.min_quality_score * 0.9 if is_otc_pair else self.min_quality_score
        
        # تسجيل سجل عن الحد المستخدم
        logger.debug(f"الحد المطلوب للجودة: {min_quality_required} (OTC: {is_otc_pair})")
        
        # التحقق من الحد الأدنى لدرجة الجودة
        if quality_score >= min_quality_required:
            if is_otc_pair:
                reason = f"الإشارة مقبولة (زوج OTC) بدرجة جودة {quality_score:.2f}/{min_quality_required:.2f}"
                logger.info(f"🚀 تمت الموافقة على إشارة OTC خاصة: {pair_symbol} بدرجة: {quality_score:.2f}")
            else:
                reason = f"الإشارة مقبولة بدرجة جودة {quality_score:.2f}/{min_quality_required:.2f}"
            
            # إضافة معلومات تحليل نقاط الدعم والمقاومة إذا كانت متوفرة
            if sr_validation_result and sr_validation_result['is_valid']:
                reason += f" | {sr_validation_result['reason']}"
                
            return True, quality_score, reason
        else:
            # تحديد المعايير التي تسببت في انخفاض درجة الجودة
            threshold = 45 if is_otc_pair else 50  # عتبة أقل للمعايير المنخفضة لأزواج OTC
            low_criteria = [k for k, v in criteria_scores.items() if v < threshold]
            reason = f"تم رفض الإشارة (درجة الجودة {quality_score:.2f}/{min_quality_required:.2f}). المعايير المنخفضة: {', '.join(low_criteria)}"
            
            # إضافة معلومات تحليل نقاط الدعم والمقاومة إذا كانت متوفرة وسلبية
            if sr_validation_result and not sr_validation_result['is_valid']:
                reason += f" | {sr_validation_result['reason']}"
                
            return False, quality_score, reason
    
    def evaluate_signal_quality(self, signal, candles=None, multi_timeframe_analysis=None):
        """
        تقييم جودة الإشارة بناءً على معايير متعددة
        
        Args:
            signal (dict): معلومات الإشارة
            candles (list, optional): بيانات الشموع للتحليل الإضافي
            multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
            
        Returns:
            tuple: (درجة الجودة الإجمالية, قاموس بدرجات كل معيار)
        """
        # التحقق ما إذا كان الزوج من أزواج OTC للاستخدام في تخصيص التحليل
        pair_symbol = signal.get('pair', '')
        is_otc_pair = "-OTC" in pair_symbol
        
        # استخدام استراتيجية OTC المتخصصة إذا كان الزوج من أزواج OTC
        if is_otc_pair:
            try:
                # محاولة استيراد وحدة استراتيجية OTC المتخصصة
                otc_strategy = __import__('otc_analyzer_strategy')
                logger.debug(f"تم استيراد استراتيجية OTC المتخصصة لتحليل الزوج {pair_symbol}")
            except ImportError:
                # في حالة عدم توفر وحدة استراتيجية OTC، نستخدم التحليل القياسي
                logger.warning(f"لم يتم العثور على وحدة استراتيجية OTC المتخصصة، سيتم استخدام التحليل القياسي")
                otc_strategy = None
        else:
            otc_strategy = None
            
        # تهيئة درجات المعايير
        criteria_scores = {
            'probability': 0,
            'sr_validation': 0,
            'pattern_strength': 0,
            'timeframe_alignment': 0,
            'risk_reward': 0,
            'market_volatility': 0,
            'consecutive_pattern': 0,
            'divergence': 0
        }
        
        # 1. تقييم احتمالية النجاح
        probability_str = signal.get('probability', '0')
        # تحويل النسبة المئوية إلى رقم (إزالة % إذا وجدت)
        probability = float(probability_str.replace('%', '')) if isinstance(probability_str, str) else float(probability_str)
        # نعالج التحويل بشكل صحيح لتجنب أخطاء النوع
        max_score = 100.0  # قيمة عائمة
        scaled_probability = probability * 100.0 / 95.0  # حساب كقيمة عائمة
        criteria_scores['probability'] = min(max_score, scaled_probability)  # نحول إلى درجة من 100
        
        # 2. تقييم التحقق من مناطق الدعم والمقاومة
        sr_validated = signal.get('sr_validated', False)
        if sr_validated:
            criteria_scores['sr_validation'] = 100
        elif 'sr_info' in signal:
            # إذا كانت هناك معلومات عن الدعم والمقاومة ولكن لم يتم التحقق منها بالكامل
            criteria_scores['sr_validation'] = 50
        else:
            criteria_scores['sr_validation'] = 0
        
        # 3. تقييم قوة نمط الشموع
        if candles and len(candles) >= 3:
            try:
                from candlestick_pattern_analyzer import analyze_candlestick_patterns
                pattern_result = analyze_candlestick_patterns(candles)
                pattern_strength = pattern_result.get('strength', 0)
                pattern_direction = pattern_result.get('direction', 'NEUTRAL')
                
                # التحقق من توافق الاتجاه
                if pattern_direction == signal.get('direction', ''):
                    # إذا كان اتجاه النمط يتوافق مع إشارة التداول
                    criteria_scores['pattern_strength'] = pattern_strength
                elif pattern_direction == 'NEUTRAL':
                    # إذا كان النمط محايدًا، نعطي درجة متوسطة
                    criteria_scores['pattern_strength'] = 50
                else:
                    # إذا كان النمط يتعارض مع الإشارة، نعطي درجة منخفضة
                    criteria_scores['pattern_strength'] = max(0, pattern_strength * 0.3)
            except Exception as e:
                logger.warning(f"خطأ في تحليل أنماط الشموع: {e}")
                criteria_scores['pattern_strength'] = 50  # قيمة افتراضية في حالة الخطأ
        else:
            criteria_scores['pattern_strength'] = 50  # قيمة افتراضية إذا لم تتوفر بيانات الشموع
        
        # 4. تقييم توافق الإطارات الزمنية - خوارزمية متقدمة جديدة مخصصة للأزواج OTC
        if multi_timeframe_analysis:
            try:
                # التحقق ما إذا كان الزوج من أزواج OTC للاستخدام في تخصيص التحليل
                pair_symbol = signal.get('pair', '')
                is_otc_pair = "-OTC" in pair_symbol
                
                # الحصول على اتجاهات الإطارات المختلفة
                m1_direction = multi_timeframe_analysis.get('timeframes', {}).get('M1', {}).get('direction', 'NEUTRAL')
                m5_direction = multi_timeframe_analysis.get('timeframes', {}).get('M5', {}).get('direction', 'NEUTRAL')
                m15_direction = multi_timeframe_analysis.get('timeframes', {}).get('M15', {}).get('direction', 'NEUTRAL')
                
                signal_direction = signal.get('direction', '')
                
                # اختيار مجموعة الأوزان المناسبة حسب نوع الزوج
                weights = self.timeframe_weights['otc'] if is_otc_pair else self.timeframe_weights['default']
                
                # حساب درجة التوافق المرجحة (0-100) - خوارزمية جديدة
                alignment_score = 0.0
                
                # حساب التوافق للإطار M1
                if m1_direction == signal_direction:
                    alignment_score += 100.0 * weights['M1']
                elif m1_direction == 'NEUTRAL':
                    alignment_score += 50.0 * weights['M1']
                # في حالة التعارض لا نضيف أي درجات
                
                # حساب التوافق للإطار M5
                if m5_direction == signal_direction:
                    alignment_score += 100.0 * weights['M5']
                elif m5_direction == 'NEUTRAL':
                    alignment_score += 50.0 * weights['M5']
                # في حالة التعارض لا نضيف أي درجات
                
                # حساب التوافق للإطار M15
                if m15_direction == signal_direction:
                    alignment_score += 100.0 * weights['M15']
                elif m15_direction == 'NEUTRAL':
                    alignment_score += 50.0 * weights['M15']
                # في حالة التعارض لا نضيف أي درجات
                
                # تسجيل معلومات إضافية للأزواج OTC
                if is_otc_pair:
                    logger.debug(f"تحليل توافق إطارات OTC: M1={m1_direction}, M5={m5_direction}, M15={m15_direction}, الاتجاه={signal_direction}")
                    logger.debug(f"الأوزان المستخدمة: M1={weights['M1']}, M5={weights['M5']}, M15={weights['M15']}, النتيجة={alignment_score}")
                
                # تحديد نتيجة التوافق النهائية
                criteria_scores['timeframe_alignment'] = alignment_score
                
                # تعزيز الإشارات التي يكون فيها اتجاه M1 متوافقًا مع الإشارة لأزواج OTC
                if is_otc_pair and m1_direction == signal_direction:
                    # منح مكافأة إضافية للزوج OTC عندما يكون إطار M1 متوافقًا تمامًا مع الإشارة
                    otc_m1_bonus = 10.0  # مكافأة إضافية للتوافق في الإطار M1
                    criteria_scores['timeframe_alignment'] = min(100.0, criteria_scores['timeframe_alignment'] + otc_m1_bonus)
                    logger.debug(f"تم منح مكافأة إضافية ({otc_m1_bonus}) لتوافق الإطار M1 في زوج OTC")
                
                # تطبيق خوارزمية مخصصة إضافية للأزواج OTC
                if is_otc_pair:
                    # استراتيجية خاصة: الأزواج OTC أكثر استقرارًا عندما يكون هناك توافق بين M1 و M5 فقط
                    if m1_direction == m5_direction and m1_direction == signal_direction:
                        # عندما يكون هناك توافق بين M1 و M5 فقط، نعطي وزنًا إضافيًا
                        criteria_scores['timeframe_alignment'] = min(100.0, criteria_scores['timeframe_alignment'] * 1.2)
                        logger.debug(f"تم تطبيق استراتيجية التوافق الخاصة بين M1 و M5 للزوج OTC")
                    
                    # تخفيض تأثير M15 على النتيجة النهائية لأزواج OTC
                    if m15_direction != signal_direction and m15_direction != 'NEUTRAL':
                        # نقلل من تأثير التعارض في M15 للأزواج OTC
                        criteria_scores['timeframe_alignment'] = min(100.0, criteria_scores['timeframe_alignment'] * 0.9 + 10.0)
                        logger.debug(f"تم تخفيف تأثير تعارض الإطار M15 للزوج OTC")
            except Exception as e:
                logger.warning(f"خطأ في تقييم توافق الإطارات الزمنية: {e}")
                criteria_scores['timeframe_alignment'] = 50  # قيمة افتراضية في حالة الخطأ
        else:
            criteria_scores['timeframe_alignment'] = 50  # قيمة افتراضية إذا لم تتوفر بيانات الإطارات المتعددة
        
        # 5. تقييم نسبة المخاطرة/العائد
        if 'risk_reward_ratio' in signal:
            risk_reward = signal.get('risk_reward_ratio', 0)
            criteria_scores['risk_reward'] = min(100.0, (risk_reward / self.risk_reward_threshold) * 100.0)
        else:
            # إذا لم تتوفر نسبة المخاطرة/العائد، نحاول حسابها من خلال المعلومات المتاحة
            if candles and len(candles) > 0 and multi_timeframe_analysis:
                try:
                    # التقدير التقريبي للمخاطرة/العائد بناءً على مناطق الدعم والمقاومة
                    current_price = candles[-1]['close']
                    sr_zones = multi_timeframe_analysis.get('support_resistance', {})
                    
                    direction = signal.get('direction', '')
                    take_profit = 0
                    stop_loss = 0
                    
                    if direction == 'BUY':
                        # للشراء، البحث عن أقرب مقاومة ودعم
                        resistance_levels = sr_zones.get('resistance', [])
                        support_levels = sr_zones.get('support', [])
                        
                        if resistance_levels and support_levels:
                            # إيجاد أقرب مقاومة فوق السعر الحالي بطريقة آمنة
                            resistance_above = [r for r in resistance_levels if r['price'] > current_price]
                            next_resistance = min(resistance_above, key=lambda x: x['price'] - current_price) if resistance_above else None
                            
                            # إيجاد أقرب دعم تحت السعر الحالي بطريقة آمنة
                            support_below = [s for s in support_levels if s['price'] < current_price]
                            next_support = max(support_below, key=lambda x: current_price - x['price']) if support_below else None
                            
                            if next_resistance and next_support:
                                take_profit = next_resistance['price'] - current_price
                                stop_loss = current_price - next_support['price']
                                
                                if stop_loss > 0:
                                    risk_reward = take_profit / stop_loss
                                    criteria_scores['risk_reward'] = min(100.0, (risk_reward / self.risk_reward_threshold) * 100.0)
                    
                    elif direction == 'SELL':
                        # للبيع، البحث عن أقرب دعم ومقاومة
                        resistance_levels = sr_zones.get('resistance', [])
                        support_levels = sr_zones.get('support', [])
                        
                        if resistance_levels and support_levels:
                            # إيجاد أقرب مقاومة فوق السعر الحالي بطريقة آمنة
                            resistance_above = [r for r in resistance_levels if r['price'] > current_price]
                            next_resistance = min(resistance_above, key=lambda x: x['price'] - current_price) if resistance_above else None
                            
                            # إيجاد أقرب دعم تحت السعر الحالي بطريقة آمنة
                            support_below = [s for s in support_levels if s['price'] < current_price]
                            next_support = max(support_below, key=lambda x: current_price - x['price']) if support_below else None
                            
                            if next_resistance and next_support:
                                take_profit = current_price - next_support['price']
                                stop_loss = next_resistance['price'] - current_price
                                
                                if stop_loss > 0:
                                    risk_reward = take_profit / stop_loss
                                    criteria_scores['risk_reward'] = min(100.0, (risk_reward / self.risk_reward_threshold) * 100.0)
                
                except Exception as e:
                    logger.warning(f"خطأ في حساب نسبة المخاطرة/العائد: {e}")
                    criteria_scores['risk_reward'] = 50.0  # قيمة افتراضية في حالة الخطأ
            else:
                criteria_scores['risk_reward'] = 50.0  # قيمة افتراضية
        
        # 6. تقييم تقلب السوق وجودة الوقت
        signal_time = None
        if 'entry_time' in signal:
            try:
                entry_time_str = signal.get('entry_time', '')
                # تحويل الوقت إلى كائن time
                if ':' in entry_time_str:
                    hour, minute = map(int, entry_time_str.split(':'))
                    signal_time = time(hour, minute)
            except Exception as e:
                logger.warning(f"خطأ في تحليل وقت الإشارة: {e}")
        
        if signal_time:
            # التحقق مما إذا كان الوقت ضمن الأوقات عالية الجودة
            in_high_quality = any(start <= signal_time <= end for start, end in self.high_quality_hours)
            # التحقق مما إذا كان الوقت ضمن الأوقات منخفضة الجودة
            in_low_quality = any(start <= signal_time <= end for start, end in self.low_quality_hours)
            
            # تعديل خاص لأزواج OTC - تحسين درجة جودة الوقت
            pair_symbol = signal.get('pair', '')
            is_otc_pair = "-OTC" in pair_symbol
            
            if in_high_quality:
                criteria_scores['market_volatility'] = 90.0  # وقت جيد للتداول
            elif in_low_quality:
                # إذا كان زوج OTC نحسن قليلاً من درجة الوقت المنخفض
                criteria_scores['market_volatility'] = 50.0 if is_otc_pair else 30.0  # وقت سيء للتداول
            else:
                # إذا كان زوج OTC نحسن قليلاً من درجة الوقت المتوسط
                criteria_scores['market_volatility'] = 75.0 if is_otc_pair else 60.0  # وقت متوسط الجودة
        else:
            # إذا لم نتمكن من تحليل الوقت، نستخدم قيمة افتراضية متوسطة
            criteria_scores['market_volatility'] = 60.0
        
        # تقييم إضافي بناءً على موثوقية الزوج
        pair_symbol = signal.get('pair', '')
        if any(reliable_pair in pair_symbol for reliable_pair in self.high_reliability_pairs):
            # زيادة درجة احتمالية النجاح للأزواج الموثوقة
            criteria_scores['probability'] = min(100.0, criteria_scores['probability'] * 1.15)
        
        # بونص خاص لأزواج OTC
        if '-OTC' in pair_symbol:
            # تعزيز درجة الجودة للأزواج OTC بقيمة ثابتة
            OTC_BONUS_SCORE = 15.0  # بونص ثابت للإشارات OTC
            # تعزيز الجودة الإجمالية وليس معيار معين
            for key in criteria_scores:
                criteria_scores[key] = min(100.0, criteria_scores[key] + OTC_BONUS_SCORE / len(criteria_scores))
        
        # حساب درجة الجودة الإجمالية (حاصل ضرب كل معيار بوزنه)
        weighted_sum = sum(criteria_scores[criterion] * self.weights[criterion] for criterion in self.weights)
        
        return weighted_sum, criteria_scores
    
    def set_min_quality_score(self, score):
        """تعيين الحد الأدنى لدرجة جودة الإشارة"""
        self.min_quality_score = score
    
    def set_min_probability(self, probability):
        """تعيين الحد الأدنى لاحتمالية النجاح"""
        self.min_probability = probability
    
    def set_min_pattern_strength(self, strength):
        """تعيين الحد الأدنى لقوة نمط الشموع"""
        self.min_pattern_strength = strength
    
    def set_risk_reward_threshold(self, ratio):
        """تعيين الحد الأدنى لنسبة المخاطرة/العائد"""
        self.risk_reward_threshold = ratio
    
    def get_filter_statistics(self):
        """
        الحصول على إحصائيات وإعدادات المرشح
        
        Returns:
            dict: إحصائيات وإعدادات المرشح
        """
        return {
            'min_quality_score': self.min_quality_score,
            'min_probability': self.min_probability,
            'min_pattern_strength': self.min_pattern_strength,
            'risk_reward_threshold': self.risk_reward_threshold,
            'min_sr_validation_score': self.min_sr_validation_score,
            'weights': self.weights,
            'high_reliability_pairs': self.high_reliability_pairs
        }

# إنشاء كائن واحد فقط للاستخدام من قبل الوحدات الأخرى
_signal_filter = AdvancedSignalFilter()

def filter_trading_signal(signal, candles=None, multi_timeframe_analysis=None):
    """
    تصفية إشارة التداول بناءً على المعايير المتقدمة
    
    Args:
        signal (dict): معلومات الإشارة المراد تصفيتها
        candles (list, optional): بيانات الشموع للتحليل الإضافي
        multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
        
    Returns:
        tuple: (قبول الإشارة, درجة الجودة, سبب القبول أو الرفض)
    """
    return _signal_filter.filter_signal(signal, candles, multi_timeframe_analysis)

def evaluate_signal_quality(signal, candles=None, multi_timeframe_analysis=None):
    """
    تقييم جودة إشارة التداول
    
    Args:
        signal (dict): معلومات الإشارة المراد تقييمها
        candles (list, optional): بيانات الشموع للتحليل الإضافي
        multi_timeframe_analysis (dict, optional): نتائج تحليل الإطارات الزمنية المتعددة
        
    Returns:
        tuple: (درجة الجودة الإجمالية, قاموس بدرجات كل معيار)
    """
    return _signal_filter.evaluate_signal_quality(signal, candles, multi_timeframe_analysis)

def get_filter_settings():
    """
    الحصول على إعدادات المرشح الحالية
    
    Returns:
        dict: إعدادات المرشح
    """
    return _signal_filter.get_filter_statistics()

def configure_filter(min_quality=None, min_probability=None, min_pattern_strength=None, risk_reward=None):
    """
    تكوين إعدادات المرشح
    
    Args:
        min_quality (int, optional): الحد الأدنى لدرجة الجودة (0-100)
        min_probability (int, optional): الحد الأدنى للاحتمالية (%)
        min_pattern_strength (int, optional): الحد الأدنى لقوة نمط الشموع (%)
        risk_reward (float, optional): الحد الأدنى لنسبة المخاطرة/العائد
    """
    if min_quality is not None:
        _signal_filter.set_min_quality_score(min_quality)
    
    if min_probability is not None:
        _signal_filter.set_min_probability(min_probability)
    
    if min_pattern_strength is not None:
        _signal_filter.set_min_pattern_strength(min_pattern_strength)
    
    if risk_reward is not None:
        _signal_filter.set_risk_reward_threshold(risk_reward)