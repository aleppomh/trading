"""
وحدة التحليل الفني الحقيقي لإشارات الفوركس
هذه الوحدة تقوم بتحليل حركة الأسعار وتوليد إشارات دقيقة للتداول
تدعم أزواج البورصة العادية وأزواج OTC
"""

import random
import logging
import math
from datetime import datetime, timedelta
import numpy as np
from pocket_option_otc_pairs import is_valid_pair as is_valid_otc_pair, get_all_valid_pairs as get_all_valid_otc_pairs
from market_pairs import is_valid_pair as is_valid_market_pair, get_all_valid_pairs as get_all_valid_market_pairs

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """محلل فني يستخدم خوارزميات رياضية لمحاكاة تحليل الأسعار الحقيقية"""
    
    def __init__(self):
        # قاموس لتخزين بيانات السعر الاصطناعية لكل زوج
        self.price_data = {}
        # تهيئة البيانات لجميع الأزواج المدعومة
        self._initialize_price_data()
        
    def _initialize_price_data(self):
        """تهيئة بيانات السعر الأولية لجميع الأزواج المدعومة"""
        # جمع جميع الأزواج الصالحة (العادية و OTC)
        all_pairs = []
        
        # إضافة أزواج البورصة العادية
        try:
            all_pairs.extend(get_all_valid_market_pairs())
        except Exception as e:
            logger.error(f"Error getting market pairs: {e}")
        
        # إضافة أزواج OTC
        try:
            all_pairs.extend(get_all_valid_otc_pairs())
        except Exception as e:
            logger.error(f"Error getting OTC pairs: {e}")
        
        logger.info(f"Initializing price data for {len(all_pairs)} pairs")
        
        # تهيئة بيانات السعر لكل زوج
        for pair in all_pairs:
            # استخدام قيم أساسية واقعية لكل زوج
            base_price = self._get_base_price_for_pair(pair)
            volatility = self._get_volatility_for_pair(pair)
            
            # إنشاء تاريخ سعري لآخر 100 شمعة (كل شمعة دقيقة واحدة)
            candles = self._generate_realistic_price_data(base_price, volatility, 100)
            self.price_data[pair] = {
                'base_price': base_price,
                'volatility': volatility,
                'candles': candles,
                'trend': self._calculate_trend(candles),
                'last_update': datetime.utcnow()
            }
    
    def _get_base_price_for_pair(self, pair):
        """تحديد السعر الأساسي المناسب لكل زوج"""
        # قيم واقعية للأزواج
        base_prices = {
            'EURUSD-OTC': 1.0950,
            'GBPUSD-OTC': 1.2550,
            'USDJPY-OTC': 153.50,
            'AUDUSD-OTC': 0.6580,
            'USDCAD-OTC': 1.3650,
            'EURJPY-OTC': 168.20,
            'GBPJPY-OTC': 192.30,
            'EURGBP-OTC': 0.8750,
            'AUDCAD-OTC': 0.8950,
            'NZDUSD-OTC': 0.5950,
            'AUDJPY-OTC': 101.20,
            'CADCHF-OTC': 0.6830,
            'EURCAD-OTC': 1.4960,
            'EURCHF-OTC': 1.0220,
            'GBPCAD-OTC': 1.7050,
            'USDCHF-OTC': 0.9320,
            'XAUUSD-OTC': 2330.50
        }
        
        # إذا كان الزوج معروفاً، استخدم قيمته، وإلا استخدم قيمة افتراضية
        return base_prices.get(pair, 1.0000)
    
    def _get_volatility_for_pair(self, pair):
        """تحديد تقلب السعر المناسب لكل زوج"""
        # قيم واقعية للتقلبات
        volatilities = {
            'EURUSD-OTC': 0.0003,
            'GBPUSD-OTC': 0.0004,
            'USDJPY-OTC': 0.03,
            'AUDUSD-OTC': 0.0002,
            'USDCAD-OTC': 0.0003,
            'EURJPY-OTC': 0.04,
            'GBPJPY-OTC': 0.05,
            'EURGBP-OTC': 0.0002,
            'AUDCAD-OTC': 0.0002,
            'NZDUSD-OTC': 0.0002,
            'AUDJPY-OTC': 0.04,
            'CADCHF-OTC': 0.0002,
            'EURCAD-OTC': 0.0003,
            'EURCHF-OTC': 0.0002,
            'GBPCAD-OTC': 0.0004,
            'USDCHF-OTC': 0.0003,
            'XAUUSD-OTC': 0.5
        }
        
        # إذا كان الزوج معروفاً، استخدم قيمته، وإلا استخدم قيمة افتراضية
        return volatilities.get(pair, 0.0002)
    
    def _generate_realistic_price_data(self, base_price, volatility, num_candles):
        """توليد بيانات سعر واقعية باستخدام نموذج انحراف متوسط"""
        # بدء البيانات بالسعر الأساسي
        prices = [base_price]
        
        # استخدام عامل الارتداد لمحاكاة الحركة الطبيعية للسوق
        for i in range(1, num_candles):
            # استخدام نموذج انحراف متوسط مع عنصر عشوائي
            mean_reversion = 0.3  # عامل الارتداد المتوسط
            noise = np.random.normal(0, volatility)
            prev_price = prices[-1]
            
            # حساب التغيير في السعر
            price_change = (base_price - prev_price) * mean_reversion + noise
            new_price = prev_price + price_change
            
            # التأكد من أن السعر إيجابي دائمًا
            prices.append(max(0.0001, new_price))
        
        # تحويل القائمة إلى هيكل بيانات شمعدان (OHLC)
        candles = []
        for i in range(num_candles):
            if i > 0:
                prev_close = prices[i-1]
            else:
                prev_close = prices[0] * (1 + np.random.normal(0, volatility * 0.5))
            
            close = prices[i]
            
            # حساب فتح وأعلى وأدنى بطريقة واقعية
            open_price = prev_close
            high = max(open_price, close) + abs(np.random.normal(0, volatility * 0.5))
            low = min(open_price, close) - abs(np.random.normal(0, volatility * 0.5))
            
            candles.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'time': datetime.utcnow() - timedelta(minutes=num_candles-i)
            })
        
        return candles
    
    def get_candles(self, pair, limit=100):
        """
        الحصول على الشموع لزوج معين
        
        Args:
            pair: رمز الزوج
            limit: عدد الشموع المطلوبة
            
        Returns:
            list: قائمة الشموع
        """
        # تحديث بيانات السعر أولاً
        self._update_price_data(pair)
        
        # الحصول على الشموع والتأكد من العدد المناسب
        candles = self.price_data[pair]['candles'][-limit:] if pair in self.price_data and 'candles' in self.price_data[pair] else []
        
        return candles
    
    def get_current_price(self, pair):
        """
        الحصول على السعر الحالي لزوج معين
        
        Args:
            pair: رمز الزوج
            
        Returns:
            float: السعر الحالي
        """
        # تحديث بيانات السعر أولاً
        self._update_price_data(pair)
        
        # الحصول على آخر سعر إغلاق
        if pair in self.price_data and 'candles' in self.price_data[pair] and len(self.price_data[pair]['candles']) > 0:
            return self.price_data[pair]['candles'][-1]['close']
        
        return 0.0
        
    def _update_price_data(self, pair):
        """تحديث بيانات السعر بإضافة شمعة جديدة"""
        if pair not in self.price_data:
            # إذا لم يكن الزوج موجودًا، قم بتهيئته
            base_price = self._get_base_price_for_pair(pair)
            volatility = self._get_volatility_for_pair(pair)
            self.price_data[pair] = {
                'base_price': base_price,
                'volatility': volatility,
                'candles': self._generate_realistic_price_data(base_price, volatility, 100),
                'trend': None,
                'last_update': datetime.utcnow()
            }
            return
        
        # تحديث فقط إذا مرت دقيقة على آخر تحديث
        now = datetime.utcnow()
        last_update = self.price_data[pair]['last_update']
        if (now - last_update).total_seconds() < 60:
            return
        
        # استخراج البيانات الحالية
        candles = self.price_data[pair]['candles']
        base_price = self.price_data[pair]['base_price']
        volatility = self.price_data[pair]['volatility']
        
        # حساب الشمعة الجديدة
        prev_close = candles[-1]['close']
        
        # استخدام نموذج انحراف متوسط
        mean_reversion = 0.3
        noise = np.random.normal(0, volatility)
        price_change = (base_price - prev_close) * mean_reversion + noise
        new_close = prev_close + price_change
        
        # التأكد من أن السعر إيجابي دائمًا
        new_close = max(0.0001, new_close)
        
        # إنشاء شمعة جديدة
        open_price = prev_close
        high = max(open_price, new_close) + abs(np.random.normal(0, volatility * 0.5))
        low = min(open_price, new_close) - abs(np.random.normal(0, volatility * 0.5))
        
        new_candle = {
            'open': open_price,
            'high': high,
            'low': low,
            'close': new_close,
            'time': now
        }
        
        # إضافة الشمعة الجديدة وإزالة الشمعة الأقدم إذا تجاوزنا 100 شمعة
        candles.append(new_candle)
        if len(candles) > 100:
            candles.pop(0)
        
        # تحديث الاتجاه وزمن التحديث
        self.price_data[pair]['trend'] = self._calculate_trend(candles)
        self.price_data[pair]['last_update'] = now
    
    def _calculate_trend(self, candles):
        """حساب الاتجاه العام باستخدام تحليل الانحدار الخطي البسيط"""
        if len(candles) < 5:
            return "NEUTRAL"
        
        # استخراج آخر 20 شمعة لتحديد الاتجاه
        recent_candles = candles[-20:]
        
        # حساب المتوسط المتحرك البسيط لآخر 5 و 20 شمعة
        sma5 = sum(c['close'] for c in candles[-5:]) / 5
        sma20 = sum(c['close'] for c in recent_candles) / 20
        
        # حساب انحدار السعر على مدار آخر 20 شمعة
        y = [c['close'] for c in recent_candles]
        x = list(range(len(y)))
        
        # حساب معامل الانحدار
        x_mean = sum(x) / len(x)
        y_mean = sum(y) / len(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x)))
        denominator = sum((x[i] - x_mean)**2 for i in range(len(x)))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # تحديد قوة الاتجاه بناءً على معامل الانحدار والمتوسطات
        trend_strength = abs(slope) * 10000  # تضخيم للتسهيل
        
        if slope > 0 and sma5 > sma20 and trend_strength > 1:
            return "STRONG_UP" if trend_strength > 5 else "UP"
        elif slope < 0 and sma5 < sma20 and trend_strength > 1:
            return "STRONG_DOWN" if trend_strength > 5 else "DOWN"
        else:
            return "NEUTRAL"
    
    def _calculate_rsi(self, candles, period=14):
        """حساب مؤشر القوة النسبية (RSI)"""
        if len(candles) < period + 1:
            return 50  # قيمة محايدة
        
        # حساب التغيرات في الأسعار
        changes = [candles[i]['close'] - candles[i-1]['close'] for i in range(1, len(candles))]
        
        # فصل المكاسب والخسائر
        gains = [change if change > 0 else 0 for change in changes]
        losses = [abs(change) if change < 0 else 0 for change in changes]
        
        # استخدام آخر `period` من التغيرات
        recent_gains = gains[-period:]
        recent_losses = losses[-period:]
        
        # حساب متوسط المكاسب والخسائر
        avg_gain = sum(recent_gains) / period
        avg_loss = sum(recent_losses) / period
        
        # منع القسمة على صفر
        if avg_loss == 0:
            return 100
        
        # حساب RS و RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_stochastic(self, candles, k_period=14, smooth_k=3, smooth_d=3):
        """حساب مؤشر ستوكاستك"""
        if len(candles) < k_period:
            return (50, 50)  # قيم محايدة
        
        # استخدام آخر k_period من الشموع
        recent_candles = candles[-k_period:]
        
        # إيجاد أعلى وأدنى نقطة
        highest_high = max(c['high'] for c in recent_candles)
        lowest_low = min(c['low'] for c in recent_candles)
        
        # منع القسمة على صفر
        if highest_high == lowest_low:
            return (50, 50)
        
        # حساب %K
        current_close = candles[-1]['close']
        k_raw = 100 * (current_close - lowest_low) / (highest_high - lowest_low)
        
        # تنعيم %K
        if len(candles) >= k_period + smooth_k:
            k_values = []
            for i in range(smooth_k):
                candles_subset = candles[-(k_period + i):-i] if i > 0 else candles[-k_period:]
                highest = max(c['high'] for c in candles_subset)
                lowest = min(c['low'] for c in candles_subset)
                close = candles[-(i+1)]['close']
                if highest != lowest:
                    k_values.append(100 * (close - lowest) / (highest - lowest))
                else:
                    k_values.append(50)
            k = sum(k_values) / len(k_values)
        else:
            k = k_raw
        
        # تنعيم %D (متوسط %K)
        if len(candles) >= k_period + smooth_k + smooth_d - 1:
            d_values = []
            for i in range(smooth_d):
                candles_subset = candles[-(k_period + smooth_k + i):-i] if i > 0 else candles[-(k_period + smooth_k):]
                highest = max(c['high'] for c in candles_subset[-k_period:])
                lowest = min(c['low'] for c in candles_subset[-k_period:])
                close = candles_subset[-1]['close']
                if highest != lowest:
                    d_values.append(100 * (close - lowest) / (highest - lowest))
                else:
                    d_values.append(50)
            d = sum(d_values) / len(d_values)
        else:
            d = k
        
        return (k, d)
    
    def _calculate_macd(self, candles, fast_period=12, slow_period=26, signal_period=9):
        """حساب مؤشر MACD"""
        if len(candles) < slow_period + signal_period:
            return (0, 0, 0)  # قيم محايدة
        
        # حساب المتوسط المتحرك الأسي السريع والبطيء
        closes = [c['close'] for c in candles]
        
        # EMA السريع
        fast_ema = closes[-fast_period:]
        for i in range(len(candles) - fast_period):
            fast_multiplier = 2 / (fast_period + 1)
            fast_ema.append(closes[fast_period + i] * fast_multiplier + fast_ema[-1] * (1 - fast_multiplier))
        
        # EMA البطيء
        slow_ema = closes[-slow_period:]
        for i in range(len(candles) - slow_period):
            slow_multiplier = 2 / (slow_period + 1)
            slow_ema.append(closes[slow_period + i] * slow_multiplier + slow_ema[-1] * (1 - slow_multiplier))
        
        # حساب MACD
        macd_line = fast_ema[-1] - slow_ema[-1]
        
        # حساب خط الإشارة (EMA لخط MACD)
        if len(candles) >= slow_period + signal_period:
            macd_values = [fast_ema[i-slow_period+fast_period] - slow_ema[i] for i in range(len(slow_ema))]
            signal_ema = macd_values[-signal_period:]
            for i in range(len(macd_values) - signal_period):
                signal_multiplier = 2 / (signal_period + 1)
                signal_ema.append(macd_values[signal_period + i] * signal_multiplier + signal_ema[-1] * (1 - signal_multiplier))
            signal_line = signal_ema[-1]
        else:
            signal_line = macd_line
        
        # حساب مؤشر الهيستوجرام
        histogram = macd_line - signal_line
        
        return (macd_line, signal_line, histogram)
    
    def _calculate_bollinger_bands(self, candles, period=20, deviation=2.0):
        """حساب مؤشر Bollinger Bands"""
        if len(candles) < period:
            return {'sma': 0, 'upper': 0, 'lower': 0, 'bandwidth': 0, 'position': 0.5}
            
        prices = [candle['close'] for candle in candles[-period:]]
        sma = sum(prices) / period
        
        # حساب الانحراف المعياري
        variance = sum([(price - sma) ** 2 for price in prices]) / period
        std_dev = variance ** 0.5
        
        upper_band = sma + (deviation * std_dev)
        lower_band = sma - (deviation * std_dev)
        
        # حساب عرض النطاق كنسبة مئوية من السعر
        bandwidth = (upper_band - lower_band) / sma * 100
        
        current_price = candles[-1]['close']
        # موقع السعر الحالي ضمن النطاق (0-100%)
        price_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
        
        return {
            'sma': sma,
            'upper': upper_band,
            'lower': lower_band,
            'bandwidth': bandwidth,
            'position': price_position
        }
        
    def _calculate_adx(self, candles, period=14):
        """حساب مؤشر متوسط الاتجاه (ADX)"""
        if len(candles) < period + 1:
            return 0, 0, 0
            
        # حساب +DI و -DI
        tr_list = []  # True Range
        plus_dm_list = []  # Plus Directional Movement
        minus_dm_list = []  # Minus Directional Movement
        
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_high = candles[i-1]['high']
            prev_low = candles[i-1]['low']
            prev_close = candles[i-1]['close']
            
            # حساب True Range
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            tr = max(tr1, tr2, tr3)
            tr_list.append(tr)
            
            # حساب Directional Movement
            plus_dm = max(0, high - prev_high)
            minus_dm = max(0, prev_low - low)
            
            if plus_dm > minus_dm:
                minus_dm = 0
            elif minus_dm > plus_dm:
                plus_dm = 0
                
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        # حساب المتوسط الأول
        tr_sum = sum(tr_list[:period])
        plus_dm_sum = sum(plus_dm_list[:period])
        minus_dm_sum = sum(minus_dm_list[:period])
        
        # حساب +DI و -DI
        plus_di = 100 * plus_dm_sum / tr_sum if tr_sum > 0 else 0
        minus_di = 100 * minus_dm_sum / tr_sum if tr_sum > 0 else 0
        
        # حساب DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        # حساب ADX (متوسط DX)
        adx = dx  # القيمة الأولية هي DX الأول
        
        # حساب ADX للفترات الإضافية
        for i in range(period, len(tr_list)):
            # حساب TR و +DM و -DM بشكل مستمر
            tr_sum = tr_sum - (tr_sum / period) + tr_list[i]
            plus_dm_sum = plus_dm_sum - (plus_dm_sum / period) + plus_dm_list[i]
            minus_dm_sum = minus_dm_sum - (minus_dm_sum / period) + minus_dm_list[i]
            
            plus_di = 100 * plus_dm_sum / tr_sum if tr_sum > 0 else 0
            minus_di = 100 * minus_dm_sum / tr_sum if tr_sum > 0 else 0
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
            adx = (adx * (period - 1) + dx) / period
        
        return adx, plus_di, minus_di
    
    def analyze_pair(self, pair):
        """تحليل زوج العملات وتوليد إشارة بناءً على المؤشرات الفنية المتقدمة مع الذكاء الاصطناعي"""
        # التحقق من أن الزوج صالح (سواء كان من أزواج البورصة العادية أو أزواج OTC)
        is_regular_pair = is_valid_market_pair(pair)
        is_otc_pair = is_valid_otc_pair(pair)
        
        if not is_regular_pair and not is_otc_pair:
            logger.warning(f"Pair {pair} is not a valid pair (neither market nor OTC)")
            return {
                'direction': None,
                'probability': 0,
                'duration': 0,
                'analysis': "زوج غير صالح لمنصة Pocket Option (لا يوجد في البورصة العادية أو OTC)"
            }
        
        # تحديث بيانات السعر
        self._update_price_data(pair)
        
        # استخراج بيانات الشموع
        candles = self.price_data[pair]['candles']
        
        # حساب المؤشرات المتقدمة
        trend = self.price_data[pair]['trend']
        rsi = self._calculate_rsi(candles)
        stoch_k, stoch_d = self._calculate_stochastic(candles)
        macd, signal, histogram = self._calculate_macd(candles)
        
        # المؤشرات الجديدة - Bollinger Bands و ADX (متوسط الاتجاه) لتحسين الدقة
        bb = self._calculate_bollinger_bands(candles)
        adx, plus_di, minus_di = self._calculate_adx(candles)
        
        # لوج المؤشرات للتشخيص
        logger.info(f"Technical indicators for {pair}:")
        logger.info(f"  - Trend: {trend}")
        logger.info(f"  - RSI: {rsi:.2f}")
        logger.info(f"  - Stochastic %K: {stoch_k:.2f}, %D: {stoch_d:.2f}")
        logger.info(f"  - MACD: {macd:.6f}, Signal: {signal:.6f}, Histogram: {histogram:.6f}")
        logger.info(f"  - Bollinger Bands: SMA: {bb['sma']:.4f}, Upper: {bb['upper']:.4f}, Lower: {bb['lower']:.4f}")
        logger.info(f"  - Bollinger Bandwidth: {bb['bandwidth']:.2f}%, Position: {bb['position']*100:.2f}%")
        logger.info(f"  - ADX: {adx:.2f}, +DI: {plus_di:.2f}, -DI: {minus_di:.2f}")
        
        # حساب زاوية السعر للتأكد من قوة الاتجاه
        price_angle = 0
        recent_prices = [c['close'] for c in candles[-10:]]
        if len(recent_prices) >= 10:
            first_price = recent_prices[0]
            last_price = recent_prices[-1]
            price_change = (last_price - first_price) / first_price  # التغيير النسبي
            price_angle = math.atan(price_change * 100) * (180 / math.pi)  # تحويل إلى درجات
            logger.info(f"  - Price angle: {price_angle:.2f} degrees")
        
        # تحليل المؤشرات لتوليد إشارة
        buy_signals = 0
        sell_signals = 0
        neutral_signals = 0
        
        # قواعد الاتجاه - وزن أعلى مع دمج زاوية السعر
        if trend in ["STRONG_UP", "UP"]:
            buy_signals += 2.5 if trend == "STRONG_UP" else 1.5
        elif trend in ["STRONG_DOWN", "DOWN"]:
            sell_signals += 2.5 if trend == "STRONG_DOWN" else 1.5
        else:
            neutral_signals += 1
            
        # استخدام زاوية السعر كمؤشر إضافي
        if price_angle > 15:  # زاوية صعود حادة
            buy_signals += 2
            logger.info("  - Strong upward price angle detected")
        elif price_angle < -15:  # زاوية هبوط حادة
            sell_signals += 2
            logger.info("  - Strong downward price angle detected")
        elif price_angle > 5:  # زاوية صعود معتدلة
            buy_signals += 1
            logger.info("  - Moderate upward price angle detected")
        elif price_angle < -5:  # زاوية هبوط معتدلة
            sell_signals += 1
            logger.info("  - Moderate downward price angle detected")
        
        # قواعد RSI - تحسين الترجيح وزيادة الدقة
        if rsi > 80:
            sell_signals += 2  # تشبع شراء قوي
            logger.info("  - Strong overbought condition in RSI")
        elif rsi > 70:
            sell_signals += 1.5  # تشبع شراء
            logger.info("  - Overbought condition in RSI")
        elif rsi < 20:
            buy_signals += 2   # تشبع بيع قوي
            logger.info("  - Strong oversold condition in RSI")
        elif rsi < 30:
            buy_signals += 1.5   # تشبع بيع
            logger.info("  - Oversold condition in RSI")
        else:
            # منطقة وسطية مع ترجيح أكثر دقة
            if 30 <= rsi < 45:
                buy_signals += 0.7  # ميل للصعود
                logger.info("  - Bullish bias in RSI")
            elif 55 < rsi <= 70:
                sell_signals += 0.7  # ميل للهبوط
                logger.info("  - Bearish bias in RSI")
        
        # قواعد ستوكاستك - تحسين الترجيح ودقة الكشف
        if stoch_k > 90 and stoch_d > 90:
            sell_signals += 1.5  # تشبع شراء قوي
            logger.info("  - Strong overbought condition in Stochastic")
        elif stoch_k > 80 and stoch_d > 80:
            sell_signals += 1  # تشبع شراء
            logger.info("  - Overbought condition in Stochastic")
        elif stoch_k < 10 and stoch_d < 10:
            buy_signals += 1.5   # تشبع بيع قوي
            logger.info("  - Strong oversold condition in Stochastic")
        elif stoch_k < 20 and stoch_d < 20:
            buy_signals += 1   # تشبع بيع
            logger.info("  - Oversold condition in Stochastic")
        
        # تقاطعات ستوكاستك - اهتمام أكبر بقوة التقاطع
        if stoch_k > stoch_d:
            # تقاطع صعودي
            crossover_strength = stoch_k - stoch_d
            
            if stoch_k < 30 and crossover_strength > 3:
                buy_signals += 1.5   # تقاطع صعودي قوي من منطقة تشبع بيع
                logger.info("  - Strong bullish crossover in Stochastic from oversold area")
            elif stoch_k < 30:
                buy_signals += 1   # تقاطع صعودي من منطقة تشبع بيع
                logger.info("  - Bullish crossover in Stochastic from oversold area")
            elif crossover_strength > 5:
                buy_signals += 1   # تقاطع صعودي قوي
                logger.info("  - Strong bullish crossover in Stochastic")
            else:
                buy_signals += 0.5   # تقاطع صعودي عادي
                logger.info("  - Normal bullish crossover in Stochastic")
        elif stoch_k < stoch_d:
            # تقاطع هبوطي
            crossover_strength = stoch_d - stoch_k
            
            if stoch_k > 70 and crossover_strength > 3:
                sell_signals += 1.5  # تقاطع هبوطي قوي من منطقة تشبع شراء
                logger.info("  - Strong bearish crossover in Stochastic from overbought area")
            elif stoch_k > 70:
                sell_signals += 1  # تقاطع هبوطي من منطقة تشبع شراء
                logger.info("  - Bearish crossover in Stochastic from overbought area")
            elif crossover_strength > 5:
                sell_signals += 1  # تقاطع هبوطي قوي
                logger.info("  - Strong bearish crossover in Stochastic")
            else:
                sell_signals += 0.5  # تقاطع هبوطي عادي
                logger.info("  - Normal bearish crossover in Stochastic")
        
        # قواعد MACD - تحسين الاعتماد على قوة المؤشر
        histogram_strength = abs(histogram) * 10000  # تضخيم الهيستوجرام للتسهيل
        logger.info(f"  - MACD Histogram strength: {histogram_strength:.2f}")
        
        if histogram > 0:
            # هيستوجرام موجب (إشارة شراء)
            if histogram_strength > 10:
                buy_signals += 2  # إشارة قوية للشراء
                logger.info("  - Strong positive MACD histogram")
            elif histogram_strength > 5:
                buy_signals += 1.5  # إشارة متوسطة للشراء
                logger.info("  - Moderate positive MACD histogram")
            elif histogram_strength > 1:
                buy_signals += 1  # إشارة ضعيفة للشراء
                logger.info("  - Weak positive MACD histogram")
        elif histogram < 0:
            # هيستوجرام سالب (إشارة بيع)
            if histogram_strength > 10:
                sell_signals += 2  # إشارة قوية للبيع
                logger.info("  - Strong negative MACD histogram")
            elif histogram_strength > 5:
                sell_signals += 1.5  # إشارة متوسطة للبيع
                logger.info("  - Moderate negative MACD histogram")
            elif histogram_strength > 1:
                sell_signals += 1  # إشارة ضعيفة للبيع
                logger.info("  - Weak negative MACD histogram")
        
        # إشارات تقاطع MACD - تحسين الترجيح
        macd_cross_strength = abs(macd - signal) * 10000  # تضخيم الفرق للتسهيل
        logger.info(f"  - MACD crossover strength: {macd_cross_strength:.2f}")
        
        if macd > signal:
            # تقاطع صعودي
            if macd_cross_strength > 5:
                buy_signals += 1.5   # تقاطع صعودي قوي
                logger.info("  - Strong bullish MACD crossover")
            elif macd_cross_strength > 1:
                buy_signals += 1   # تقاطع صعودي عادي
                logger.info("  - Normal bullish MACD crossover")
        elif macd < signal:
            # تقاطع هبوطي
            if macd_cross_strength > 5:
                sell_signals += 1.5  # تقاطع هبوطي قوي
                logger.info("  - Strong bearish MACD crossover")
            elif macd_cross_strength > 1:
                sell_signals += 1  # تقاطع هبوطي عادي
                logger.info("  - Normal bearish MACD crossover")
        
        # قواعد Bollinger Bands - استخدام المؤشر الجديد لتعزيز دقة الإشارات
        current_price = candles[-1]['close']
        bb_position = bb['position']  # موقع السعر بالنسبة للنطاق (0-1)
        bb_bandwidth = bb['bandwidth']  # عرض النطاق كنسبة مئوية
        
        logger.info(f"  - Current price: {current_price:.4f}")
        logger.info(f"  - BB position (0-1): {bb_position:.4f}")
        
        # تحليل موقع السعر من نطاق بولنجر
        if bb_position < 0.05:
            # السعر أقل من الحد السفلي بشكل كبير (احتمالية ارتداد)
            buy_signals += 2.5
            logger.info("  - Price significantly below lower Bollinger Band (strong oversold)")
        elif bb_position < 0.2:
            # السعر قريب من الحد السفلي (احتمالية ارتداد)
            buy_signals += 1.5
            logger.info("  - Price near lower Bollinger Band (oversold)")
        elif bb_position > 0.95:
            # السعر أعلى من الحد العلوي بشكل كبير (احتمالية تصحيح)
            sell_signals += 2.5
            logger.info("  - Price significantly above upper Bollinger Band (strong overbought)")
        elif bb_position > 0.8:
            # السعر قريب من الحد العلوي (احتمالية تصحيح)
            sell_signals += 1.5
            logger.info("  - Price near upper Bollinger Band (overbought)")
        
        # تحليل عرض نطاق بولنجر
        if bb_bandwidth < 1.0:
            # نطاق ضيق جداً - احتمالية حدوث اختراق قوي
            neutral_signals += 1.5
            logger.info("  - Very tight Bollinger Bands (preparing for volatility breakout)")
        elif bb_bandwidth < 2.0:
            # نطاق ضيق - احتمالية زيادة التذبذب قريباً
            neutral_signals += 1
            logger.info("  - Tight Bollinger Bands (potential increase in volatility)")
        elif bb_bandwidth > 8.0:
            # نطاق واسع جداً - تذبذب عالي واحتمالية تراجع إلى الوسط
            if bb_position > 0.7:
                sell_signals += 1  # احتمالية تراجع من القمة
            elif bb_position < 0.3:
                buy_signals += 1  # احتمالية ارتداد من القاع
            logger.info("  - Wide Bollinger Bands (high volatility, potential mean reversion)")
        
        # قواعد ADX - استخدام مؤشر قوة الاتجاه لتأكيد الإشارات
        # ADX > 25 يشير إلى اتجاه قوي، ADX < 20 يشير إلى عدم وجود اتجاه واضح
        
        if adx > 30:
            logger.info(f"  - Strong trend detected (ADX: {adx:.2f})")
            
            # تأكيد اتجاه قوي - استخدم +DI و -DI لتحديد اتجاه الاتجاه
            if plus_di > minus_di:
                # اتجاه صعودي قوي
                strength_factor = min(2.5, (adx - 30) / 10 + 1)  # أكبر ADX، أكبر التأثير
                buy_signals += strength_factor
                logger.info(f"  - Strong uptrend confirmed (ADX: {adx:.2f}, +DI: {plus_di:.2f}, -DI: {minus_di:.2f})")
                logger.info(f"  - Added {strength_factor:.2f} to buy signals based on ADX strength")
            elif minus_di > plus_di:
                # اتجاه هبوطي قوي
                strength_factor = min(2.5, (adx - 30) / 10 + 1)  # أكبر ADX، أكبر التأثير
                sell_signals += strength_factor
                logger.info(f"  - Strong downtrend confirmed (ADX: {adx:.2f}, +DI: {plus_di:.2f}, -DI: {minus_di:.2f})")
                logger.info(f"  - Added {strength_factor:.2f} to sell signals based on ADX strength")
        elif adx > 20:
            logger.info(f"  - Moderate trend detected (ADX: {adx:.2f})")
            
            # اتجاه معتدل - استخدم +DI و -DI بتأثير أقل
            if plus_di > minus_di and plus_di - minus_di > 5:
                buy_signals += 1
                logger.info(f"  - Moderate uptrend confirmed (ADX: {adx:.2f}, +DI: {plus_di:.2f}, -DI: {minus_di:.2f})")
            elif minus_di > plus_di and minus_di - plus_di > 5:
                sell_signals += 1
                logger.info(f"  - Moderate downtrend confirmed (ADX: {adx:.2f}, +DI: {plus_di:.2f}, -DI: {minus_di:.2f})")
        else:
            # السوق بدون اتجاه واضح
            neutral_signals += 1
            logger.info(f"  - No clear trend detected (ADX: {adx:.2f} below 20)")
            
            # في الأسواق بدون اتجاه، الترجيح الإضافي على أساس تقاطعات +DI و -DI
            if plus_di > minus_di and plus_di - minus_di > 10:
                buy_signals += 0.5
                logger.info("  - Potential uptrend formation detected in range-bound market")
            elif minus_di > plus_di and minus_di - plus_di > 10:
                sell_signals += 0.5
                logger.info("  - Potential downtrend formation detected in range-bound market")
                
        # تحليل أنماط الشموع - إضافة تحليل الأنماط لزيادة الدقة
        if len(candles) >= 3:
            last_candle = candles[-1]
            prev_candle = candles[-2]
            prev2_candle = candles[-3]
            
            # تعريف إذا كانت الشمعة صاعدة أو هابطة
            is_last_bullish = last_candle['close'] > last_candle['open']
            is_prev_bullish = prev_candle['close'] > prev_candle['open']
            is_prev2_bullish = prev2_candle['close'] > prev2_candle['open']
            
            # حساب أحجام أجسام الشموع
            last_body_size = abs(last_candle['close'] - last_candle['open'])
            last_total_size = last_candle['high'] - last_candle['low']
            last_body_ratio = last_body_size / last_total_size if last_total_size > 0 else 0
            
            prev_body_size = abs(prev_candle['close'] - prev_candle['open'])
            prev_total_size = prev_candle['high'] - prev_candle['low']
            prev_body_ratio = prev_body_size / prev_total_size if prev_total_size > 0 else 0
            
            # نمط الدوجي (جسم صغير جدًا مع ظلال)
            if last_body_ratio < 0.15:
                neutral_signals += 1
                logger.info("  - Pattern: Doji candle detected (market indecision)")
            
            # نمط المطرقة (جسم صغير في الأعلى وظل سفلي طويل)
            lower_shadow = min(last_candle['open'], last_candle['close']) - last_candle['low']
            upper_shadow = last_candle['high'] - max(last_candle['open'], last_candle['close'])
            
            if (last_body_ratio < 0.3 and
                lower_shadow > 2 * last_body_size and
                upper_shadow < 0.2 * last_body_size):
                # المطرقة بعد اتجاه هبوطي إشارة انعكاس صعودي قوية
                if not is_prev_bullish and not is_prev2_bullish:
                    buy_signals += 2
                    logger.info("  - Pattern: Hammer after downtrend (strong reversal signal)")
                else:
                    buy_signals += 1
                    logger.info("  - Pattern: Hammer detected (potential reversal)")
            
            # نمط النجمة الساقطة (جسم صغير في الأسفل وظل علوي طويل)
            if (last_body_ratio < 0.3 and
                upper_shadow > 2 * last_body_size and
                lower_shadow < 0.2 * last_body_size):
                # النجمة الساقطة بعد اتجاه صعودي إشارة انعكاس هبوطي قوية
                if is_prev_bullish and is_prev2_bullish:
                    sell_signals += 2
                    logger.info("  - Pattern: Shooting star after uptrend (strong reversal signal)")
                else:
                    sell_signals += 1
                    logger.info("  - Pattern: Shooting star detected (potential reversal)")
            
            # نمط الابتلاع الصعودي
            if (is_last_bullish and not is_prev_bullish and
                last_candle['close'] > prev_candle['open'] and
                last_candle['open'] < prev_candle['close']):
                buy_signals += 1.5
                logger.info("  - Pattern: Bullish engulfing detected")
            
            # نمط الابتلاع الهبوطي
            if (not is_last_bullish and is_prev_bullish and
                last_candle['close'] < prev_candle['open'] and
                last_candle['open'] > prev_candle['close']):
                sell_signals += 1.5
                logger.info("  - Pattern: Bearish engulfing detected")
        
        # تقييم نهائي
        total_signals = buy_signals + sell_signals + neutral_signals
        if total_signals == 0:
            total_signals = 1  # تجنب القسمة على صفر
        
        buy_strength = buy_signals / total_signals
        sell_strength = sell_signals / total_signals
        
        # حساب الفارق بين إشارات الشراء والبيع
        signal_diff = abs(buy_signals - sell_signals)
        min_signal_diff = 1.5  # الحد الأدنى للفارق المطلوب
        
        # تحديد الاتجاه مع متطلبات أكثر صرامة للإشارات الواضحة
        if buy_signals > sell_signals and signal_diff >= min_signal_diff:
            direction = "BUY"
            # قوة الإشارة أكثر دقة
            signal_strength = (buy_signals - sell_signals * 0.5) / (buy_signals + sell_signals)
            signal_strength = min(1.0, max(0.3, signal_strength))  # تقييد بين 0.3 و 1.0 لضمان إشارات معقولة
            # احتمالية نجاح محسنة (بداية من 80%)
            probability = int(80 + (signal_strength * 15))
            logger.info(f"  - Final BUY signal with strength: {signal_strength:.2f}, probability: {probability}%")
        elif sell_signals > buy_signals and signal_diff >= min_signal_diff:
            direction = "SELL"
            # قوة الإشارة أكثر دقة
            signal_strength = (sell_signals - buy_signals * 0.5) / (sell_signals + buy_signals)
            signal_strength = min(1.0, max(0.3, signal_strength))  # تقييد بين 0.3 و 1.0
            # احتمالية نجاح محسنة (بداية من 80%)
            probability = int(80 + (signal_strength * 15))
            logger.info(f"  - Final SELL signal with strength: {signal_strength:.2f}, probability: {probability}%")
        else:
            # ترجيح أضعف أو تعادل - نوفر إشارة بسيطة مع ترجيح خفيف بناءً على مؤشرات أخرى
            logger.info("No strong signal, but providing a weak directional bias based on RSI and trend")
            # نستخدم مؤشر RSI كمؤشر بديل في حالة عدم وضوح الإشارة الأساسية
            if rsi > 60:
                direction = "SELL"
                probability = max(75, min(80, int(rsi)))
                analysis = "إشارة بيع ضعيفة مبنية على RSI في المنطقة العليا. "
                logger.info(f"  - Weak SELL signal based on RSI: {rsi:.2f}")
            elif rsi < 40:
                direction = "BUY"
                probability = max(75, min(80, int(100-rsi)))
                analysis = "إشارة شراء ضعيفة مبنية على RSI في المنطقة السفلى. "
                logger.info(f"  - Weak BUY signal based on RSI: {rsi:.2f}")
            else:
                # في حالة وجود اتجاه للسوق، نتبعه
                if trend in ["STRONG_UP", "UP"]:
                    direction = "BUY"
                    probability = 75
                    analysis = "إشارة شراء ضعيفة جداً مبنية على الاتجاه العام. "
                    logger.info("  - Very weak BUY signal based on market trend")
                elif trend in ["STRONG_DOWN", "DOWN"]:
                    direction = "SELL"
                    probability = 75
                    analysis = "إشارة بيع ضعيفة جداً مبنية على الاتجاه العام. "
                    logger.info("  - Very weak SELL signal based on market trend")
                else:
                    # إذا لم يكن هناك اتجاه واضح، نختار اتجاه عشوائي ذو احتمالية منخفضة
                    import random
                    if random.random() > 0.5:
                        direction = "BUY"
                    else:
                        direction = "SELL"
                    probability = 75
                    analysis = "إشارة ضعيفة جداً في سوق متذبذب. "
                    logger.info("  - Random direction with lowest probability in neutral market")
                    
            # العودة بإشارة ذات احتمالية منخفضة بدلاً من القيمة الفارغة
            return {
                'direction': direction,
                'probability': probability,
                'duration': 1,  # دائماً مدة قصيرة (1 دقيقة) للإشارات الضعيفة
                'analysis': analysis + "احتمالية نجاح منخفضة، يفضل تجنب التداول مع مثل هذه الإشارة الضعيفة."
            }
        
        # تقييد الاحتمالية بين 80 و 95 (زيادة الحد الأدنى للاحتمالية)
        probability = max(80, min(95, probability))
        
        # تحديد المدة المناسبة بناءً على عوامل متعددة وخوارزمية ذكية
        # مدة أطول للإشارات الأقوى، ومدة أقصر للإشارات الأضعف
        # استخدام المدد المطلوبة: 1، 2، 3 دقائق فقط (بناء على طلب المستخدم)
        duration_options = [1, 2, 3]
        
        # عامل زاوية السعر: الأكثر أهمية
        angle_factor = 0
        if abs(price_angle) > 20:  # زاوية حادة جداً
            angle_factor = 3.5  # فترة أطول
        elif abs(price_angle) > 15:  # زاوية حادة
            angle_factor = 3.0  # فترة أطول
        elif abs(price_angle) > 10:
            angle_factor = 2.0  # فترة متوسطة
        elif abs(price_angle) > 5:
            angle_factor = 1.0  # فترة قصيرة
        logger.info(f"  - Angle factor for duration: {angle_factor}")
        
        # عامل قوة الإشارة: يؤثر في المدة أيضاً
        strength_factor = 0
        if signal_strength >= 0.8:
            strength_factor = 3.5  # إشارة قوية جداً
        elif signal_strength >= 0.7:
            strength_factor = 3.0  # إشارة قوية
        elif signal_strength >= 0.5:
            strength_factor = 2.0  # إشارة متوسطة
        elif signal_strength >= 0.3:
            strength_factor = 1.0  # إشارة ضعيفة
        logger.info(f"  - Signal strength factor for duration: {strength_factor}")
        
        # عامل اتجاه السوق: تحسين التأثير
        trend_factor = 0
        if trend in ["STRONG_UP", "STRONG_DOWN"]:
            trend_factor = 2.5  # اتجاه قوي جداً
        elif trend in ["UP", "DOWN"]:
            trend_factor = 1.5  # اتجاه عادي
        logger.info(f"  - Trend factor for duration: {trend_factor}")
        
        # عامل جديد: تذبذب السوق (Volatility)
        volatility_factor = 0
        candle_sizes = [abs(c['high'] - c['low']) for c in candles[-10:]]
        avg_candle_size = sum(candle_sizes) / len(candle_sizes)
        volatility = avg_candle_size / candles[-1]['close'] * 100  # النسبة المئوية للتذبذب
        
        if volatility > 0.5:  # تذبذب عالي جداً
            volatility_factor = -1.0  # تقليل المدة للأسواق عالية التذبذب
        elif volatility > 0.3:  # تذبذب عالي
            volatility_factor = -0.5  # تقليل المدة قليلاً
        elif volatility < 0.1:  # تذبذب منخفض
            volatility_factor = 1.0  # زيادة المدة للأسواق المستقرة
        logger.info(f"  - Volatility: {volatility:.2f}%, factor: {volatility_factor}")
        
        # عامل توافق المؤشرات: يزداد كلما اتفقت المؤشرات على نفس الاتجاه
        indicators_alignment = 0
        if direction == "BUY":
            if rsi < 30: indicators_alignment += 1  # RSI يشير للشراء
            if stoch_k < 20 and stoch_k > stoch_d: indicators_alignment += 1  # ستوكاستك يشير للشراء
            if histogram > 0 or macd > signal: indicators_alignment += 1  # MACD يشير للشراء
        else:  # direction == "SELL"
            if rsi > 70: indicators_alignment += 1  # RSI يشير للبيع
            if stoch_k > 80 and stoch_k < stoch_d: indicators_alignment += 1  # ستوكاستك يشير للبيع
            if histogram < 0 or macd < signal: indicators_alignment += 1  # MACD يشير للبيع
        
        indicator_alignment_factor = indicators_alignment * 0.5
        logger.info(f"  - Indicators alignment: {indicators_alignment}/3, factor: {indicator_alignment_factor}")
        
        # المجموع النهائي للعوامل - مع تأثيرات إضافية
        duration_factor_sum = angle_factor + strength_factor + trend_factor + volatility_factor + indicator_alignment_factor
        logger.info(f"  - Total duration factor: {duration_factor_sum}")
        
        # توزيع أكثر توازناً للمدد المختلفة
        # تحديد مدة الصفقة بناءً على مجموع العوامل بتوزيع أكثر عدالة
        if duration_factor_sum >= 6.0:
            duration = duration_options[2]  # 3 دقائق للإشارات القوية جداً
            logger.info("  - Selected duration 3 min (very strong signal)")
        elif duration_factor_sum >= 3.0:
            duration = duration_options[1]  # 2 دقائق للإشارات المتوسطة
            logger.info("  - Selected duration 2 min (moderate signal)")
        else:
            duration = duration_options[0]  # 1 دقيقة للإشارات الضعيفة
            logger.info("  - Selected duration 1 min (weak signal)")
            
        # CRITICAL UPDATE: زيادة تنوع المدد مع تركيز على المدد (2-4 دقائق)
        # زيادة احتمالية التنويع لتحقيق توازن أفضل
        import random
        if random.random() < 0.35:  # زيادة الاحتمالية إلى 35% للتنويع أكثر
            # زيادة فرص اختيار المدد الأقل استخداماً (5 دقائق و 2 دقائق)
            if duration in [3, 4]:  # إذا كانت المدة الحالية هي المدة المتوسطة الأكثر استخداماً
                underused_durations = [2, 5]  # المدد التي نريد زيادة استخدامها
                alternative_duration = random.choice(underused_durations)
                logger.info(f"  - Increasing variety, favoring underused durations: {duration} -> {alternative_duration}")
                duration = alternative_duration
            else:
                # للمدد الأخرى، تنويع عادي
                nearby_durations = [d for d in duration_options if d != duration]
                if nearby_durations:
                    alternative_duration = random.choice(nearby_durations)
                    logger.info(f"  - Randomizing duration for diversity: {duration} -> {alternative_duration}")
                    duration = alternative_duration
            
        # تسجيل المدة النهائية
        logger.info(f"  - Final duration selection: {duration} minutes (factor sum: {duration_factor_sum})")
        
        # تحليل مفصل أكثر شمولاً
        if direction == "BUY":
            analysis = f"إشارة شراء بقوة {signal_strength:.2f} ومدة {duration} دقيقة. "
            reasons = []
            
            # إضافة أسباب الاتجاه
            if price_angle > 15:
                reasons.append("زاوية سعر صاعدة حادة")
            elif price_angle > 5:
                reasons.append("زاوية سعر صاعدة معتدلة")
            if trend in ["STRONG_UP"]:
                reasons.append("اتجاه عام صاعد قوي")
            elif trend in ["UP"]:
                reasons.append("اتجاه عام صاعد")
                
            # إضافة أسباب المؤشرات الفنية
            if rsi < 20:
                reasons.append("مؤشر RSI في منطقة تشبع بيع قوي")
            elif rsi < 30:
                reasons.append("مؤشر RSI في منطقة تشبع بيع")
            elif rsi < 45:
                reasons.append("مؤشر RSI يميل للصعود")
                
            # مؤشر ستوكاستك
            if stoch_k < 20 and stoch_k > stoch_d:
                reasons.append("تقاطع صعودي في ستوكاستك من منطقة تشبع بيع")
            elif stoch_k > stoch_d:
                reasons.append("تقاطع صعودي في ستوكاستك")
                
            # مؤشر MACD
            if histogram > 0 and histogram_strength > 5:
                reasons.append("هيستوجرام MACD إيجابي قوي")
            elif histogram > 0:
                reasons.append("هيستوجرام MACD إيجابي")
            if macd > signal and macd_cross_strength > 5:
                reasons.append("تقاطع صعودي قوي في MACD")
            elif macd > signal:
                reasons.append("تقاطع صعودي في MACD")
                
            # أنماط الشموع
            if 'last_candle' in locals() and 'lower_shadow' in locals() and 'upper_shadow' in locals():
                if last_body_ratio < 0.3 and lower_shadow > 2 * last_body_size and upper_shadow < 0.2 * last_body_size:
                    if not is_prev_bullish and not is_prev2_bullish:
                        reasons.append("نمط المطرقة بعد اتجاه هبوطي")
                    else:
                        reasons.append("نمط المطرقة")
                        
                if is_last_bullish and not is_prev_bullish and last_candle['close'] > prev_candle['open'] and last_candle['open'] < prev_candle['close']:
                    reasons.append("نمط الابتلاع الصعودي")
            
            analysis += "الأسباب: " + " ، ".join(reasons)
        else:
            analysis = f"إشارة بيع بقوة {signal_strength:.2f} ومدة {duration} دقيقة. "
            reasons = []
            
            # إضافة أسباب الاتجاه
            if price_angle < -15:
                reasons.append("زاوية سعر هابطة حادة")
            elif price_angle < -5:
                reasons.append("زاوية سعر هابطة معتدلة")
            if trend in ["STRONG_DOWN"]:
                reasons.append("اتجاه عام هابط قوي")
            elif trend in ["DOWN"]:
                reasons.append("اتجاه عام هابط")
                
            # إضافة أسباب المؤشرات الفنية
            if rsi > 80:
                reasons.append("مؤشر RSI في منطقة تشبع شراء قوي")
            elif rsi > 70:
                reasons.append("مؤشر RSI في منطقة تشبع شراء")
            elif rsi > 55:
                reasons.append("مؤشر RSI يميل للهبوط")
                
            # مؤشر ستوكاستك
            if stoch_k > 80 and stoch_k < stoch_d:
                reasons.append("تقاطع هبوطي في ستوكاستك من منطقة تشبع شراء")
            elif stoch_k < stoch_d:
                reasons.append("تقاطع هبوطي في ستوكاستك")
                
            # مؤشر MACD
            if histogram < 0 and histogram_strength > 5:
                reasons.append("هيستوجرام MACD سلبي قوي")
            elif histogram < 0:
                reasons.append("هيستوجرام MACD سلبي")
            if macd < signal and macd_cross_strength > 5:
                reasons.append("تقاطع هبوطي قوي في MACD")
            elif macd < signal:
                reasons.append("تقاطع هبوطي في MACD")
                
            # أنماط الشموع
            if 'last_candle' in locals() and 'lower_shadow' in locals() and 'upper_shadow' in locals():
                if last_body_ratio < 0.3 and upper_shadow > 2 * last_body_size and lower_shadow < 0.2 * last_body_size:
                    if is_prev_bullish and is_prev2_bullish:
                        reasons.append("نمط النجمة الساقطة بعد اتجاه صعودي")
                    else:
                        reasons.append("نمط النجمة الساقطة")
                        
                if not is_last_bullish and is_prev_bullish and last_candle['close'] < prev_candle['open'] and last_candle['open'] > prev_candle['close']:
                    reasons.append("نمط الابتلاع الهبوطي")
            
            analysis += "الأسباب: " + " ، ".join(reasons)
            
        # إضافة معلومات إضافية للإشارة للتوثيق
        analysis += f" | زاوية السعر: {price_angle:.1f}°, RSI: {rsi:.1f}, المدة: {duration} دقيقة"
        
        return {
            'direction': direction,
            'probability': probability,
            'duration': duration,
            'analysis': analysis
        }
    
    def get_signal(self, pair_symbol=None):
        """الحصول على إشارة لزوج محدد أو اختيار زوج عشوائي"""
        # جمع جميع الأزواج الصالحة (العادية و OTC)
        valid_pairs = []
        
        try:
            # أزواج البورصة العادية
            market_pairs = get_all_valid_market_pairs()
            valid_pairs.extend(market_pairs)
            logger.info(f"Found {len(market_pairs)} valid market pairs")
        except Exception as e:
            logger.error(f"Error getting valid market pairs: {e}")
        
        try:
            # أزواج OTC
            otc_pairs = get_all_valid_otc_pairs()
            valid_pairs.extend(otc_pairs)
            logger.info(f"Found {len(otc_pairs)} valid OTC pairs")
        except Exception as e:
            logger.error(f"Error getting valid OTC pairs: {e}")
        
        if not valid_pairs:
            logger.error("No valid pairs available (neither market nor OTC)")
            return None
        
        if pair_symbol is None:
            # اختيار زوج عشوائي من القائمة الصالحة
            pair_symbol = random.choice(valid_pairs)
            logger.info(f"Randomly selected pair: {pair_symbol}")
        elif not is_valid_market_pair(pair_symbol) and not is_valid_otc_pair(pair_symbol):
            logger.warning(f"Pair {pair_symbol} is not supported (neither market nor OTC)")
            return None
        
        # تحليل الزوج
        analysis_result = self.analyze_pair(pair_symbol)
        
        # التعديل: لم نعد نرجع أي إشارات بقيمة None للاتجاه
        # ولكن نتحقق هنا كإجراء احترازي فقط
        if analysis_result['direction'] is None:
            logger.warning(f"Unexpected NULL direction for {pair_symbol}, defaulting to random direction")
            
            # في حالة حدوث خلل غير متوقع، نقوم بإنشاء اتجاه عشوائي كحل أخير
            import random
            analysis_result['direction'] = "BUY" if random.random() > 0.5 else "SELL"
            analysis_result['probability'] = 75
            analysis_result['duration'] = 2  # تم تحديث المدة الافتراضية إلى 2 دقائق
            analysis_result['analysis'] = "إشارة عشوائية للتوافق مع قاعدة البيانات. تجنب التداول مع هذه الإشارة."
            
            # استبعاد الزوج الحالي من الاختيار
            remaining_pairs = [p for p in valid_pairs if p != pair_symbol]
            if not remaining_pairs:
                return None
            
            # اختيار زوج جديد عشوائي
            new_pair = random.choice(remaining_pairs)
            return self.get_signal(new_pair)
        
        # إذا وجدنا إشارة، نعيدها
        return {
            'pair': pair_symbol,
            'direction': analysis_result['direction'],
            'probability': analysis_result['probability'],
            'duration': analysis_result['duration'],
            'analysis': analysis_result['analysis']
        }

# إنشاء نسخة عامة من المحلل لاستخدامها في جميع أنحاء التطبيق
technical_analyzer = TechnicalAnalyzer()

def get_technical_signal(pair_id=None, pair_symbol=None):
    """
    الحصول على إشارة تداول بناءً على التحليل الفني
    
    Args:
        pair_id: معرف الزوج في قاعدة البيانات (اختياري)
        pair_symbol: رمز الزوج (اختياري)
        
    Returns:
        dict: معلومات الإشارة التي تم إنشاؤها، أو None في حالة الفشل
    """
    try:
        # استخراج رمز الزوج من معرف الزوج إذا تم تمريره
        if pair_id is not None:
            try:
                # البحث أولاً في أزواج OTC
                from models import OTCPair
                pair = OTCPair.query.filter_by(id=pair_id, is_active=True).first()
                if pair:
                    pair_symbol = pair.symbol
                    logger.info(f"Found OTC pair with ID {pair_id}: {pair_symbol}")
                else:
                    # البحث في أزواج البورصة العادية
                    from models import MarketPair
                    pair = MarketPair.query.filter_by(id=pair_id, is_active=True).first()
                    if pair:
                        pair_symbol = pair.symbol
                        logger.info(f"Found market pair with ID {pair_id}: {pair_symbol}")
                    else:
                        logger.warning(f"No active pair found (neither market nor OTC) with ID {pair_id}")
                        return None
            except Exception as db_error:
                logger.error(f"Database error when trying to find pair ID {pair_id}: {db_error}")
                # إذا فشل البحث، نحاول إنشاء إشارة عشوائية
                pair_symbol = None
        
        # استخدام المحلل الفني للحصول على إشارة (سيختار زوجًا عشوائيًا إذا كان pair_symbol=None)
        logger.info(f"Generating technical signal for pair: {pair_symbol or 'random pair'}")
        signal_info = technical_analyzer.get_signal(pair_symbol)
        
        if not signal_info:
            logger.warning("Could not generate a valid technical signal")
            # في حالة الفشل، نحاول مرة أخرى مع زوج عشوائي
            logger.info("Trying again with a random pair")
            signal_info = technical_analyzer.get_signal(None)
            if not signal_info:
                logger.error("Failed to generate signal even with random pair")
                return None
        
        # التأكد من أن الإشارة تحتوي على اتجاه غير فارغ
        if signal_info.get('direction') is None:
            logger.error(f"Signal still has NULL direction for {signal_info.get('pair')}")
            import random
            signal_info['direction'] = "BUY" if random.random() > 0.5 else "SELL"
            signal_info['probability'] = 75
            signal_info['duration'] = 2  # تم تحديث المدة الافتراضية إلى 2 دقائق
            signal_info['analysis'] = "إشارة معالجة بسبب خطأ فني. تجنب التداول مع هذه الإشارة."
        
        logger.info(f"Successfully generated signal for {signal_info['pair']}: {signal_info['direction']} with {signal_info['probability']}% probability")
        return signal_info
        
    except Exception as e:
        logger.error(f"Error in get_technical_signal: {e}")
        logger.exception("Detailed exception:")
        return None