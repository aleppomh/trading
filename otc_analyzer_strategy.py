"""
خوارزمية تحليل مخصصة لأزواج OTC في منصة Pocket Option
توفر هذه الوحدة استراتيجيات متخصصة للتحليل الفني لأزواج OTC
"""

import logging
import numpy as np
from datetime import datetime, time

# إعداد السجلات
logger = logging.getLogger(__name__)

# ثوابت خاصة بتحليل أزواج OTC
OTC_THRESHOLD_MULTIPLIER = 0.9  # معامل تخفيض عتبة القبول للأزواج OTC (90%)
OTC_QUALITY_BONUS = 15.0       # مكافأة إضافية لدرجة جودة الإشارة للأزواج OTC
OTC_SR_STRENGTH_MULTIPLIER = 1.2  # معامل زيادة قوة مستويات الدعم والمقاومة للأزواج OTC

# وزن الإطارات الزمنية المختلفة للأزواج OTC
OTC_TIMEFRAME_WEIGHTS = {
    'M1': 0.6,    # وزن أكبر للإطار الزمني دقيقة واحدة للأزواج OTC
    'M5': 0.3,    # وزن متوسط للإطار الزمني 5 دقائق
    'M15': 0.1    # وزن منخفض للإطار الزمني 15 دقيقة
}

# ساعات التداول المفضلة للأزواج OTC
OTC_HIGH_QUALITY_HOURS = [
    (time(8, 0), time(11, 0)),    # جلسة لندن الصباحية
    (time(13, 0), time(16, 0)),   # جلسة نيويورك النشطة
    (time(19, 0), time(22, 0))    # جلسة آسيا المبكرة
]

# قائمة أزواج OTC الموثوقة ذات الأداء العالي
PREFERRED_OTC_PAIRS = [
    # أزواج OTC الأساسية ذات الموثوقية العالية جداً
    'EURUSD-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'GBPUSD-OTC',
    'EURGBP-OTC', 'AUDJPY-OTC', 'USDCAD-OTC', 'GBPJPY-OTC',
    # أزواج OTC إضافية ذات أداء جيد
    'AUDUSD-OTC', 'NZDUSD-OTC', 'USDCHF-OTC', 'CADCHF-OTC',
    'GBPCAD-OTC', 'EURAUD-OTC', 'AUDCAD-OTC', 'AUDNZD-OTC',
    # أزواج OTC للسلع
    'XAUUSD-OTC', 'XAGUSD-OTC'
]

def is_otc_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج من أزواج OTC
    
    Args:
        pair_symbol (str): رمز الزوج
        
    Returns:
        bool: True إذا كان الزوج من أزواج OTC، False خلاف ذلك
    """
    return "-OTC" in pair_symbol if isinstance(pair_symbol, str) else False

def is_preferred_otc_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج من أزواج OTC المفضلة
    
    Args:
        pair_symbol (str): رمز الزوج
        
    Returns:
        bool: True إذا كان الزوج من أزواج OTC المفضلة، False خلاف ذلك
    """
    return pair_symbol in PREFERRED_OTC_PAIRS if isinstance(pair_symbol, str) else False

def calculate_otc_threshold(base_threshold):
    """
    حساب عتبة القبول المخفضة للأزواج OTC
    
    Args:
        base_threshold (float): العتبة الأساسية
        
    Returns:
        float: العتبة المخفضة للأزواج OTC
    """
    return base_threshold * OTC_THRESHOLD_MULTIPLIER

def analyze_otc_timeframes(m1_direction, m5_direction, m15_direction, signal_direction):
    """
    تحليل توافق الإطارات الزمنية للأزواج OTC باستخدام الأوزان المخصصة
    
    Args:
        m1_direction (str): اتجاه الإطار الزمني M1
        m5_direction (str): اتجاه الإطار الزمني M5
        m15_direction (str): اتجاه الإطار الزمني M15
        signal_direction (str): اتجاه الإشارة
        
    Returns:
        tuple: (درجة التوافق، تفاصيل التحليل)
    """
    # التهيئة
    alignment_score = 0.0
    details = {}
    
    # حساب درجة توافق الإطار M1
    if m1_direction == signal_direction:
        m1_score = 100.0
    elif m1_direction == 'NEUTRAL':
        m1_score = 50.0
    else:
        m1_score = 0.0
    alignment_score += m1_score * OTC_TIMEFRAME_WEIGHTS['M1']
    details['M1'] = {'direction': m1_direction, 'score': m1_score, 'weight': OTC_TIMEFRAME_WEIGHTS['M1']}
    
    # حساب درجة توافق الإطار M5
    if m5_direction == signal_direction:
        m5_score = 100.0
    elif m5_direction == 'NEUTRAL':
        m5_score = 50.0
    else:
        m5_score = 0.0
    alignment_score += m5_score * OTC_TIMEFRAME_WEIGHTS['M5']
    details['M5'] = {'direction': m5_direction, 'score': m5_score, 'weight': OTC_TIMEFRAME_WEIGHTS['M5']}
    
    # حساب درجة توافق الإطار M15
    if m15_direction == signal_direction:
        m15_score = 100.0
    elif m15_direction == 'NEUTRAL':
        m15_score = 50.0
    else:
        m15_score = 0.0
    alignment_score += m15_score * OTC_TIMEFRAME_WEIGHTS['M15']
    details['M15'] = {'direction': m15_direction, 'score': m15_score, 'weight': OTC_TIMEFRAME_WEIGHTS['M15']}
    
    # استراتيجيات خاصة بأزواج OTC
    # 1. إذا كان هناك توافق بين M1 و M5، نزيد الدرجة بنسبة 20%
    if m1_direction == m5_direction and m1_direction == signal_direction:
        details['M1_M5_alignment_bonus'] = True
        alignment_score *= 1.2  # زيادة 20%
    else:
        details['M1_M5_alignment_bonus'] = False
    
    # 2. إذا كان هناك تعارض في M15، نخفف من تأثيره
    if m15_direction != signal_direction and m15_direction != 'NEUTRAL':
        details['M15_conflict_mitigation'] = True
        alignment_score = min(100.0, alignment_score * 0.9 + 10.0)  # تخفيف تأثير التعارض
    else:
        details['M15_conflict_mitigation'] = False
    
    # 3. بونص خاص لتوافق M1 بشكل كامل مع اتجاه الإشارة
    if m1_direction == signal_direction:
        details['M1_perfect_alignment_bonus'] = 10.0
        alignment_score = min(100.0, alignment_score + 10.0)
    else:
        details['M1_perfect_alignment_bonus'] = 0.0
    
    return alignment_score, details

def enhance_otc_signal(signal, basic_score):
    """
    تعزيز جودة إشارة OTC بناءً على استراتيجيات خاصة
    
    Args:
        signal (dict): بيانات الإشارة
        basic_score (float): الدرجة الأساسية للإشارة
        
    Returns:
        float: الدرجة المعززة للإشارة
    """
    enhanced_score = basic_score
    
    # إضافة بونص ثابت لأزواج OTC
    enhanced_score += OTC_QUALITY_BONUS
    
    # إذا كان الزوج من الأزواج المفضلة، نضيف بونص إضافي
    pair_symbol = signal.get('pair', '')
    if is_preferred_otc_pair(pair_symbol):
        enhanced_score = min(100.0, enhanced_score * 1.1)  # زيادة 10% أخرى للأزواج المفضلة
    
    # بونص إضافي لأزواج محددة ذات أداء ممتاز
    if pair_symbol in ['EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC']:
        enhanced_score = min(100.0, enhanced_score + 5.0)  # بونص 5 نقاط إضافية
    
    return min(100.0, enhanced_score)  # ضمان عدم تجاوز الحد الأقصى 100

def validate_otc_entry_time(entry_time):
    """
    التحقق من صلاحية وقت الدخول لأزواج OTC
    
    Args:
        entry_time (datetime.time): وقت الدخول المقترح
        
    Returns:
        float: درجة جودة الوقت (0-100)
    """
    if not entry_time:
        return 60.0  # درجة متوسطة افتراضية
    
    # التحقق مما إذا كان الوقت ضمن الأوقات المفضلة
    is_high_quality = any(start <= entry_time <= end for start, end in OTC_HIGH_QUALITY_HOURS)
    
    # الأوقات منخفضة الجودة للتداول
    low_quality_hours = [
        (time(0, 0), time(2, 0)),    # ساعات منتصف الليل
        (time(12, 0), time(13, 0))   # فترة الغداء الأوروبية
    ]
    
    is_low_quality = any(start <= entry_time <= end for start, end in low_quality_hours)
    
    # تعيين درجة جودة الوقت
    if is_high_quality:
        time_quality = 90.0  # جودة عالية
    elif is_low_quality:
        time_quality = 50.0  # جودة منخفضة (محسنة للأزواج OTC)
    else:
        time_quality = 75.0  # جودة متوسطة (محسنة للأزواج OTC)
    
    return time_quality

def adjust_sr_levels_for_otc(resistance_levels, support_levels):
    """
    تعديل قوة مستويات الدعم والمقاومة للأزواج OTC
    
    Args:
        resistance_levels (list): قائمة مستويات المقاومة
        support_levels (list): قائمة مستويات الدعم
        
    Returns:
        tuple: (مستويات المقاومة المعدلة، مستويات الدعم المعدلة)
    """
    # تعديل قوة مستويات المقاومة
    adjusted_resistance = []
    for level in resistance_levels:
        adjusted_level = level.copy()
        if 'strength' in adjusted_level:
            adjusted_level['strength'] = min(100.0, adjusted_level['strength'] * OTC_SR_STRENGTH_MULTIPLIER)
        adjusted_resistance.append(adjusted_level)
    
    # تعديل قوة مستويات الدعم
    adjusted_support = []
    for level in support_levels:
        adjusted_level = level.copy()
        if 'strength' in adjusted_level:
            adjusted_level['strength'] = min(100.0, adjusted_level['strength'] * OTC_SR_STRENGTH_MULTIPLIER)
        adjusted_support.append(adjusted_level)
    
    return adjusted_resistance, adjusted_support

def optimize_duration_for_otc(original_duration):
    """
    تحسين مدة التداول لأزواج OTC
    
    أزواج OTC تتطلب مدة أقصر بسبب طبيعتها المتقلبة
    
    Args:
        original_duration (int): المدة الأصلية بالدقائق
        
    Returns:
        int: المدة المحسنة للأزواج OTC
    """
    # أزواج OTC تعمل بشكل أفضل مع مدد قصيرة (1-3 دقائق)
    if original_duration > 3:
        return 3  # الحد الأقصى 3 دقائق للأزواج OTC
    return original_duration  # الإبقاء على المدة الأصلية إذا كانت مناسبة

def get_optimal_otc_pairs():
    """
    الحصول على قائمة أزواج OTC المفضلة المرتبة حسب الأولوية
    
    Returns:
        list: قائمة أزواج OTC مرتبة حسب الأولوية
    """
    # يمكن توسيع هذه الوظيفة لتقديم قائمة ديناميكية بناءً على أداء الأزواج الحالي
    return PREFERRED_OTC_PAIRS