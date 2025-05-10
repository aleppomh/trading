"""
وحدة تصفية الإشارات لضمان إرسال الإشارات ذات الجودة العالية فقط
هذه الوحدة تستخدم مجموعة من المرشحات المتقدمة لتقييم قوة الإشارات قبل إرسالها
"""
import logging
import math
import random
from datetime import datetime, timedelta

from technical_analyzer import TechnicalAnalyzer
from multi_timeframe_analyzer import get_multi_timeframe_signal
from pocket_option_otc_pairs import get_all_valid_pairs as get_all_valid_otc_pairs
from pocket_option_otc_pairs import get_pairs_with_good_payout as get_otc_pairs_with_good_payout
from pocket_option_otc_pairs import is_valid_pair as is_valid_otc_pair
from market_pairs import get_all_valid_pairs as get_all_valid_market_pairs
from market_pairs import get_pairs_with_good_payout as get_market_pairs_with_good_payout
from market_pairs import get_tradable_pairs as get_tradable_market_pairs
from market_pairs import get_tradable_pairs_with_good_payout as get_tradable_market_pairs_with_good_payout
from market_pairs import is_pair_tradable_now

# إعداد سجل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مرشحات متقدمة لتصفية الإشارات
class SignalFilter:
    """مصفي متقدم للإشارات"""
    
    def __init__(self):
        """تهيئة مصفي الإشارات"""
        self.technical_analyzer = TechnicalAnalyzer()
        
        # تعيين عتبات الثقة لكل نوع من الإشارات
        self.confidence_thresholds = {
            'standard': 85,  # الإشارات العادية
            'mtf': 88,       # إشارات متعددة الأطر الزمنية
            'critical': 90   # الإشارات الحاسمة (مثل قبل الأخبار الاقتصادية)
        }
        
        # سجل الإشارات السابقة (لتجنب التكرار)
        self.recent_signals = []
        self.max_recent_signals = 10
        
        # عداد رفض الإشارات (للتشخيص)
        self.rejected_signals = {
            'low_confidence': 0,
            'recent_pair': 0,
            'market_conditions': 0,
            'inconsistent': 0,
            'other': 0
        }
    
    def filter_signal(self, signal, signal_type='standard'):
        """
        تصفية الإشارة بناءً على المعايير المتقدمة
        
        Args:
            signal (dict): معلومات الإشارة المقترحة
            signal_type (str): نوع الإشارة (standard, mtf, critical)
            
        Returns:
            bool: True إذا اجتازت الإشارة التصفية، False إذا تم رفضها
        """
        if not signal:
            return False
        
        # فحص إذا كانت الإشارة تحتوي على الحقول المطلوبة
        required_fields = ['direction', 'probability', 'duration', 'pair']
        if not all(field in signal for field in required_fields):
            logger.warning("Signal missing required fields")
            self.rejected_signals['other'] = self.rejected_signals.get('other', 0) + 1
            return False
            
        pair = signal['pair']
        direction = signal['direction']
        probability = signal['probability']
        
        # تسجيل معلومات الإشارة المقترحة
        logger.info(f"Filtering signal: {pair} {direction} (probability: {probability}%)")
        
        # الفحص 0: التحقق من نسبة ربح الزوج (يجب أن تكون 80% أو أعلى)
        try:
            # تحديد نوع الزوج (عادي أو OTC) للتحقق من معدل العائد بشكل صحيح
            try:
                from market_pairs import get_all_valid_pairs as get_all_valid_market_pairs
                is_market_pair = any(pair == mp for mp in get_all_valid_market_pairs())
                
                # إضافة معلومات نوع الزوج إلى الإشارة
                signal['pair_type'] = 'market' if is_market_pair else 'otc'
            except Exception as e:
                logger.warning(f"Error checking market pairs: {e}")
                is_market_pair = False
                signal['pair_type'] = 'otc'  # القيمة الافتراضية
            
            if is_market_pair:
                # هذا زوج بورصة عادي
                from market_pairs import is_good_payout_pair, get_pair_payout_rate
                payout_check_func = is_good_payout_pair
                payout_rate_func = get_pair_payout_rate
            else:
                # هذا زوج OTC
                from pocket_option_otc_pairs import is_good_payout_pair, get_pair_payout_rate
                payout_check_func = is_good_payout_pair
                payout_rate_func = get_pair_payout_rate
            
            # التحقق من نسبة العائد باستخدام الدالة المناسبة
            if not payout_check_func(pair):
                payout_rate = payout_rate_func(pair)
                logger.info(f"Signal rejected: payout rate too low for {pair} ({payout_rate}% < 80%)")
                self.rejected_signals['low_payout'] = self.rejected_signals.get('low_payout', 0) + 1
                return False
            else:
                payout_rate = payout_rate_func(pair)
                logger.info(f"Pair {pair} has acceptable payout rate: {payout_rate}%")
                # تعديل نسبة الربح في الإشارة
                signal['payout_rate'] = payout_rate
        except Exception as e:
            logger.warning(f"Error checking payout rate: {e}")
        
        # الفحص 1: عتبة الثقة الدنيا حسب نوع الإشارة
        confidence_threshold = self.confidence_thresholds.get(signal_type, 85)
        if probability < confidence_threshold:
            logger.info(f"Signal rejected: confidence {probability}% below threshold {confidence_threshold}%")
            self.rejected_signals['low_confidence'] = self.rejected_signals.get('low_confidence', 0) + 1
            return False
        
        # الفحص 2: تجنب تكرار نفس الزوج في وقت قصير
        for recent in self.recent_signals:
            if recent['pair'] == pair:
                time_diff = (datetime.now() - recent['timestamp']).total_seconds() / 60
                if time_diff < 30:  # 30 دقيقة
                    logger.info(f"Signal rejected: same pair {pair} was used recently ({time_diff:.1f} min ago)")
                    self.rejected_signals['recent_pair'] = self.rejected_signals.get('recent_pair', 0) + 1
                    return False
        
        # الفحص 3: فحص ظروف السوق الحالية (التذبذب، حجم التداول، إلخ)
        if not self._check_market_conditions(signal):
            logger.info(f"Signal rejected: unfavorable market conditions for {pair}")
            self.rejected_signals['market_conditions'] = self.rejected_signals.get('market_conditions', 0) + 1
            return False
        
        # الفحص 4: التحقق من اتساق الإشارة (للإشارات متعددة الأطر الزمنية)
        if signal_type == 'mtf' and not self._check_signal_consistency(signal):
            logger.info(f"Signal rejected: inconsistent signal for {pair}")
            self.rejected_signals['inconsistent'] = self.rejected_signals.get('inconsistent', 0) + 1
            return False
            
        # الفحص 5: التحقق من عدم وجود إشارة عكسية عند مستويات الدعم والمقاومة
        if not self._check_support_resistance_validity(signal):
            logger.info(f"Signal rejected: invalid signal at support/resistance level for {pair}")
            self.rejected_signals['invalid_sr_signal'] = self.rejected_signals.get('invalid_sr_signal', 0) + 1
            return False
        
        # تحديث سجل الإشارات الأخيرة
        self._update_recent_signals(signal)
        
        logger.info(f"Signal accepted: {signal['direction']} {signal['pair']} with {signal['probability']}% confidence")
        return True
    
    def _check_market_conditions(self, signal):
        """
        التحقق من ظروف السوق المناسبة للإشارة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            bool: True إذا كانت ظروف السوق مناسبة، False إذا كانت غير مناسبة
        """
        pair = signal['pair']
        
        # الحصول على بيانات السوق الحالية
        market_data = self.technical_analyzer.price_data.get(pair, {})
        if not market_data or 'candles' not in market_data or len(market_data['candles']) < 20:
            # لا توجد بيانات كافية للتقييم
            return True
        
        candles = market_data['candles']
        
        # حساب مؤشر التذبذب (Volatility)
        volatility = self._calculate_volatility(candles)
        
        # تحليل العلاقة بين التذبذب واتجاه الإشارة
        if volatility > 2.0:  # تذبذب عالٍ جداً
            logger.info(f"  - High volatility detected ({volatility:.2f}%), requiring higher confidence")
            # في حالة التذبذب العالي، نطلب ثقة أعلى
            return signal['probability'] >= 92
        elif volatility < 0.2:  # تذبذب منخفض جداً
            logger.info(f"  - Very low volatility detected ({volatility:.2f}%), signals may not perform well")
            # في حالة التذبذب المنخفض جداً، قد تكون الإشارات أقل فعالية
            return signal['probability'] >= 90
        
        # ظروف السوق طبيعية
        return True
    
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
    
    def _check_support_resistance_validity_indicators(self, signal):
        """
        التحقق من صحة الإشارة بالنسبة لمستويات الدعم والمقاومة (باستخدام المؤشرات)
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            bool: True إذا كانت الإشارة صحيحة، False إذا كانت إشارة عكسية عند مستوى دعم/مقاومة
        """
        # عدم وجود معلومات المؤشرات يعني عدم القدرة على التحقق
        if 'indicators' not in signal:
            return True
            
        indicators = signal['indicators']
        
        # التحقق من وجود معلومات الدعم والمقاومة
        if 'near_support_resistance' not in indicators:
            return True
            
        near_sr = indicators['near_support_resistance']
        if not near_sr:
            # لا يوجد مستوى دعم أو مقاومة قريب
            return True
            
        direction = signal['direction']
        sr_type = near_sr['type']
        
        # الحالات التي نرفضها:
        # 1. إشارة بيع عند مستوى دعم (إلا في حالة كسر الدعم بقوة)
        if sr_type == 'support' and direction == 'SELL':
            # شدة رفض الإشارة العكسية عند الدعم أعلى - لتجنب الإشارات الخاسرة
            # التحقق من وجود كسر قوي للدعم
            if near_sr.get('breakout_strength', 0) > 85:
                logger.info(f"  - Very strong support breakdown detected, allowing SELL signal")
                return True
            
            # فحص تأكيدات إضافية بشروط أكثر صرامة
            adx = indicators.get('adx', 0)
            rsi = indicators.get('rsi', 50)
            stoch_k = indicators.get('stoch_k', 50)
            stoch_d = indicators.get('stoch_d', 50)
            macd = indicators.get('macd', 0)
            
            # نطلب أكثر من مؤشر للتأكيد لتجنب الإشارات الخاطئة
            bearish_confirmations = 0
            
            # مؤشر قوة الاتجاه
            if adx > 35:
                bearish_confirmations += 1
                logger.info(f"  - Strong trend confirmation with ADX {adx}")
                
            # مؤشر القوة النسبية
            if rsi < 35 and rsi > 15:  # قوي ولكن ليس متشبعاً بالبيع
                bearish_confirmations += 1
                logger.info(f"  - Bearish RSI confirmation: {rsi}")
                
            # مؤشر الاستوكاستك
            if stoch_k < stoch_d and stoch_k > 20:  # تقاطع هبوطي وليس متشبعاً
                bearish_confirmations += 1
                logger.info(f"  - Bearish Stochastic crossover: K={stoch_k}, D={stoch_d}")
                
            # مؤشر الماكد
            if macd < 0:
                bearish_confirmations += 1
                logger.info(f"  - Negative MACD confirms bearish trend: {macd}")
                
            # نطلب على الأقل 3 تأكيدات من أصل 4 لقبول الإشارة عند الدعم
            if bearish_confirmations >= 3:
                logger.info(f"  - Multiple strong bearish confirmations ({bearish_confirmations}/4) allow SELL signal at support level")
                return True
                
            logger.info(f"  - Rejecting SELL signal at support level - insufficient confirmations ({bearish_confirmations}/4)")
            return False
            
        # 2. إشارة شراء عند مستوى مقاومة (إلا في حالة اختراق المقاومة بقوة)
        elif sr_type == 'resistance' and direction == 'BUY':
            # شدة رفض الإشارة العكسية عند المقاومة أعلى - لتجنب الإشارات الخاسرة
            # التحقق من وجود اختراق قوي للمقاومة
            if near_sr.get('breakout_strength', 0) > 85:
                logger.info(f"  - Very strong resistance breakout detected, allowing BUY signal")
                return True
                
            # فحص تأكيدات إضافية بشروط أكثر صرامة
            adx = indicators.get('adx', 0)
            rsi = indicators.get('rsi', 50)
            stoch_k = indicators.get('stoch_k', 50)
            stoch_d = indicators.get('stoch_d', 50)
            macd = indicators.get('macd', 0)
            
            # نطلب أكثر من مؤشر للتأكيد لتجنب الإشارات الخاطئة
            bullish_confirmations = 0
            
            # مؤشر قوة الاتجاه
            if adx > 35:
                bullish_confirmations += 1
                logger.info(f"  - Strong trend confirmation with ADX {adx}")
                
            # مؤشر القوة النسبية
            if rsi > 65 and rsi < 85:  # قوي ولكن ليس متشبعاً بالشراء
                bullish_confirmations += 1
                logger.info(f"  - Bullish RSI confirmation: {rsi}")
                
            # مؤشر الاستوكاستك
            if stoch_k > stoch_d and stoch_k < 80:  # تقاطع صعودي وليس متشبعاً
                bullish_confirmations += 1
                logger.info(f"  - Bullish Stochastic crossover: K={stoch_k}, D={stoch_d}")
                
            # مؤشر الماكد
            if macd > 0:
                bullish_confirmations += 1
                logger.info(f"  - Positive MACD confirms bullish trend: {macd}")
                
            # نطلب على الأقل 3 تأكيدات من أصل 4 لقبول الإشارة عند المقاومة
            if bullish_confirmations >= 3:
                logger.info(f"  - Multiple strong bullish confirmations ({bullish_confirmations}/4) allow BUY signal at resistance level")
                return True
                
            logger.info(f"  - Rejecting BUY signal at resistance level - insufficient confirmations ({bullish_confirmations}/4)")
            return False
            
        # الحالات الأخرى (شراء عند دعم أو بيع عند مقاومة) مسموح بها
        return True

    def _check_support_resistance_validity(self, signal):
        """
        التحقق من صحة الإشارة بالنسبة لمستويات الدعم والمقاومة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            bool: True إذا كانت الإشارة صحيحة، False إذا كانت إشارة عكسية عند مستوى دعم/مقاومة
        """
        # 1. تحقق من وجود معلومات التحليل الفني
        if 'technical_analysis' not in signal or not signal['technical_analysis']:
            return True
            
        analysis = signal['technical_analysis']
        direction = signal['direction']
        
        # 2. البحث عن معلومات مستويات الدعم والمقاومة
        support_resistance_info = None
        
        for item in analysis:
            if 'support_resistance' in item or 'مستويات الدعم والمقاومة' in item:
                support_resistance_info = item
                break
                
        if not support_resistance_info:
            return True
            
        # 3. التحليل بناءً على الاتجاه ومستويات الدعم والمقاومة
        sr_text = str(support_resistance_info).lower()
        
        # 4. رفض إشارات البيع عند مستويات الدعم إلا مع وجود تأكيد قوي
        if direction == 'SELL' and ('support' in sr_text or 'دعم' in sr_text or 'الدعم' in sr_text):
            # تحقق من وجود "كسر" أو "اختراق" للدعم
            if 'break' in sr_text or 'اختراق' in sr_text or 'كسر' in sr_text:
                logger.info(f"  - SELL signal at support level is valid due to support breakdown")
                return True
                
            # تحقق من وجود مؤشرات إضافية تؤكد الاتجاه
            indicators_confirmation = False
            
            if 'indicators' in signal:
                indicators = signal['indicators']
                
                # التحقق من وجود مؤشرات تدعم اتجاه البيع
                if (indicators.get('rsi', 50) < 30 or 
                    indicators.get('adx', 0) > 25 and indicators.get('trend_strength', 0) > 70):
                    indicators_confirmation = True
                    
            if indicators_confirmation:
                logger.info(f"  - SELL signal at support level is valid due to strong bearish confirmation")
                return True
                
            logger.info(f"  - Rejecting SELL signal at support level without confirmation")
            return False
            
        # 5. رفض إشارات الشراء عند مستويات المقاومة إلا مع وجود تأكيد قوي
        elif direction == 'BUY' and ('resistance' in sr_text or 'مقاومة' in sr_text or 'المقاومة' in sr_text):
            # تحقق من وجود "كسر" أو "اختراق" للمقاومة
            if 'break' in sr_text or 'اختراق' in sr_text or 'كسر' in sr_text:
                logger.info(f"  - BUY signal at resistance level is valid due to resistance breakout")
                return True
                
            # تحقق من وجود مؤشرات إضافية تؤكد الاتجاه
            indicators_confirmation = False
            
            if 'indicators' in signal:
                indicators = signal['indicators']
                
                # التحقق من وجود مؤشرات تدعم اتجاه الشراء
                if (indicators.get('rsi', 50) > 70 or 
                    indicators.get('adx', 0) > 25 and indicators.get('trend_strength', 0) > 70):
                    indicators_confirmation = True
                    
            if indicators_confirmation:
                logger.info(f"  - BUY signal at resistance level is valid due to strong bullish confirmation")
                return True
                
            logger.info(f"  - Rejecting BUY signal at resistance level without confirmation")
            return False
            
        # الحالات الأخرى (شراء عند دعم أو بيع عند مقاومة) مسموح بها
        return True
        
    def _check_signal_consistency(self, signal):
        """
        التحقق من اتساق الإشارة مع تحليلات أخرى
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            bool: True إذا كانت الإشارة متسقة، False إذا كانت متضاربة
        """
        # بالنسبة للإشارات المتعددة الأطر الزمنية، نفترض أنها بالفعل اجتازت فحص الاتساق
        if signal.get('multi_timeframe'):
            logger.info(f"  - Multi-timeframe signal is inherently consistent, no extra verification needed")
            return True
        
        # للإشارات العادية، نقارنها مع تحليل متعدد الأطر الزمنية وتحليل الإطار الزمني الأكبر
        pair_symbol = signal.get('pair')
        if not pair_symbol:
            logger.warning(f"  - Cannot check consistency: missing pair symbol in signal")
            return False
            
        mtf_signal = get_multi_timeframe_signal(pair_symbol=pair_symbol)
        
        # تحليل الاتساق مع تحليل الإطار الزمني الأكبر
        # استدعاء الدالة بإطار زمني أكبر من الإطار الزمني الحالي
        timeframes_consistency = True
        
        # استدعاء المحلل الفني للحصول على اتجاه الإطار الزمني الأكبر
        try:
            from technical_analyzer import TechnicalAnalyzer
            analyzer = TechnicalAnalyzer()
            
            # فحص الاتجاه على الإطار الزمني M5 (5 دقائق)
            m5_trend = analyzer.get_trend(pair_symbol, timeframe=5)
            # فحص الاتجاه على الإطار الزمني M15 (15 دقيقة)
            m15_trend = analyzer.get_trend(pair_symbol, timeframe=15)
            
            current_direction = signal['direction']
            
            # التحقق من اتساق الاتجاه على الأطر الزمنية المختلفة
            m5_consistent = (current_direction == 'BUY' and m5_trend in ['UP', 'STRONG_UP']) or \
                           (current_direction == 'SELL' and m5_trend in ['DOWN', 'STRONG_DOWN'])
                           
            m15_consistent = (current_direction == 'BUY' and m15_trend in ['UP', 'STRONG_UP']) or \
                            (current_direction == 'SELL' and m15_trend in ['DOWN', 'STRONG_DOWN'])
            
            timeframes_consistency = m5_consistent or m15_consistent
            
            logger.info(f"  - Signal direction: {current_direction}, M5 trend: {m5_trend}, M15 trend: {m15_trend}")
            
            if not timeframes_consistency:
                logger.warning(f"  - Signal conflicts with higher timeframes analysis")
                return False
                
            logger.info(f"  - Signal is consistent with at least one higher timeframe")
            
        except Exception as e:
            logger.warning(f"  - Error checking timeframes consistency: {e}")
            # في حالة حدوث خطأ، نعتبر الاتساق موجود
            timeframes_consistency = True
            
        # إذا لم نحصل على إشارة متعددة الأطر الزمنية، نعتمد على نتيجة فحص الأطر الزمنية المختلفة
        if not mtf_signal:
            return timeframes_consistency
        
        # مقارنة الاتجاهات
        mtf_consistency = signal['direction'] == mtf_signal['direction']
        
        # نحتاج لتحقق الاتساق مع كلا التحليلين: متعدد الأطر وتحليل الأطر الزمنية الأكبر
        if mtf_consistency:
            logger.info(f"  - Signal is consistent with multi-timeframe analysis")
        else:
            logger.warning(f"  - Signal conflicts with multi-timeframe analysis ({signal['direction']} vs {mtf_signal['direction']})")
        
        # على الأقل أحد نوعي التحقق يجب أن يكون متسقاً
        return mtf_consistency or timeframes_consistency
    
    def _update_recent_signals(self, signal):
        """
        تحديث سجل الإشارات الأخيرة
        
        Args:
            signal (dict): معلومات الإشارة
        """
        # إضافة طابع زمني للإشارة
        signal_record = {
            'pair': signal['pair'],
            'direction': signal['direction'],
            'timestamp': datetime.now()
        }
        
        # إضافة الإشارة إلى السجل
        self.recent_signals.append(signal_record)
        
        # الحفاظ على حجم السجل
        while len(self.recent_signals) > self.max_recent_signals:
            self.recent_signals.pop(0)
    
    def get_filtered_signal(self, override_pair=None):
        """
        الحصول على إشارة مصفاة عالية الجودة
        
        Args:
            override_pair (str, optional): رمز الزوج المراد تحليله، أو None لاختيار زوج عشوائي
            
        Returns:
            dict: معلومات الإشارة المصفاة، أو None في حالة عدم وجود إشارة جيدة
        """
        # محاولة الحصول على إشارة متعددة الأطر الزمنية أولاً (أعلى جودة)
        logger.info("Attempting to generate multi-timeframe signal...")
        mtf_signal = get_multi_timeframe_signal(pair_symbol=override_pair)
        
        if mtf_signal and self.filter_signal(mtf_signal, 'mtf'):
            logger.info("Generated high-quality multi-timeframe signal")
            return mtf_signal
        
        # إذا فشلت، نحاول الحصول على إشارة عادية
        logger.info("Multi-timeframe signal not available, falling back to standard signal...")
        standard_signal = self.technical_analyzer.get_signal(override_pair)
        
        if standard_signal and self.filter_signal(standard_signal, 'standard'):
            logger.info("Generated standard signal that passes quality filters")
            return standard_signal
        
        # في حالة عدم وجود إشارة جيدة
        logger.info("No signals pass quality filters at this time")
        return None
    
    def generate_safe_signal(self):
        """
        توليد إشارة آمنة بعد محاولات متعددة على أزواج مختلفة
        استخدام فقط الأزواج ذات نسبة الربح 80% أو أعلى
        يشمل أزواج البورصة العادية وأزواج OTC
        
        Returns:
            dict: معلومات الإشارة الآمنة، أو None في حالة عدم وجود إشارة جيدة
        """
        # مجموعة الأزواج التي سيتم استخدامها (من OTC والبورصة العادية)
        all_pairs = []
        
        # 1. أولاً، نضيف أزواج البورصة العادية المتاحة للتداول حالياً ذات نسبة الربح العالية
        tradable_market_pairs = get_tradable_market_pairs_with_good_payout()
        if tradable_market_pairs:
            logger.info(f"Found {len(tradable_market_pairs)} tradable market pairs with payout ≥ 80%")
            all_pairs.extend(tradable_market_pairs)
        else:
            logger.info("No tradable market pairs with good payout found at this time")
        
        # 2. ثم نضيف أزواج OTC ذات نسبة الربح العالية (متاحة 24/7)
        otc_pairs = get_otc_pairs_with_good_payout()
        if otc_pairs:
            logger.info(f"Found {len(otc_pairs)} OTC pairs with payout ≥ 80%")
            all_pairs.extend(otc_pairs)
        else:
            logger.info("No OTC pairs with good payout found")
        
        # إذا لم نجد أي أزواج مناسبة، نرجع للأزواج العادية
        if not all_pairs:
            logger.warning("No pairs found with payout rate ≥ 80%. Falling back to all valid pairs.")
            all_pairs = get_all_valid_otc_pairs()
            # إضافة أزواج البورصة العادية المتاحة للتداول الآن
            all_pairs.extend(get_tradable_market_pairs())
        
        # ترتيب الأزواج بشكل عشوائي
        random.shuffle(all_pairs)
        
        logger.info(f"Attempting to generate signals for {len(all_pairs)} pairs with good payout rates")
        
        # محاولة توليد إشارة لكل زوج
        for pair in all_pairs[:10]:  # نحاول مع 10 أزواج كحد أقصى
            # تحقق ما إذا كان هذا زوج بورصة عادية
            is_market_pair = any(pair == mp for mp in get_all_valid_market_pairs())
            
            # تحقق من أن زوج البورصة العادية متاح للتداول حالياً
            if is_market_pair and not is_pair_tradable_now(pair):
                logger.info(f"Skipping {pair} as it's not tradable at current time")
                continue
                
            logger.info(f"Attempting to generate safe signal for {pair}...")
            signal = self.get_filtered_signal(pair)
            
            if signal:
                # تحديد نوع الزوج ونسبة الربح
                if is_market_pair:
                    from market_pairs import get_pair_payout_rate
                    payout = get_pair_payout_rate(pair)
                    signal['pair_type'] = 'market'
                else:
                    from pocket_option_otc_pairs import get_pair_payout_rate
                    payout = get_pair_payout_rate(pair)
                    signal['pair_type'] = 'otc'
                    
                logger.info(f"Generated successful signal for {pair} ({signal['pair_type']}) with {payout}% payout rate")
                return signal
        
        # محاولة أخيرة بدون تحديد زوج (سيختار الزوج تلقائياً)
        logger.info("No suitable high payout pair found, attempting automatic pair selection...")
        return self.get_filtered_signal()

# مرشح عالمي للإشارات للاستخدام في جميع أنحاء التطبيق
signal_filter = SignalFilter()

def get_high_quality_signal(pair_id=None, pair_symbol=None):
    """
    الحصول على إشارة تداول عالية الجودة بعد تطبيق المرشحات المتقدمة
    
    Args:
        pair_id: معرف الزوج في قاعدة البيانات (اختياري)
        pair_symbol: رمز الزوج (اختياري)
        
    Returns:
        dict: معلومات الإشارة التي تم إنشاؤها والتحقق منها، أو None في حالة الفشل
    """
    return signal_filter.get_filtered_signal(pair_symbol)

def generate_safe_signal():
    """
    توليد إشارة آمنة عالية الجودة
    
    Returns:
        dict: معلومات الإشارة الآمنة، أو None في حالة الفشل
    """
    return signal_filter.generate_safe_signal()