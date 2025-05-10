"""
اختبار النظام الجديد المتقدم للأزواج OTC
"""

import logging
from advanced_signal_filter import AdvancedSignalFilter
from otc_analyzer_strategy import (
    is_otc_pair, is_preferred_otc_pair, 
    analyze_otc_timeframes, optimize_duration_for_otc,
    enhance_otc_signal, validate_otc_entry_time, 
    get_optimal_otc_pairs
)
from datetime import time

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_otc_pair_detection():
    """اختبار كشف أزواج OTC"""
    
    logger.info("اختبار كشف أزواج OTC...")
    
    # قائمة من الأزواج للاختبار
    pairs = [
        'EURUSD-OTC', 'EURUSD', 'GBPUSD-OTC', 'XAUUSD', 'XAUUSD-OTC', 'USDJPY-OTC'
    ]
    
    for pair in pairs:
        is_otc = is_otc_pair(pair)
        preferred = is_preferred_otc_pair(pair) if is_otc else False
        
        logger.info(f"الزوج: {pair} | OTC: {is_otc} | مفضل: {preferred}")

def test_analyze_otc_timeframes():
    """اختبار تحليل الإطارات الزمنية لأزواج OTC"""
    
    logger.info("اختبار تحليل الإطارات الزمنية لأزواج OTC...")
    
    # سيناريوهات مختلفة للاختبار
    test_cases = [
        {
            'name': "توافق كامل في جميع الإطارات",
            'm1': "BUY", 'm5': "BUY", 'm15': "BUY", 'signal': "BUY"
        },
        {
            'name': "توافق M1 و M5 فقط",
            'm1': "BUY", 'm5': "BUY", 'm15': "NEUTRAL", 'signal': "BUY"
        },
        {
            'name': "توافق M1 فقط مع تعارض M5 و M15",
            'm1': "BUY", 'm5': "SELL", 'm15': "SELL", 'signal': "BUY"
        },
        {
            'name': "تعارض كامل في جميع الإطارات",
            'm1': "SELL", 'm5': "SELL", 'm15': "SELL", 'signal': "BUY"
        }
    ]
    
    for case in test_cases:
        score, details = analyze_otc_timeframes(
            case['m1'], case['m5'], case['m15'], case['signal']
        )
        
        logger.info(f"الحالة: {case['name']}")
        logger.info(f"  النتيجة: {score:.2f}/100")
        logger.info(f"  التفاصيل: {details}")

def test_signal_enhancement():
    """اختبار تعزيز جودة إشارة OTC"""
    
    logger.info("اختبار تعزيز جودة إشارة OTC...")
    
    # إشارات مختلفة للاختبار
    test_signals = [
        {'pair': 'EURUSD-OTC', 'direction': 'BUY', 'probability': 75},
        {'pair': 'GBPUSD-OTC', 'direction': 'SELL', 'probability': 70},
        {'pair': 'XAUUSD-OTC', 'direction': 'BUY', 'probability': 80},
        {'pair': 'USDJPY', 'direction': 'SELL', 'probability': 75}  # ليس زوج OTC
    ]
    
    # درجات أساسية افتراضية
    basic_scores = [65, 68, 72, 70]
    
    for i, signal in enumerate(test_signals):
        is_otc = is_otc_pair(signal.get('pair', ''))
        basic_score = basic_scores[i]
        
        if is_otc:
            enhanced_score = enhance_otc_signal(signal, basic_score)
            logger.info(f"الزوج: {signal['pair']} | أساسي: {basic_score} | معزز: {enhanced_score:.2f}")
        else:
            logger.info(f"الزوج: {signal['pair']} | أساسي: {basic_score} | (ليس زوج OTC)")

def test_duration_optimization():
    """اختبار تحسين مدة التداول لأزواج OTC"""
    
    logger.info("اختبار تحسين مدة التداول لأزواج OTC...")
    
    # مدد مختلفة للاختبار
    durations = [1, 2, 3, 5, 10, 15]
    
    for duration in durations:
        optimized = optimize_duration_for_otc(duration)
        logger.info(f"المدة الأصلية: {duration} دقيقة | المدة المحسنة: {optimized} دقيقة")

def test_entry_time_validation():
    """اختبار التحقق من صلاحية وقت الدخول"""
    
    logger.info("اختبار التحقق من صلاحية وقت الدخول...")
    
    # أوقات مختلفة للاختبار
    test_times = [
        time(9, 30),   # وقت جيد (جلسة لندن)
        time(14, 0),   # وقت جيد (جلسة نيويورك)
        time(1, 0),    # وقت سيئ (منتصف الليل)
        time(12, 30),  # وقت سيئ (فترة الغداء الأوروبية)
        time(18, 0)    # وقت متوسط
    ]
    
    for entry_time in test_times:
        quality = validate_otc_entry_time(entry_time)
        logger.info(f"وقت الدخول: {entry_time.strftime('%H:%M')} | جودة الوقت: {quality:.2f}/100")

def test_optimal_pairs():
    """اختبار الحصول على قائمة أزواج OTC المفضلة"""
    
    logger.info("اختبار الحصول على قائمة أزواج OTC المفضلة...")
    
    optimal_pairs = get_optimal_otc_pairs()
    logger.info(f"عدد الأزواج المفضلة: {len(optimal_pairs)}")
    logger.info(f"الأزواج المفضلة: {optimal_pairs}")

def test_filter_integration():
    """اختبار تكامل مرشح الإشارات المتقدم مع نظام OTC"""
    
    logger.info("اختبار تكامل مرشح الإشارات المتقدم مع نظام OTC...")
    
    # إنشاء مرشح إشارات متقدم
    signal_filter = AdvancedSignalFilter()
    
    # إشارات للاختبار
    test_signals = [
        {
            'pair': 'EURUSD-OTC',
            'direction': 'BUY',
            'probability': '80%',
            'entry_time': '10:30',
            'expiry_time': '10:31',
            'duration': 1
        },
        {
            'pair': 'EURUSD',
            'direction': 'BUY',
            'probability': '80%',
            'entry_time': '10:30',
            'expiry_time': '10:31',
            'duration': 1
        }
    ]
    
    for signal in test_signals:
        is_accepted, quality_score, reason = signal_filter.filter_signal(signal)
        logger.info(f"الزوج: {signal['pair']} | قبول: {is_accepted} | الجودة: {quality_score:.2f} | السبب: {reason}")

def main():
    """الوظيفة الرئيسية للاختبار"""
    
    logger.info("=== بدء اختبار النظام المتقدم لأزواج OTC ===")
    
    # تشغيل الاختبارات
    test_otc_pair_detection()
    logger.info("-" * 50)
    
    test_analyze_otc_timeframes()
    logger.info("-" * 50)
    
    test_signal_enhancement()
    logger.info("-" * 50)
    
    test_duration_optimization()
    logger.info("-" * 50)
    
    test_entry_time_validation()
    logger.info("-" * 50)
    
    test_optimal_pairs()
    logger.info("-" * 50)
    
    test_filter_integration()
    logger.info("-" * 50)
    
    logger.info("=== اكتمال اختبار النظام المتقدم لأزواج OTC ===")

if __name__ == "__main__":
    main()