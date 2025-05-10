"""
محلل الإطارات الزمنية المتعددة
يستخدم لتحليل الزوج على إطارات زمنية متعددة لتأكيد الإشارات وزيادة الدقة
"""

import logging
import numpy as np
from datetime import datetime, timedelta
import importlib

# تهيئة نظام التسجيل
logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    """محلل الإطارات الزمنية المتعددة"""
    
    def __init__(self):
        """تهيئة محلل الإطارات الزمنية المتعددة"""
        # قائمة الإطارات الزمنية التي يتم تحليلها
        self.timeframes = ['M1', 'M5', 'M15']
        
        # قائمة المؤشرات الفنية
        self.indicators = ['RSI', 'MACD', 'Stochastic', 'ADX']
        
        # وزن كل إطار زمني في التحليل النهائي
        self.timeframe_weights = {
            'M1': 0.5,   # الإطار الأساسي له الوزن الأكبر
            'M5': 0.3,
            'M15': 0.2
        }
        
        # قيم المؤشرات التي تشير إلى فرط الشراء/البيع
        self.overbought_levels = {
            'RSI': 70,
            'Stochastic': 80
        }
        
        self.oversold_levels = {
            'RSI': 30,
            'Stochastic': 20
        }
        
        logger.info("✅ تم تهيئة محلل الإطارات الزمنية المتعددة")
    
    def analyze(self, pair_symbol, candles_dict=None):
        """
        تحليل الزوج على إطارات زمنية متعددة
        
        Args:
            pair_symbol (str): رمز الزوج المراد تحليله
            candles_dict (dict, optional): قاموس بيانات الشموع لكل إطار زمني
            
        Returns:
            dict: نتائج التحليل لجميع الإطارات الزمنية
        """
        if not candles_dict:
            logger.warning("لا توجد بيانات للتحليل")
            return {
                'pair': pair_symbol,
                'trend': 'NEUTRAL',
                'strength': 0,
                'confidence': 0,
                'timeframes': {},
                'indicators': {},
                'support_resistance': {
                    'support': [],
                    'resistance': []
                }
            }
        
        # التحقق مما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
        is_otc_pair = False
        try:
            from pocket_option_otc_pairs import is_valid_otc_pair
            is_otc_pair = is_valid_otc_pair(pair_symbol)
            
            if is_otc_pair:
                logger.info(f"🔍 تحليل الإطارات الزمنية المتعددة لزوج OTC: {pair_symbol}")
                # ضبط الأوزان بشكل مختلف للأزواج OTC
                self.timeframe_weights = {
                    'M1': 0.6,  # زيادة وزن الإطار الزمني الأصغر للأزواج OTC لأنها أكثر تقلباً
                    'M5': 0.25,
                    'M15': 0.15
                }
        except ImportError:
            logger.info("لم يتم العثور على وحدة تحقق أزواج OTC")
        
        # تحليل كل إطار زمني
        timeframe_results = {}
        for tf in self.timeframes:
            if tf in candles_dict and candles_dict[tf]:
                timeframe_results[tf] = self._analyze_timeframe(candles_dict[tf])
            else:
                timeframe_results[tf] = {
                    'trend': 'NEUTRAL',
                    'strength': 0,
                    'indicators': {}
                }
        
        # تحليل نقاط الدعم والمقاومة عبر الإطارات الزمنية (تمرير معلومة كون الزوج OTC)
        sr_levels = self._analyze_support_resistance(candles_dict, is_otc_pair)
        
        # تحليل المؤشرات الفنية المتقدمة
        indicators_analysis = self._analyze_indicators(candles_dict)
        
        # تحديد الاتجاه العام وقوته (مع ضبط مختلف للأزواج OTC)
        overall_trend, trend_strength, trend_confidence = self._determine_overall_trend(timeframe_results)
        
        # تجميع النتائج
        result = {
            'pair': pair_symbol,
            'trend': overall_trend,
            'strength': trend_strength,
            'confidence': trend_confidence,
            'timeframes': timeframe_results,
            'indicators': indicators_analysis,
            'support_resistance': sr_levels
        }
        
        return result
    
    def _analyze_timeframe(self, candles):
        """
        تحليل إطار زمني واحد
        
        Args:
            candles (list): قائمة بيانات الشموع للإطار الزمني
            
        Returns:
            dict: نتائج تحليل الإطار الزمني
        """
        if not candles or len(candles) < 14:
            return {
                'trend': 'NEUTRAL',
                'strength': 0,
                'indicators': {}
            }
        
        # استخراج بيانات السعر
        closes = np.array([candle['close'] for candle in candles])
        highs = np.array([candle['high'] for candle in candles])
        lows = np.array([candle['low'] for candle in candles])
        
        # تحليل الاتجاه باستخدام المتوسطات المتحركة
        ma20 = self._calculate_ma(closes, 20)
        ma50 = self._calculate_ma(closes, 50)
        
        # تحديد الاتجاه بناءً على المتوسطات المتحركة
        current_price = closes[-1]
        trend = 'NEUTRAL'
        trend_strength = 0
        
        if current_price > ma20 and ma20 > ma50:
            # اتجاه صاعد
            trend = 'BUY'
            trend_strength = min(100, int(((current_price / ma20) - 1) * 500))
        elif current_price < ma20 and ma20 < ma50:
            # اتجاه هابط
            trend = 'SELL'
            trend_strength = min(100, int(((ma20 / current_price) - 1) * 500))
        
        # حساب المؤشرات الفنية
        indicators = {}
        
        # RSI
        rsi = self._calculate_rsi(closes)
        indicators['RSI'] = {
            'value': rsi,
            'signal': 'SELL' if rsi > self.overbought_levels['RSI'] else 'BUY' if rsi < self.oversold_levels['RSI'] else 'NEUTRAL',
            'zone': 'OVERBOUGHT' if rsi > self.overbought_levels['RSI'] else 'OVERSOLD' if rsi < self.oversold_levels['RSI'] else 'NEUTRAL'
        }
        
        # Stochastic
        k, d = self._calculate_stochastic(closes, highs, lows)
        stoch_signal = 'NEUTRAL'
        
        if k > self.overbought_levels['Stochastic'] and d > self.overbought_levels['Stochastic']:
            stoch_signal = 'SELL'
        elif k < self.oversold_levels['Stochastic'] and d < self.oversold_levels['Stochastic']:
            stoch_signal = 'BUY'
        
        indicators['Stochastic'] = {
            'k': k,
            'd': d,
            'signal': stoch_signal,
            'zone': 'OVERBOUGHT' if k > self.overbought_levels['Stochastic'] else 'OVERSOLD' if k < self.oversold_levels['Stochastic'] else 'NEUTRAL'
        }
        
        # MACD
        macd, signal, hist = self._calculate_macd(closes)
        macd_signal = 'BUY' if macd > signal else 'SELL' if macd < signal else 'NEUTRAL'
        
        indicators['MACD'] = {
            'macd': macd,
            'signal': macd_signal,
            'histogram': hist
        }
        
        return {
            'trend': trend,
            'strength': trend_strength,
            'price': current_price,
            'ma20': ma20,
            'ma50': ma50,
            'indicators': indicators
        }
    
    def _analyze_support_resistance(self, candles_dict, is_otc_pair=False):
        """
        تحليل نقاط الدعم والمقاومة عبر الإطارات الزمنية
        
        Args:
            candles_dict (dict): قاموس بيانات الشموع لكل إطار زمني
            is_otc_pair (bool): ما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
            
        Returns:
            dict: نقاط الدعم والمقاومة
        """
        # محاولة استخدام محلل نقاط الدعم والمقاومة المتقدم إذا كان متاحًا
        try:
            sr_analyzer = importlib.import_module('advanced_sr_analyzer')
            analyze_sr_levels = getattr(sr_analyzer, 'analyze_sr_levels', None)
            
            if analyze_sr_levels and 'M15' in candles_dict and candles_dict['M15']:
                # استخدام الإطار الزمني الأعلى للحصول على نقاط دعم ومقاومة أكثر دقة
                # تمرير معلومة كون الزوج من أزواج OTC أم لا
                if is_otc_pair:
                    logger.info("🔍 استخدام محلل SR متخصص لزوج OTC")
                
                sr_analysis = analyze_sr_levels(candles_dict['M15'], is_otc_pair=is_otc_pair)
                return {
                    'support': sr_analysis.get('support_levels', []),
                    'resistance': sr_analysis.get('resistance_levels', []),
                    'is_otc': is_otc_pair  # إضافة معلومة نوع الزوج للاستخدام في الواجهة
                }
                
        except (ImportError, AttributeError) as e:
            logger.warning(f"لم يتم العثور على محلل نقاط الدعم والمقاومة المتقدم: {e}")
        
        # استخدام طريقة بديلة بسيطة إذا لم يكن المحلل المتقدم متاحًا
        support_levels = []
        resistance_levels = []
        
        # جمع نقاط الدعم والمقاومة من جميع الإطارات الزمنية
        for tf, candles in candles_dict.items():
            if not candles or len(candles) < 20:
                continue
                
            tf_levels = self._find_key_levels(candles)
            
            # إضافة معلومات الإطار الزمني
            for level in tf_levels['support']:
                level['timeframe'] = tf
                # تعديل قوة المستويات لأزواج OTC
                if is_otc_pair:
                    level['strength'] = level.get('strength', 50) * 1.2  # زيادة قوة نقاط الدعم للأزواج OTC
                support_levels.append(level)
                
            for level in tf_levels['resistance']:
                level['timeframe'] = tf
                # تعديل قوة المستويات لأزواج OTC
                if is_otc_pair:
                    level['strength'] = level.get('strength', 50) * 1.2  # زيادة قوة نقاط المقاومة للأزواج OTC
                resistance_levels.append(level)
        
        # إزالة المستويات المتكررة بعتبة مختلفة لأزواج OTC
        threshold = 0.0008 if is_otc_pair else 0.001  # عتبة أقل للأزواج OTC للحصول على مستويات أكثر دقة
        unique_support = self._consolidate_levels(support_levels, threshold)
        unique_resistance = self._consolidate_levels(resistance_levels, threshold)
        
        return {
            'support': unique_support,
            'resistance': unique_resistance,
            'is_otc': is_otc_pair  # إضافة معلومة نوع الزوج للاستخدام في الواجهة
        }
    
    def _find_key_levels(self, candles):
        """
        العثور على نقاط الدعم والمقاومة الرئيسية في إطار زمني واحد
        
        Args:
            candles (list): قائمة بيانات الشموع
            
        Returns:
            dict: نقاط الدعم والمقاومة
        """
        if not candles or len(candles) < 20:
            return {'support': [], 'resistance': []}
        
        support_levels = []
        resistance_levels = []
        
        # استخراج بيانات السعر
        highs = [candle['high'] for candle in candles]
        lows = [candle['low'] for candle in candles]
        
        # البحث عن القمم المحلية (نقاط المقاومة)
        for i in range(2, len(candles) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append({
                    'price': highs[i],
                    'date': candles[i].get('date', ''),
                    'strength': 50  # قيمة افتراضية
                })
        
        # البحث عن القيعان المحلية (نقاط الدعم)
        for i in range(2, len(candles) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append({
                    'price': lows[i],
                    'date': candles[i].get('date', ''),
                    'strength': 50  # قيمة افتراضية
                })
        
        return {
            'support': support_levels,
            'resistance': resistance_levels
        }
    
    def _consolidate_levels(self, levels, threshold=0.001):
        """
        دمج مستويات الدعم/المقاومة المتقاربة
        
        Args:
            levels (list): قائمة المستويات
            threshold (float): عتبة القرب
            
        Returns:
            list: قائمة المستويات المدمجة
        """
        if not levels:
            return []
        
        # فرز المستويات حسب السعر
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        
        # تجميع المستويات
        consolidated = []
        current_group = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            current_level = sorted_levels[i]
            prev_level = sorted_levels[i-1]
            
            # حساب الفرق النسبي
            rel_diff = abs(current_level['price'] - prev_level['price']) / prev_level['price']
            
            if rel_diff < threshold:
                # إضافة إلى المجموعة الحالية
                current_group.append(current_level)
            else:
                # إنشاء مستوى جديد من المجموعة الحالية
                avg_price = sum(level['price'] for level in current_group) / len(current_group)
                avg_strength = sum(level.get('strength', 50) for level in current_group) / len(current_group)
                consolidated.append({
                    'price': avg_price,
                    'strength': avg_strength,
                    'timeframe': current_group[0].get('timeframe', 'unknown'),
                    'count': len(current_group)
                })
                
                # بدء مجموعة جديدة
                current_group = [current_level]
        
        # إضافة المجموعة الأخيرة
        if current_group:
            avg_price = sum(level['price'] for level in current_group) / len(current_group)
            avg_strength = sum(level.get('strength', 50) for level in current_group) / len(current_group)
            consolidated.append({
                'price': avg_price,
                'strength': avg_strength,
                'timeframe': current_group[0].get('timeframe', 'unknown'),
                'count': len(current_group)
            })
        
        return consolidated
    
    def _analyze_indicators(self, candles_dict):
        """
        تحليل المؤشرات الفنية عبر الإطارات الزمنية
        
        Args:
            candles_dict (dict): قاموس بيانات الشموع لكل إطار زمني
            
        Returns:
            dict: تحليلات المؤشرات الفنية
        """
        indicator_signals = {
            'RSI': {
                'value': 0,
                'signal': 'NEUTRAL',
                'direction': 0
            },
            'MACD': {
                'value': 0,
                'signal': 'NEUTRAL',
                'direction': 0
            },
            'Stochastic': {
                'k': 0,
                'd': 0,
                'signal': 'NEUTRAL',
                'direction': 0
            }
        }
        
        # تجميع إشارات المؤشرات من جميع الإطارات الزمنية
        for tf, weight in self.timeframe_weights.items():
            if tf not in candles_dict or not candles_dict[tf]:
                continue
                
            # الحصول على تحليل الإطار الزمني
            tf_result = self._analyze_timeframe(candles_dict[tf])
            tf_indicators = tf_result.get('indicators', {})
            
            # دمج إشارات المؤشرات مع الوزن المناسب
            for ind_name, ind_data in tf_indicators.items():
                if ind_name in indicator_signals:
                    # RSI
                    if ind_name == 'RSI':
                        indicator_signals[ind_name]['value'] += ind_data.get('value', 50) * weight
                        
                        if ind_data.get('signal', 'NEUTRAL') == 'BUY':
                            indicator_signals[ind_name]['direction'] += 1 * weight
                        elif ind_data.get('signal', 'NEUTRAL') == 'SELL':
                            indicator_signals[ind_name]['direction'] -= 1 * weight
                    
                    # MACD
                    elif ind_name == 'MACD':
                        if ind_data.get('signal', 'NEUTRAL') == 'BUY':
                            indicator_signals[ind_name]['direction'] += 1 * weight
                        elif ind_data.get('signal', 'NEUTRAL') == 'SELL':
                            indicator_signals[ind_name]['direction'] -= 1 * weight
                    
                    # Stochastic
                    elif ind_name == 'Stochastic':
                        indicator_signals[ind_name]['k'] += ind_data.get('k', 50) * weight
                        indicator_signals[ind_name]['d'] += ind_data.get('d', 50) * weight
                        
                        if ind_data.get('signal', 'NEUTRAL') == 'BUY':
                            indicator_signals[ind_name]['direction'] += 1 * weight
                        elif ind_data.get('signal', 'NEUTRAL') == 'SELL':
                            indicator_signals[ind_name]['direction'] -= 1 * weight
        
        # تحديد الإشارة النهائية لكل مؤشر
        for ind_name, ind_data in indicator_signals.items():
            direction = ind_data.get('direction', 0)
            
            if direction > 0.3:
                ind_data['signal'] = 'BUY'
            elif direction < -0.3:
                ind_data['signal'] = 'SELL'
            else:
                ind_data['signal'] = 'NEUTRAL'
        
        return indicator_signals
    
    def _determine_overall_trend(self, timeframe_results):
        """
        تحديد الاتجاه العام وقوته وثقته
        
        Args:
            timeframe_results (dict): نتائج تحليل الإطارات الزمنية
            
        Returns:
            tuple: (الاتجاه، القوة، الثقة)
        """
        # حساب القيم المرجحة لكل إطار زمني
        buy_score = 0
        sell_score = 0
        total_weight = 0
        
        for tf, weight in self.timeframe_weights.items():
            if tf in timeframe_results:
                result = timeframe_results[tf]
                strength = result.get('strength', 0) / 100.0  # تحويل إلى نسبة
                
                if result.get('trend', 'NEUTRAL') == 'BUY':
                    buy_score += strength * weight
                elif result.get('trend', 'NEUTRAL') == 'SELL':
                    sell_score += strength * weight
                
                total_weight += weight
        
        # تحديد الاتجاه العام
        overall_trend = 'NEUTRAL'
        if buy_score > sell_score and (buy_score - sell_score) > 0.1:
            overall_trend = 'BUY'
        elif sell_score > buy_score and (sell_score - buy_score) > 0.1:
            overall_trend = 'SELL'
        
        # حساب قوة الاتجاه
        trend_strength = 0
        if overall_trend == 'BUY':
            trend_strength = int(buy_score / total_weight * 100) if total_weight > 0 else 0
        elif overall_trend == 'SELL':
            trend_strength = int(sell_score / total_weight * 100) if total_weight > 0 else 0
        
        # حساب ثقة الاتجاه (بناءً على اتفاق الإطارات الزمنية)
        aligned_timeframes = 0
        for tf in self.timeframes:
            if tf in timeframe_results and timeframe_results[tf].get('trend', 'NEUTRAL') == overall_trend:
                aligned_timeframes += 1
        
        trend_confidence = int((aligned_timeframes / len(self.timeframes)) * 100)
        
        return overall_trend, trend_strength, trend_confidence
    
    def _calculate_ma(self, data, period):
        """حساب المتوسط المتحرك"""
        if len(data) >= period:
            return np.mean(data[-period:])
        return data[-1] if len(data) > 0 else 0
    
    def _calculate_rsi(self, data, period=14):
        """حساب مؤشر القوة النسبية (RSI)"""
        if len(data) < period + 1:
            return 50  # قيمة افتراضية
        
        deltas = np.diff(data)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return 100
        
        rs = up / down
        return 100 - (100 / (1 + rs))
    
    def _calculate_stochastic(self, closes, highs, lows, k_period=14, d_period=3):
        """حساب مؤشر Stochastic"""
        if len(closes) < k_period:
            return 50, 50  # قيم افتراضية
        
        # حساب %K
        lowest_low = np.min(lows[-k_period:])
        highest_high = np.max(highs[-k_period:])
        
        if highest_high == lowest_low:
            k = 50
        else:
            k = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)
        
        # حساب %D (المتوسط المتحرك لـ %K)
        k_values = []
        for i in range(min(d_period, len(closes))):
            if len(closes) > k_period + i:
                low_i = np.min(lows[-(k_period+i):-i] if i > 0 else lows[-k_period:])
                high_i = np.max(highs[-(k_period+i):-i] if i > 0 else highs[-k_period:])
                
                if high_i == low_i:
                    k_i = 50
                else:
                    k_i = 100 * (closes[-1-i] - low_i) / (high_i - low_i)
                
                k_values.append(k_i)
        
        d = np.mean(k_values) if k_values else 50
        
        return k, d
    
    def _calculate_macd(self, data, fast_period=12, slow_period=26, signal_period=9):
        """حساب مؤشر MACD"""
        if len(data) < slow_period:
            return 0, 0, 0  # قيم افتراضية
        
        # حساب EMA السريع والبطيء
        ema_fast = self._calculate_ema(data, fast_period)
        ema_slow = self._calculate_ema(data, slow_period)
        
        # حساب MACD
        macd = ema_fast - ema_slow
        
        # حساب خط الإشارة (EMA للـ MACD)
        # نستخدم قيمة MACD الأخيرة فقط بدلاً من سلسلة القيم
        signal = macd * 0.9  # تقريب بسيط
        
        # حساب الرسم البياني (MACD - Signal)
        histogram = macd - signal
        
        return macd, signal, histogram
    
    def _calculate_ema(self, data, period):
        """حساب المتوسط المتحرك الأسي (EMA)"""
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        
        alpha = 2 / (period + 1)
        ema = data[-period]
        
        for i in range(-period+1, 0):
            ema = data[i] * alpha + ema * (1 - alpha)
        
        return ema

# إنشاء كائن عام للاستخدام
multi_tf_analyzer = MultiTimeframeAnalyzer()

def get_multi_timeframe_signal(pair_symbol, candles_dict=None):
    """
    الحصول على إشارة من تحليل الإطارات الزمنية المتعددة
    
    Args:
        pair_symbol (str): رمز الزوج
        candles_dict (dict, optional): قاموس بيانات الشموع لكل إطار زمني
        
    Returns:
        dict: إشارة التداول ومعلوماتها
    """
    # التحقق مما إذا كان الزوج من أزواج OTC الخاصة بمنصة Pocket Option
    is_otc_pair = False
    try:
        from pocket_option_otc_pairs import is_valid_otc_pair
        is_otc_pair = is_valid_otc_pair(pair_symbol)
        
        if is_otc_pair:
            logger.info(f"🔍 تحليل متعدد الإطارات لزوج OTC: {pair_symbol}")
    except ImportError:
        pass
    
    # تحليل الإطارات الزمنية المتعددة
    analysis = multi_tf_analyzer.analyze(pair_symbol, candles_dict)
    
    # استخراج الاتجاه وقوته وثقته
    trend = analysis.get('trend', 'NEUTRAL')
    strength = analysis.get('strength', 0)
    confidence = analysis.get('confidence', 0)
    
    # زيادة الثقة لأزواج OTC عند تطابق الاتجاه في الإطارات الزمنية المختلفة
    if is_otc_pair and trend != 'NEUTRAL':
        # تعديل الثقة للأزواج OTC إذا كان هناك تطابق جيد في الاتجاه
        if confidence > 60:
            confidence = min(95, confidence + 10)
            logger.info(f"✅ زيادة الثقة في تحليل زوج OTC ({pair_symbol}) إلى {confidence}%")
    
    # تحويل التحليل إلى إشارة تداول
    signal = {
        'pair': pair_symbol,
        'direction': trend,
        'probability': min(95, int(strength * 0.7 + confidence * 0.3)),
        'analysis': f"{trend} : قوة {strength}%, ثقة {confidence}%",
        'timeframe_analysis': analysis,
        'sr_levels': analysis.get('support_resistance'),
        'is_otc_pair': is_otc_pair  # إضافة معلومة نوع الزوج
    }
    
    # إضافة تأكيد الدعم/المقاومة
    sr_levels = analysis.get('support_resistance', {})
    current_price = 0
    
    # الحصول على السعر الحالي
    if 'M1' in analysis.get('timeframes', {}) and analysis['timeframes']['M1']:
        current_price = analysis['timeframes']['M1'].get('price', 0)
    
    # تأكيد الإشارة بناءً على نقاط الدعم والمقاومة
    if current_price > 0:
        if trend == 'BUY':
            # التحقق من وجود مستوى دعم قريب تحت السعر الحالي (جيد للشراء)
            support_levels = sr_levels.get('support', [])
            for level in support_levels:
                price_diff = abs(current_price - level.get('price', 0)) / current_price
                if price_diff < 0.002:  # قريب جداً (0.2%)
                    signal['sr_validated'] = True
                    signal['sr_info'] = f"ارتداد من مستوى دعم {level.get('price', 0):.5f}"
                    break
                    
        elif trend == 'SELL':
            # التحقق من وجود مستوى مقاومة قريب فوق السعر الحالي (جيد للبيع)
            resistance_levels = sr_levels.get('resistance', [])
            for level in resistance_levels:
                price_diff = abs(level.get('price', 0) - current_price) / current_price
                if price_diff < 0.002:  # قريب جداً (0.2%)
                    signal['sr_validated'] = True
                    signal['sr_info'] = f"ارتداد من مستوى مقاومة {level.get('price', 0):.5f}"
                    break
    
    return signal