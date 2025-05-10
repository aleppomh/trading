"""
نظام تحليل الرسوم البيانية المطور
يقوم بتحليل شامل للرسوم البيانية المستخرجة من منصة Pocket Option
ويتضمن خوارزميات متقدمة للتعرف على الأنماط وتوقع الحركة المستقبلية
"""

import os
import io
import base64
import math
import random
import logging
import numpy as np
from datetime import datetime, timedelta
from PIL import Image, ImageFilter, ImageEnhance
import cv2

logger = logging.getLogger(__name__)

# Constants for analysis
DEFAULT_CONFIDENCE = 85
MIN_CONFIDENCE = 70
MAX_CONFIDENCE = 95
TIMEFRAME_MINUTES = 1  # Default timeframe

# التحسين: معاملات ترجيح للعوامل المختلفة
WEIGHT_LAST_CANDLE = 4.0        # وزن الشمعة الأخيرة - ذات أهمية كبيرة جداً
WEIGHT_CONSECUTIVE_CANDLES = 3.5  # وزن تسلسل الشموع المتتالية
WEIGHT_PRICE_TREND = 2.0        # وزن اتجاه السعر العام
WEIGHT_SUPPORT_RESISTANCE = 3.0  # وزن مستويات الدعم والمقاومة
WEIGHT_VOLUME_ANALYSIS = 2.5    # وزن تحليل الحجم
WEIGHT_OSCILLATOR_SIGNALS = 2.0  # وزن إشارات المذبذبات
WEIGHT_PATTERN_RECOGNITION = 3.5  # وزن التعرف على الأنماط

def analyze_chart_image(image_data, selected_pair=None, timeframe=1):
    """
    تحليل صورة الرسم البياني وتوليد إشارة تداول
    
    Args:
        image_data: بيانات ملف الصورة
        selected_pair: الزوج المحدد
        timeframe: الإطار الزمني بالدقائق
        
    Returns:
        قاموس يحتوي على معلومات الإشارة
    """
    try:
        logger.info(f"Starting chart analysis for {selected_pair} with timeframe {timeframe}")
        
        # التحقق من صحة الصورة
        try:
            img = Image.open(io.BytesIO(image_data))
            img_size = img.size
            logger.info(f"Image validated successfully. Size: {img_size[0]}x{img_size[1]}")
        except Exception as img_error:
            logger.error(f"Failed to process image: {str(img_error)}")
            return {
                "error": "Failed to process image",
                "details": f"The image could not be processed: {str(img_error)}"
            }
        
        # إنشاء نسخة من الصورة للمعالجة
        img_gray = img.convert('L')
        img_array = np.array(img_gray)
        
        # تحسين جودة الصورة وتقليل الضوضاء
        img_enhanced = enhance_image_quality(img, img_array)
        img_array = np.array(img_enhanced.convert('L'))
        
        # استخراج معلومات أساسية عن الصورة
        brightness = np.mean(img_array) / 255.0
        contrast = np.std(img_array) / 255.0
        
        # تحليل التدرجات والحواف
        gx = np.gradient(img_array, axis=1)
        gy = np.gradient(img_array, axis=0)
        edge_magnitude = np.sqrt(gx**2 + gy**2)
        
        # الحصول على أبعاد الصورة
        height, width = img_array.shape
        
        # تقسيم الصورة إلى مناطق للتحليل
        # ===== تقسيم المناطق الرئيسية =====
        price_area = img_array[:]  # منطقة السعر الكاملة
        right_area = img_array[:, 3*width//4:]  # آخر 25% من الرسم - أحدث البيانات
        
        # ===== تقسيم الصورة أفقياً =====
        upper_half = img_array[:height//2, :]
        lower_half = img_array[height//2:, :]
        
        # ===== تقسيم الصورة عمودياً =====
        left_quarter = img_array[:, :width//4]
        mid_left_quarter = img_array[:, width//4:width//2]
        mid_right_quarter = img_array[:, width//2:3*width//4]
        right_quarter = img_array[:, 3*width//4:]
        
        # التركيز على منطقة الشموع الأخيرة
        recent_candles_area = img_array[2*height//3:, 2*width//3:]
        
        # ===== تحليل اتجاه السعر الأساسي =====
        left_avg = np.mean(left_quarter)
        mid_left_avg = np.mean(mid_left_quarter)
        mid_right_avg = np.mean(mid_right_quarter)
        right_avg = np.mean(right_quarter)
        
        # ===== تحليل النمط المتذبذب =====
        # تقسيم الصورة إلى شرائح للتعرف على التذبذبات
        num_segments = 12  # زيادة الدقة من 8 إلى 12
        segment_width = width // num_segments
        segment_avgs = [np.mean(img_array[:, i*segment_width:(i+1)*segment_width]) for i in range(num_segments)]
        
        # حساب التغيرات بين المقاطع المتتالية
        segment_changes = [segment_avgs[i+1] - segment_avgs[i] for i in range(num_segments-1)]
        sign_changes = sum(1 for i in range(num_segments-2) if segment_changes[i] * segment_changes[i+1] < 0)
        
        # متوسط حجم التغيير بين المقاطع
        avg_change_magnitude = np.mean([abs(change) for change in segment_changes])
        
        # حساب مؤشر التذبذب
        oscillation_index = sign_changes * avg_change_magnitude * 100
        
        # ===== تحليل الاتجاه =====
        price_trend = 0
        if right_avg < mid_right_avg < mid_left_avg < left_avg:
            price_trend = -2  # اتجاه هبوطي قوي
        elif right_avg < mid_right_avg:
            price_trend = -1  # اتجاه هبوطي معتدل
        elif right_avg > mid_right_avg > mid_left_avg > left_avg:
            price_trend = 2  # اتجاه صعودي قوي
        elif right_avg > mid_right_avg:
            price_trend = 1  # اتجاه صعودي معتدل
            
        # ===== تحليل الشموع الأخيرة (الجزء الأكثر أهمية) =====
        right_edge = img_array[:, int(0.95*width):]  # تركيز أكبر على آخر 5% من الشارت
        
        # تقسيم الحافة اليمنى إلى مقاطع أفقية للتعرف على نمط الشموع
        right_edge_segments = 15  # زيادة الدقة من 10 إلى 15
        segment_height = height // right_edge_segments
        right_edge_segment_avgs = [np.mean(right_edge[i*segment_height:(i+1)*segment_height, :]) for i in range(right_edge_segments)]
        
        # تحليل نسب الإضاءة في آخر شمعة
        right_edge_top_quarter = np.mean(right_edge[:height//4, :])
        right_edge_upper_mid = np.mean(right_edge[height//4:height//2, :])
        right_edge_lower_mid = np.mean(right_edge[height//2:3*height//4, :])
        right_edge_bottom_quarter = np.mean(right_edge[3*height//4:, :])
        
        # تحليل تدرج الشموع الأخيرة
        recent_gradient_y = np.mean(np.gradient(np.mean(recent_candles_area, axis=1)))
        
        # اختبار اتجاه الشموع الأخيرة بناءً على تدرج العمود الأخير
        last_column = recent_candles_area[:, -1]
        last_column_gradient = np.gradient(last_column)
        last_column_direction = 1 if np.mean(last_column_gradient) < 0 else -1
        
        # تحليل الاتجاه الحديث
        recent_trend = 1 if recent_gradient_y < 0 else -1
        
        # ===== تحليل أنماط الشموع =====
        # تقسيم منطقة الشموع الأخيرة إلى شموع فردية للتحليل
        candle_columns = 16  # زيادة الدقة من 10 إلى 16
        last_quarter_width = width // 4
        candle_width = last_quarter_width // candle_columns
        
        candle_colors = []  # لتخزين اتجاه كل شمعة (موجب للأخضر، سالب للأحمر)
        candle_strengths = []  # لتخزين قوة كل شمعة
        candle_body_sizes = []  # لتخزين حجم جسم كل شمعة
        
        # تحليل كل شمعة على حدة
        for i in range(candle_columns):
            col_start = width - last_quarter_width + i * candle_width
            col_end = col_start + candle_width
            if col_end > width:
                col_end = width
                
            # استخراج منطقة الشمعة
            candle_area = img_array[:, col_start:col_end]
            
            # التحليل المتقدم للشموع
            candle_result = analyze_single_candle(candle_area, height)
            
            candle_colors.append(candle_result["direction"])
            candle_strengths.append(candle_result["strength"])
            candle_body_sizes.append(candle_result["body_size"])
        
        # ===== تحليل نمط تسلسل الشموع =====
        # حساب عدد الشموع المتتالية من نفس اللون
        consecutive_red = count_consecutive_candles(candle_colors, -1)
        consecutive_green = count_consecutive_candles(candle_colors, 1)
        
        # ===== تحليل نمط انعكاس الشموع =====
        # البحث عن أنماط انعكاس محددة
        reversal_pattern_result = detect_reversal_patterns(candle_colors, candle_strengths, candle_body_sizes)
        reversal_pattern = reversal_pattern_result["detected"]
        reversal_direction = reversal_pattern_result["direction"]
        reversal_strength = reversal_pattern_result["strength"]
        
        # ===== تحليل مستويات الدعم والمقاومة =====
        support_resistance_result = analyze_support_resistance(img_array, height, width)
        
        # ===== تحليل التدرجات ونمط المسار =====
        gradient_pattern_result = analyze_gradient_patterns(img_array, height, width)
        
        # ===== تجميع جميع الإشارات للتحليل النهائي =====
        trend_signals = []
        
        # 1. اتجاه السعر الأساسي
        trend_signals.append(price_trend * WEIGHT_PRICE_TREND)
        
        # 2. اتجاه الشمعة الأخيرة (الأهم) - وزن مضاعف
        if right_edge_top_quarter > right_edge_bottom_quarter:
            # الجزء العلوي من الشمعة أفتح - إشارة شراء
            trend_signals.append(WEIGHT_LAST_CANDLE)
        elif right_edge_bottom_quarter > right_edge_top_quarter:
            # الجزء السفلي من الشمعة أفتح - إشارة بيع
            trend_signals.append(-WEIGHT_LAST_CANDLE)
            
        # 3. تسلسل الشموع المتتالية (إشارة قوية جداً)
        if consecutive_red >= 3:
            # سلسلة من الشموع الحمراء - عامل بيع قوي
            sell_strength = min(consecutive_red, 6) / 2
            trend_signals.append(-sell_strength * WEIGHT_CONSECUTIVE_CANDLES)
            logger.info(f"Detected {consecutive_red} consecutive red candles - strong SELL signal")
        elif consecutive_green >= 3:
            # سلسلة من الشموع الخضراء - عامل شراء قوي
            buy_strength = min(consecutive_green, 6) / 2
            trend_signals.append(buy_strength * WEIGHT_CONSECUTIVE_CANDLES)
            logger.info(f"Detected {consecutive_green} consecutive green candles - strong BUY signal")
            
        # 4. أنماط الانعكاس
        if reversal_pattern:
            # وزن قوي لأنماط الانعكاس المكتشفة
            trend_signals.append(reversal_direction * reversal_strength * WEIGHT_PATTERN_RECOGNITION)
            
        # 5. مؤشرات الدعم والمقاومة
        if support_resistance_result["near_level"]:
            # إضافة إشارة بناءً على القرب من مستوى الدعم أو المقاومة
            trend_signals.append(support_resistance_result["direction"] * WEIGHT_SUPPORT_RESISTANCE)
            
        # 6. أنماط التدرجات والمسار
        trend_signals.append(gradient_pattern_result["direction"] * gradient_pattern_result["strength"] * 1.5)
        
        # 7. تحليل القمم والقيعان المتتالية
        highs_lows_result = analyze_highs_lows(segment_avgs)
        trend_signals.append(highs_lows_result["direction"] * highs_lows_result["strength"] * 1.8)
        
        # 8. تحليل الاتجاه الأخير (قبل الشمعة الأخيرة)
        last_candles_trend = sum(candle_colors[-4:-1])  # تجاهل الشمعة الأخيرة لتحليل الاتجاه السابق
        if abs(last_candles_trend) >= 2:
            # اتجاه واضح في آخر 3 شموع قبل الأخيرة
            trend_signals.append(np.sign(last_candles_trend) * 1.5)
            
        # تفاعل عامل التذبذب مع الإشارة
        is_oscillating = False
        oscillation_factor = 0
        oscillation_confidence_reduction = 0
        
        # تحليل التذبذب
        if sign_changes >= 3 and avg_change_magnitude > 0.01:
            is_oscillating = True
            oscillation_factor = min((sign_changes - 2) * 0.5, 2.0)
            
            # قوة التذبذب ستؤثر على تخفيض الثقة
            oscillation_confidence_reduction = int(min(sign_changes * 5, 25))
            
            # تسجيل تفاصيل التذبذب
            logger.info(f"Oscillation detected: {sign_changes} direction changes, avg_magnitude: {avg_change_magnitude:.4f}, index: {oscillation_index:.2f}")
            
            # التعامل مع التذبذب القوي
            if oscillation_factor > 1.5:
                # إذا كان التذبذب قوياً، تقليل قوة الإشارة
                strong_oscillation = True
                if abs(price_trend) < 1.0:
                    # التذبذب القوي يلغي الاتجاه الضعيف
                    logger.info(f"Strong oscillation overrides weak trend: {price_trend} -> 0")
                    price_trend = 0
        
        # حساب مجموع الإشارات
        trend_sum = sum(trend_signals)
        
        # تطبيق عامل التصحيح إذا لزم الأمر لتجنب التحيز
        corrected_trend_sum = trend_sum  # يمكن تطبيق تصحيح إضافي هنا
        
        # تسجيل تفاصيل التحليل
        logger.info(f"Trend analysis: price_trend={price_trend}, recent_trend={recent_trend}, brightness_factor={0}")
        logger.info(f"Last candle analysis: top_quarter={right_edge_top_quarter:.2f}, bottom_quarter={right_edge_bottom_quarter:.2f}")
        logger.info(f"Signals: {trend_signals}, Sum: {trend_sum} (after correction: {corrected_trend_sum})")
        
        # تسجيل تفاصيل تحليل الصورة
        logger.info(f"Image analysis details: upper_avg={upper_half.mean():.2f}, lower_avg={lower_half.mean():.2f}, right_avg={right_avg:.2f}, left_avg={left_avg:.2f}, brightness={brightness:.2f}, trend_sum={corrected_trend_sum}")
        
        # تحديد الاتجاه بناءً على مجموع الإشارات بعد التصحيح
        direction = "BUY" if corrected_trend_sum > 0 else "SELL"
        
        # حساب نسبة الاحتمالية (القوة المطلقة للإشارة)
        signal_strength = min(abs(corrected_trend_sum), 10)  # تحديد القوة القصوى بـ 10
        probability_base = 50 + int(5 * signal_strength)  # تبدأ من 50% وتزيد بناءً على القوة
        
        # تخفيض الثقة إذا كان هناك تذبذب
        probability = max(MIN_CONFIDENCE, min(probability_base, MAX_CONFIDENCE))
        
        if is_oscillating:
            # تقليل نسبة الثقة بناءً على قوة التذبذب
            probability = max(MIN_CONFIDENCE, probability - oscillation_confidence_reduction)
            logger.info(f"Reducing confidence due to oscillation: -{oscillation_confidence_reduction}% (new: {probability}%)")
        
        # تحديد وقت الدخول بعد 2-3 دقائق من الوقت الحالي
        now = datetime.now()
        entry_time = (now + timedelta(minutes=2 + random.randint(0, 1))).strftime("%H:%M")
        
        # تحديد مدة الصفقة (1-3 دقائق)
        # تكون المدة قصيرة في حالات التذبذب العالي، وطويلة في حالات الاتجاه القوي
        if abs(corrected_trend_sum) < 3 or is_oscillating:
            # اتجاه ضعيف أو تذبذب - مدة قصيرة
            trade_duration = 1
        elif abs(corrected_trend_sum) > 6:
            # اتجاه قوي جداً - مدة طويلة
            trade_duration = 3
        else:
            # اتجاه متوسط - مدة متوسطة
            trade_duration = 2
            
        # صياغة نص التحليل استناداً إلى الاتجاه والقوة
        analysis_notes = generate_analysis_notes(direction, probability, consecutive_red, consecutive_green, 
                                                 is_oscillating, sign_changes, reversal_pattern, reversal_direction)
        
        # تجميع معلومات الإشارة
        signal_data = {
            "direction": direction,
            "probability": f"{probability}%",
            "entry_time": entry_time,
            "duration": trade_duration,
            "analysis_notes": analysis_notes,
            "analysis_info": {
                "trend_sum": corrected_trend_sum,
                "oscillation_index": oscillation_index,
                "recent_trend": recent_trend,
                "price_trend": price_trend,
                "consecutive_candles": max(consecutive_red, consecutive_green),
                "is_oscillating": is_oscillating,
                "sign_changes": sign_changes,
                "reversal_pattern": reversal_pattern
            }
        }
        
        logger.info(f"Generated signal direction: {direction}")
        logger.info(f"Generated confidence level: {probability}%")
        logger.info(f"Generated entry time: {entry_time}")
        logger.info(f"Trade duration: {trade_duration} minutes")
        logger.info(f"Analysis completed successfully for {selected_pair}")
        
        return signal_data
    
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}", exc_info=True)
        return {
            "error": "Analysis error",
            "details": f"Error during analysis: {str(e)}"
        }

def enhance_image_quality(img, img_array):
    """
    تحسين جودة الصورة وتقليل الضوضاء لتحسين التحليل
    """
    try:
        # تطبيق مرشح للحد من الضوضاء
        img_enhanced = img.filter(ImageFilter.SMOOTH)
        
        # تعزيز التباين
        enhancer = ImageEnhance.Contrast(img_enhanced)
        img_enhanced = enhancer.enhance(1.2)  # زيادة التباين بنسبة 20%
        
        # تعزيز حدة الصورة
        enhancer = ImageEnhance.Sharpness(img_enhanced)
        img_enhanced = enhancer.enhance(1.3)
        
        return img_enhanced
    except Exception as e:
        logger.warning(f"Could not enhance image: {str(e)}")
        return img

def analyze_single_candle(candle_area, height):
    """
    تحليل شمعة فردية لتحديد اتجاهها وقوتها وخصائصها
    """
    # تقسيم الشمعة إلى أقسام للتحليل التفصيلي
    top_quarter = np.mean(candle_area[:height//4, :])
    upper_mid_quarter = np.mean(candle_area[height//4:height//2, :])
    lower_mid_quarter = np.mean(candle_area[height//2:3*height//4, :])
    bottom_quarter = np.mean(candle_area[3*height//4:, :])
    
    # تحليل الفتائل العلوية والسفلية
    upper_tail = top_quarter - upper_mid_quarter
    lower_tail = bottom_quarter - lower_mid_quarter
    
    # تحليل جسم الشمعة
    body_size = abs(upper_mid_quarter - lower_mid_quarter)
    
    # تحديد اتجاه الشمعة
    direction = 0  # محايد
    strength = 0   # قوة الشمعة
    
    if upper_mid_quarter > lower_mid_quarter * 1.05:
        # شمعة خضراء - الجزء العلوي أفتح
        direction = 1
        strength = (upper_mid_quarter / lower_mid_quarter - 1) * 10
    elif lower_mid_quarter > upper_mid_quarter * 1.05:
        # شمعة حمراء - الجزء السفلي أفتح
        direction = -1
        strength = (lower_mid_quarter / upper_mid_quarter - 1) * 10
    
    # تحليل خصائص الشمعة
    has_long_upper_tail = upper_tail > body_size * 1.5
    has_long_lower_tail = lower_tail > body_size * 1.5
    
    return {
        "direction": direction,
        "strength": min(strength, 5),  # تحديد الحد الأقصى للقوة
        "body_size": body_size,
        "upper_tail": upper_tail,
        "lower_tail": lower_tail,
        "has_long_upper_tail": has_long_upper_tail,
        "has_long_lower_tail": has_long_lower_tail
    }

def count_consecutive_candles(candle_colors, direction):
    """
    حساب عدد الشموع المتتالية بنفس الاتجاه
    """
    count = 0
    # البدء من آخر شمعة والعودة للخلف
    for i in range(len(candle_colors)-1, -1, -1):
        if candle_colors[i] == direction:
            count += 1
        else:
            break
    return count

def detect_reversal_patterns(candle_colors, candle_strengths, candle_body_sizes):
    """
    التعرف على أنماط الانعكاس في الشموع
    """
    # نتيجة افتراضية: لم يتم اكتشاف نمط
    result = {
        "detected": False,
        "direction": 0,
        "strength": 0,
        "pattern_name": None
    }
    
    # التحقق من وجود شموع كافية للتحليل
    if len(candle_colors) < 5:
        return result
    
    # آخر 5 شموع للتحليل
    last_5_colors = candle_colors[-5:]
    last_5_strengths = candle_strengths[-5:]
    last_5_body_sizes = candle_body_sizes[-5:]
    
    # ===== نمط المطرقة/المعلقة (Hammer/Hanging Man) =====
    # المطرقة: شمعة أخيرة بجسم صغير وفتيل سفلي طويل
    if (candle_colors[-1] == 1 and  # شمعة خضراء
        candle_body_sizes[-1] < np.mean(last_5_body_sizes) * 0.7 and  # جسم صغير
        candle_strengths[-1] < 3):  # قوة معتدلة
        
        # التحقق من نمط المطرقة
        prior_trend = sum(last_5_colors[:-1])
        if prior_trend < -2:  # اتجاه هبوطي سابق
            result = {
                "detected": True,
                "direction": 1,  # إشارة شراء
                "strength": 2.5,
                "pattern_name": "Hammer"
            }
    
    # ===== نمط الابتلاع (Engulfing) =====
    if len(candle_colors) >= 6:
        # نمط الابتلاع الصعودي: شمعة حمراء متبوعة بشمعة خضراء أكبر
        if (candle_colors[-2] == -1 and  # شمعة سابقة حمراء
            candle_colors[-1] == 1 and   # شمعة حالية خضراء
            candle_body_sizes[-1] > candle_body_sizes[-2] * 1.3):  # الشمعة الحالية أكبر
            
            # التحقق من اتجاه سابق هبوطي
            prior_trend = sum(candle_colors[-6:-2])
            if prior_trend < -2:  # اتجاه هبوطي سابق
                result = {
                    "detected": True,
                    "direction": 1,  # إشارة شراء
                    "strength": 3.0,
                    "pattern_name": "Bullish Engulfing"
                }
        
        # نمط الابتلاع الهبوطي: شمعة خضراء متبوعة بشمعة حمراء أكبر
        elif (candle_colors[-2] == 1 and    # شمعة سابقة خضراء
              candle_colors[-1] == -1 and   # شمعة حالية حمراء
              candle_body_sizes[-1] > candle_body_sizes[-2] * 1.3):  # الشمعة الحالية أكبر
              
            # التحقق من اتجاه سابق صعودي
            prior_trend = sum(candle_colors[-6:-2])
            if prior_trend > 2:  # اتجاه صعودي سابق
                result = {
                    "detected": True,
                    "direction": -1,  # إشارة بيع
                    "strength": 3.0,
                    "pattern_name": "Bearish Engulfing"
                }
    
    # ===== نمط الدوجي (Doji) =====
    if (abs(candle_colors[-1]) < 0.5 and  # شمعة محايدة أو ضعيفة الاتجاه
        candle_body_sizes[-1] < np.mean(last_5_body_sizes) * 0.5):  # جسم صغير جداً
        
        # الدوجي بعد اتجاه قوي يشير إلى انعكاس محتمل
        prior_trend = sum(last_5_colors[:-1])
        if abs(prior_trend) >= 3:
            result = {
                "detected": True,
                "direction": -np.sign(prior_trend),  # عكس الاتجاه السابق
                "strength": 2.0,
                "pattern_name": "Doji"
            }
    
    return result

def analyze_support_resistance(img_array, height, width):
    """
    تحليل مستويات الدعم والمقاومة في الرسم البياني
    """
    result = {
        "near_level": False,
        "direction": 0,
        "strength": 0,
        "level_type": None
    }
    
    # تقسيم الصورة أفقياً إلى أشرطة لتحديد مستويات الأسعار الأفقية
    num_strips = 20
    strip_height = height // num_strips
    
    strip_avgs = []
    for i in range(num_strips):
        strip = img_array[i*strip_height:(i+1)*strip_height, :]
        strip_avgs.append(np.mean(strip))
    
    # البحث عن تغيرات حادة في متوسط الإضاءة بين الأشرطة المتجاورة
    # هذه التغيرات قد تشير إلى مستويات الدعم أو المقاومة
    strip_changes = [abs(strip_avgs[i+1] - strip_avgs[i]) for i in range(num_strips-1)]
    
    # تحديد العتبة للتغيرات الكبيرة (مستويات محتملة)
    threshold = np.mean(strip_changes) * 1.5
    
    # العثور على المستويات المحتملة
    potential_levels = []
    for i in range(num_strips-1):
        if strip_changes[i] > threshold:
            potential_levels.append({
                "position": i,
                "value": strip_avgs[i],
                "change": strip_changes[i]
            })
    
    # التحقق من القرب من الشمعة الأخيرة
    if len(potential_levels) > 0:
        # تركيز على آخر 10% من عرض الصورة (الشموع الأخيرة)
        right_edge = img_array[:, int(0.9*width):]
        
        # حساب متوسط الإضاءة في كل شريط لهذه المنطقة
        right_edge_strip_avgs = []
        for i in range(num_strips):
            strip = right_edge[i*strip_height:(i+1)*strip_height, :]
            right_edge_strip_avgs.append(np.mean(strip))
        
        # التحقق من أقرب مستوى للشمعة الأخيرة
        current_price_strip = np.argmin([abs(right_edge_strip_avgs[i] - np.mean(right_edge)) for i in range(num_strips)])
        
        # البحث عن أقرب مستوى محتمل
        for level in potential_levels:
            distance = abs(level["position"] - current_price_strip)
            if distance <= 2:  # مستوى قريب (ضمن شريطين)
                result["near_level"] = True
                
                # تحديد اتجاه الإشارة
                if level["position"] < current_price_strip:
                    # المستوى فوق السعر الحالي - مقاومة محتملة
                    result["direction"] = -1  # إشارة بيع
                    result["level_type"] = "Resistance"
                else:
                    # المستوى تحت السعر الحالي - دعم محتمل
                    result["direction"] = 1  # إشارة شراء
                    result["level_type"] = "Support"
                
                # حساب قوة الإشارة بناءً على قوة المستوى
                result["strength"] = min(level["change"] / threshold, 3.0)
                break
    
    return result

def analyze_gradient_patterns(img_array, height, width):
    """
    تحليل أنماط التدرجات والمسارات في الرسم البياني
    """
    result = {
        "direction": 0,
        "strength": 0,
        "pattern_type": None
    }
    
    # تقسيم الصورة إلى أجزاء عمودية لتحليل المسار
    num_columns = 16
    column_width = width // num_columns
    
    column_avgs = []
    for i in range(num_columns):
        column = img_array[:, i*column_width:(i+1)*column_width]
        column_avgs.append(np.mean(column))
    
    # اتجاه المسار الإجمالي
    overall_trend = column_avgs[-1] - column_avgs[0]
    
    # تحليل التدرجات المتتالية
    segment_trends = [column_avgs[i+1] - column_avgs[i] for i in range(num_columns-1)]
    
    # حساب نسب الاتجاهات الإيجابية والسلبية في النصف الثاني
    second_half_trends = segment_trends[num_columns//2:]
    positive_ratio = sum(1 for trend in second_half_trends if trend > 0) / len(second_half_trends)
    negative_ratio = sum(1 for trend in second_half_trends if trend < 0) / len(second_half_trends)
    
    # تحديد نوع النمط
    if positive_ratio > 0.7:
        # اتجاه صعودي قوي في النصف الثاني
        result["direction"] = 1
        result["strength"] = positive_ratio * 2
        result["pattern_type"] = "Strong Uptrend"
    elif negative_ratio > 0.7:
        # اتجاه هبوطي قوي في النصف الثاني
        result["direction"] = -1
        result["strength"] = negative_ratio * 2
        result["pattern_type"] = "Strong Downtrend"
    else:
        # التركيز على آخر 3 تدرجات فقط
        last_3_trends = segment_trends[-3:]
        last_3_direction = np.sign(sum(last_3_trends))
        
        if abs(sum(last_3_trends)) > abs(sum(segment_trends[-6:-3])):
            # تسارع في الاتجاه الأخير
            result["direction"] = last_3_direction
            result["strength"] = min(abs(sum(last_3_trends)) / abs(np.mean(segment_trends)), 2.5)
            result["pattern_type"] = "Accelerating" + (" Uptrend" if last_3_direction > 0 else " Downtrend")
        else:
            # اتجاه ضعيف أو متذبذب
            result["direction"] = np.sign(overall_trend)
            result["strength"] = 0.5
            result["pattern_type"] = "Weak Trend"
    
    return result

def analyze_highs_lows(segment_avgs):
    """
    تحليل القمم والقيعان المتتالية لتحديد الاتجاه
    """
    result = {
        "direction": 0,
        "strength": 0,
        "pattern": None
    }
    
    # التحقق من وجود بيانات كافية
    if len(segment_avgs) < 6:
        return result
    
    # تحديد القمم والقيعان المحلية
    peaks = []
    troughs = []
    
    for i in range(1, len(segment_avgs)-1):
        if segment_avgs[i] > segment_avgs[i-1] and segment_avgs[i] > segment_avgs[i+1]:
            # هذه قمة محلية
            peaks.append((i, segment_avgs[i]))
        elif segment_avgs[i] < segment_avgs[i-1] and segment_avgs[i] < segment_avgs[i+1]:
            # هذا قاع محلي
            troughs.append((i, segment_avgs[i]))
    
    # تحليل القمم والقيعان المتتالية للتعرف على الاتجاه
    if len(peaks) >= 2:
        # مقارنة آخر قمتين
        last_peak_height = peaks[-1][1]
        prev_peak_height = peaks[-2][1]
        
        # قمم أعلى = اتجاه صعودي
        if last_peak_height > prev_peak_height:
            result["direction"] += 1
            result["strength"] += 1
            result["pattern"] = "Higher Highs"
        # قمم أقل = اتجاه هبوطي
        elif last_peak_height < prev_peak_height:
            result["direction"] -= 1
            result["strength"] += 1
            result["pattern"] = "Lower Highs"
    
    if len(troughs) >= 2:
        # مقارنة آخر قاعين
        last_trough_height = troughs[-1][1]
        prev_trough_height = troughs[-2][1]
        
        # قيعان أعلى = اتجاه صعودي
        if last_trough_height > prev_trough_height:
            result["direction"] += 1
            result["strength"] += 1
            if result["pattern"]:
                result["pattern"] += " and Higher Lows"
            else:
                result["pattern"] = "Higher Lows"
        # قيعان أقل = اتجاه هبوطي
        elif last_trough_height < prev_trough_height:
            result["direction"] -= 1
            result["strength"] += 1
            if result["pattern"]:
                result["pattern"] += " and Lower Lows"
            else:
                result["pattern"] = "Lower Lows"
    
    # تعديل قوة الإشارة
    result["strength"] = min(result["strength"], 2.0)
    
    return result

def generate_analysis_notes(direction, probability, consecutive_red, consecutive_green, 
                           is_oscillating, sign_changes, reversal_pattern, reversal_direction):
    """
    إنشاء تحليل نصي بناءً على نتائج تحليل الرسم البياني
    """
    if direction == "BUY":
        if probability >= 85:
            strength_desc = "قوية جداً"
            confidence_desc = "عالية جداً"
        elif probability >= 75:
            strength_desc = "قوية"
            confidence_desc = "عالية"
        else:
            strength_desc = "معتدلة"
            confidence_desc = "متوسطة إلى عالية"
            
        if consecutive_green >= 3:
            pattern_desc = "مع نمط شموع صاعدة واضحة"
            move_desc = "مع حركة قوية للسعر"
        else:
            pattern_desc = "مع بعض الإشارات الإيجابية"
            move_desc = "مع حركة متوقعة للسعر"
            
    else:  # SELL
        if probability >= 85:
            strength_desc = "قوية جداً"
            confidence_desc = "عالية جداً"
        elif probability >= 75:
            strength_desc = "قوية"
            confidence_desc = "عالية"
        else:
            strength_desc = "معتدلة"
            confidence_desc = "متوسطة إلى عالية"
            
        if consecutive_red >= 3:
            pattern_desc = "مع نمط شموع هابطة واضحة"
            move_desc = "مع حركة قوية للسعر"
        else:
            pattern_desc = "مع بعض الإشارات السلبية"
            move_desc = "مع حركة متوقعة للسعر"
    
    # تحديد وصف الاحتمالية
    if probability >= 85:
        probability_desc = "مرتفعة جداً"
    elif probability >= 75:
        probability_desc = "مرتفعة"
    else:
        probability_desc = "متوسطة"
    
    # وصف حالة السوق
    if is_oscillating:
        if sign_changes >= 5:
            market_desc = "السوق في حالة تذبذب عالية"
        else:
            market_desc = "السوق في حالة تذبذب"
    else:
        market_desc = "السوق في حالة اتجاه واضح"
    
    # معلومات إضافية عن النمط
    extra_info = ""
    if reversal_pattern and ((reversal_direction > 0 and direction == "BUY") or (reversal_direction < 0 and direction == "SELL")):
        extra_info = " تم رصد نمط انعكاس يدعم الإشارة."
    
    # صياغة التحليل الكامل
    if direction == "BUY":
        analysis = f"إشارة شراء {strength_desc} {pattern_desc} {move_desc}. {market_desc}، لكن الإشارة الأخيرة تشير إلى شراء. الاحتمالية {probability_desc} بناءً على تحليل متعدد المؤشرات مع درجة ثقة {confidence_desc}.{extra_info}"
    else:
        analysis = f"إشارة بيع {strength_desc} {pattern_desc} {move_desc}. {market_desc}، لكن الإشارة الأخيرة تشير إلى بيع. الاحتمالية {probability_desc} بناءً على تحليل متعدد المؤشرات مع درجة ثقة {confidence_desc}.{extra_info}"
    
    return analysis

def analyze_chart_from_file(file_path, pair_name, timeframe=1):
    """
    تحليل صورة رسم بياني من ملف محدد
    """
    try:
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        return analyze_chart_image(image_data, pair_name, timeframe)
    except Exception as e:
        logger.error(f"Error analyzing chart from file: {str(e)}")
        return {"error": f"Error analyzing chart from file: {str(e)}"}

# إذا تم تشغيل الملف مباشرة
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # إجراء اختبار باستخدام ملف صورة
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        pair_name = sys.argv[2] if len(sys.argv) > 2 else "EUR/USD"
        result = analyze_chart_from_file(file_path, pair_name)
        print(f"Analysis Result: {result}")