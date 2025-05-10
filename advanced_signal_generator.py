"""
مولد الإشارات المتقدم
يجمع بين جميع أنظمة التحليل والتقييم والتصفية لإنتاج إشارات عالية الدقة
"""
import logging
import math
import random
import time
from datetime import datetime, timedelta

from technical_analyzer import TechnicalAnalyzer
from multi_timeframe_analyzer import validate_signal, get_trading_recommendation
from signal_filter import get_high_quality_signal, generate_safe_signal
from confidence_evaluator import enhance_signal_with_confidence
from pocket_option_otc_pairs import get_all_valid_pairs, is_valid_pair

# إعداد سجل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedSignalGenerator:
    """مولد إشارات متقدم يجمع بين جميع أنظمة التحليل والتصفية والتقييم"""
    
    def __init__(self):
        """تهيئة مولد الإشارات المتقدم"""
        self.technical_analyzer = TechnicalAnalyzer()
        
        # إعدادات الإشارات
        self.min_probability = 92  # الحد الأدنى للاحتمالية
        self.preferred_durations = [1, 5, 2, 3]  # المدد المفضلة بالترتيب (تحديث: تفضيل المدد 1 و 5 دقائق)
        
        # تحديث: زيادة احتمالية المدد القصيرة والطويلة وتقليل احتمالية المدد المتوسطة
        self.duration_probabilities = {
            1: 0.35,  # 35% للمدة 1 دقيقة
            2: 0.15,  # 15% للمدة 2 دقيقة
            3: 0.15,  # 15% للمدة 3 دقائق
            5: 0.35,  # 35% للمدة 5 دقائق
        }
        
        # إعدادات الإخراج
        self.include_detailed_analysis = True  # تضمين تحليل مفصل
        self.include_confidence_metrics = True  # تضمين مقاييس الثقة
        
        # إحصائيات
        self.total_signals_generated = 0
        self.high_quality_signals = 0
        self.rejected_signals = 0
    
    def generate_premium_signal(self, pair_symbol=None, force_generation=False):
        """
        توليد إشارة ممتازة عالية الدقة
        
        Args:
            pair_symbol (str, optional): رمز الزوج المراد تحليله، أو None لاختيار زوج عشوائي
            force_generation (bool): إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
            
        Returns:
            dict: معلومات الإشارة الممتازة، أو None في حالة عدم وجود إشارة جيدة
        """
        logger.info(f"Generating premium signal for " + (pair_symbol if pair_symbol else "random pair"))
        
        # محاولة إنشاء إشارة متعددة الأطر الزمنية عالية الجودة
        logger.info("Attempt 1: Generating multi-timeframe high-quality signal")
        
        # استخدام محلل الإطارات الزمنية المتعددة للحصول على توصية تداول
        signal = None
        if pair_symbol:
            try:
                recommendation = get_trading_recommendation(pair_symbol)
                
                # التحقق من وجود توصية صالحة
                if recommendation and isinstance(recommendation, dict) and recommendation.get('direction') in ['BUY', 'SELL']:
                    logger.info(f"✅ تم الحصول على توصية تداول عبر محلل الإطارات المتعددة: {recommendation['direction']} للزوج {pair_symbol}")
                    
                    # تحويل التوصية إلى إشارة
                    signal = {
                        'pair': pair_symbol,
                        'direction': recommendation['direction'],
                        'probability': recommendation.get('probability', 90),
                        'duration': random.choice(self.preferred_durations),
                        'analysis': f"تحليل متعدد الإطارات الزمنية - {recommendation.get('reason', 'توصية مؤكدة')}",
                        'sr_info': 'تم التحقق من مناطق الدعم والمقاومة'
                    }
                else:
                    logger.warning(f"❌ لا توجد توصية واضحة من محلل الإطارات المتعددة للزوج {pair_symbol}")
            except Exception as e:
                logger.error(f"❌ خطأ أثناء الحصول على توصية التداول: {e}")
        else:
            logger.warning("⚠️ لم يتم تحديد زوج للتحليل")
        
        # إذا لم تنجح، نحاول استخدام إشارة مصفاة مباشرة
        if not signal:
            logger.info("Attempt 2: Generating filtered standard signal")
            signal = get_high_quality_signal(pair_symbol=pair_symbol)
        
        # إذا لم تنجح أيضاً، نحاول استخدام آلية توليد إشارة آمنة
        if not signal and force_generation:
            logger.info("Attempt 3: Generating safe signal (fallback)")
            signal = generate_safe_signal()
        
        # إذا لم نحصل على إشارة، نعيد None
        if not signal:
            self.rejected_signals += 1
            logger.info("Failed to generate a premium signal that meets quality criteria")
            return None
        
        # تعزيز الإشارة بمعلومات الثقة
        try:
            if signal is not None:
                # التحقق من وجود الدالة
                if 'enhance_signal_with_confidence' in globals():
                    signal = enhance_signal_with_confidence(signal)
                else:
                    # إذا لم تكن الدالة موجودة، نضيف معلومات الثقة داخلياً
                    if 'probability' in signal and 'confidence_level' not in signal:
                        signal['confidence_level'] = self._determine_confidence_level(signal['probability'])
            else:
                logger.warning("لا يمكن تعزيز الإشارة بمعلومات الثقة: الإشارة غير متوفرة")
        except Exception as e:
            logger.error(f"خطأ أثناء تعزيز الإشارة بمعلومات الثقة: {e}")
        
        # التحقق من الحد الأدنى للاحتمالية
        if signal is not None:
            probability = signal.get('probability', 0)
            if probability < self.min_probability and not force_generation:
                self.rejected_signals += 1
                logger.info(f"Generated signal rejected: probability {probability}% below minimum {self.min_probability}%")
                return None
        else:
            self.rejected_signals += 1
            logger.info("No signal generated to evaluate")
            return None
        
        # تطبيق تحسينات إضافية على الإشارة
        signal = self._enhance_signal(signal)
        
        # تحديث الإحصائيات
        self.total_signals_generated += 1
        self.high_quality_signals += 1 if signal.get('probability', 0) >= 92 else 0
        
        direction = signal.get('direction', 'UNKNOWN')
        pair = signal.get('pair', 'UNKNOWN')
        probability = signal.get('probability', 0)
        duration = signal.get('duration', 0)
        
        logger.info(f"Successfully generated premium signal: {direction} {pair} with {probability}% confidence, {duration} minutes duration")
        
        return signal
    
    def _enhance_signal(self, signal):
        """
        تطبيق تحسينات إضافية على الإشارة
        
        Args:
            signal (dict): معلومات الإشارة الأصلية
            
        Returns:
            dict: الإشارة المحسنة
        """
        # نسخة من الإشارة الأصلية
        enhanced_signal = signal.copy()
        
        # التأكد من استخدام المدد المفضلة
        if 'duration' in enhanced_signal:
            current_duration = enhanced_signal['duration']
            # إذا كانت المدة الحالية ليست من المدد المفضلة
            if current_duration not in self.preferred_durations:
                # تحديث: استخدام نظام الاحتمال لاختيار المدة المناسبة
                # بدلاً من اختيار أقرب مدة، نختار مدة عشوائية بناءً على التوزيع
                import random
                
                # قائمة المدد مع وزنها النسبي
                durations = list(self.duration_probabilities.keys())
                weights = list(self.duration_probabilities.values())
                
                # اختيار مدة عشوائية بناءً على الاحتمالات المحددة
                selected_duration = random.choices(durations, weights=weights, k=1)[0]
                
                logger.info(f"Adjusting duration from {current_duration} to selected duration {selected_duration} (based on probability distribution)")
                enhanced_signal['duration'] = selected_duration
        
        # تحسين التحليل المفصل إذا كان مطلوباً
        if self.include_detailed_analysis and 'analysis' in enhanced_signal:
            enhanced_signal['analysis'] = self._enhance_analysis(enhanced_signal)
        
        # إضافة معلومات الثقة إذا كانت مطلوبة
        if self.include_confidence_metrics and 'probability' in enhanced_signal:
            if 'confidence_level' not in enhanced_signal:
                # تحديد مستوى الثقة
                confidence_level = self._determine_confidence_level(enhanced_signal['probability'])
                enhanced_signal['confidence_level'] = confidence_level
        
        # إضافة طابع زمني للإشارة
        enhanced_signal['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # إضافة صورة الرسم البياني للإشارة
        try:
            from static.images.charts.generate_chart import generate_price_chart
            # تأكد من وجود زوج العملة واتجاه الإشارة
            if 'pair' in enhanced_signal and 'direction' in enhanced_signal:
                # إنشاء دليل حفظ الصور إذا لم يكن موجوداً
                import os
                charts_dir = os.path.join('static', 'images', 'charts', 'signals')
                os.makedirs(charts_dir, exist_ok=True)
                
                # إنشاء اسم ملف فريد للصورة
                now = datetime.now()
                filename = f"{enhanced_signal['pair'].replace('/', '_')}_{enhanced_signal['direction']}_{now.strftime('%Y%m%d_%H%M%S')}.png"
                save_path = os.path.join(charts_dir, filename)
                
                # توليد الصورة وحفظها
                chart_path = generate_price_chart(enhanced_signal['pair'], enhanced_signal['direction'], save_path)
                
                # إضافة مسار الصورة إلى الإشارة
                enhanced_signal['chart_path'] = chart_path
                logger.info(f"تم إنشاء صورة الرسم البياني للإشارة: {chart_path}")
            else:
                logger.warning("لا يمكن إنشاء صورة الرسم البياني: زوج العملة أو الاتجاه غير متوفر في الإشارة")
        except Exception as e:
            logger.error(f"خطأ أثناء إنشاء صورة الرسم البياني: {e}")
            
        return enhanced_signal
    
    def _enhance_analysis(self, signal):
        """
        تحسين التحليل النصي للإشارة
        
        Args:
            signal (dict): معلومات الإشارة
            
        Returns:
            str: التحليل المحسن
        """
        analysis = signal.get('analysis', '')
        pair = signal.get('pair', '')
        direction = signal.get('direction', '')
        probability = signal.get('probability', 0)
        duration = signal.get('duration', 0)
        
        # إضافة معلومات إضافية لتوضيح الإشارة
        enhanced_parts = []
        
        # إضافة الزوج والاتجاه
        if pair and direction:
            direction_ar = 'شراء' if direction == 'BUY' else 'بيع'
            enhanced_parts.append(f"الزوج: {pair}, الاتجاه: {direction_ar}")
        
        # إضافة الاحتمالية والمدة
        if probability > 0 and duration > 0:
            enhanced_parts.append(f"احتمالية النجاح: {probability}%, المدة: {duration} دقيقة")
        
        # إضافة التحليل الأصلي
        if analysis:
            enhanced_parts.append(analysis)
        
        # إضافة نصائح التداول
        if direction == 'BUY':
            enhanced_parts.append("نصيحة للتداول: يفضل تعيين Take Profit قريب من مستوى المقاومة التالي. تحرك مع السوق وانتبه للإشارات المعاكسة المحتملة.")
        else:  # SELL
            enhanced_parts.append("نصيحة للتداول: يفضل تعيين Take Profit قريب من مستوى الدعم التالي. تحرك مع السوق وانتبه للإشارات المعاكسة المحتملة.")
        
        # دمج الأجزاء
        return " | ".join(enhanced_parts)
    
    def _determine_confidence_level(self, probability):
        """
        تحديد مستوى الثقة من الاحتمالية
        
        Args:
            probability (int): نسبة الاحتمالية
            
        Returns:
            str: وصف مستوى الثقة
        """
        if probability >= 95:
            return 'مرتفع جداً'
        elif probability >= 90:
            return 'مرتفع'
        elif probability >= 85:
            return 'متوسط'
        elif probability >= 80:
            return 'منخفض'
        else:
            return 'منخفض جداً'
    
    def get_signal_statistics(self):
        """
        الحصول على إحصائيات الإشارات
        
        Returns:
            dict: إحصائيات الإشارات
        """
        return {
            'total_signals': self.total_signals_generated,
            'high_quality_signals': self.high_quality_signals,
            'rejected_signals': self.rejected_signals,
            'acceptance_rate': (self.high_quality_signals / max(1, self.total_signals_generated)) * 100
        }

# مولد الإشارات المتقدم العالمي للاستخدام في جميع أنحاء التطبيق
advanced_signal_generator = AdvancedSignalGenerator()

def get_premium_signal(pair_id=None, pair_symbol=None, force_generation=False):
    """
    الحصول على إشارة ممتازة عالية الدقة
    
    Args:
        pair_id: معرف الزوج في قاعدة البيانات (اختياري)
        pair_symbol: رمز الزوج (اختياري)
        force_generation: إجبار إنشاء إشارة حتى لو لم تستوفِ المعايير
        
    Returns:
        dict: معلومات الإشارة الممتازة، أو None في حالة عدم وجود إشارة جيدة
    """
    # طباعة معلومات الزوج المطلوب للتوثيق
    if pair_symbol:
        logger.info(f"طلب إشارة للزوج: {pair_symbol}")
    else:
        logger.info("طلب إشارة لزوج عشوائي")
    
    # تحقق إذا كان الزوج من البورصة العادية أم OTC
    is_regular_market = pair_symbol and "-OTC" not in pair_symbol
    is_otc_market = pair_symbol and "-OTC" in pair_symbol
    
    if is_regular_market:
        logger.info(f"الزوج {pair_symbol} من البورصة العادية")
        # التحقق من أوقات التداول للزوج
        from market_pairs import is_pair_tradable_now
        if not is_pair_tradable_now(pair_symbol):
            logger.warning(f"الزوج {pair_symbol} غير متاح للتداول في الوقت الحالي")
            # إذا كان هناك إجبار على إنشاء الإشارة، نستمر. وإلا، نعيد None
            if not force_generation:
                return None
    
    # إنشاء الإشارة
    return advanced_signal_generator.generate_premium_signal(pair_symbol, force_generation)