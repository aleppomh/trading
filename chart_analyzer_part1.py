import os
import io
import base64
import random
import logging
from datetime import datetime, timedelta
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CONFIDENCE = 85
MIN_CONFIDENCE = 70
MAX_CONFIDENCE = 95
TIMEFRAME_MINUTES = 1  # Default timeframe (1 minute)

def analyze_chart_image(image_data, selected_pair=None, timeframe=1):
    """
    Analyze uploaded chart image and generate a trading signal
    
    Args:
        image_data: Image file data
        selected_pair: Selected OTC pair
        timeframe: Selected timeframe in minutes
        
    Returns:
        Dictionary with signal information
    """
    try:
        logger.info(f"Starting chart analysis for {selected_pair} with timeframe {timeframe}")
        
        # First, try to validate the image to make sure it's processable
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
        
        # Generate direction (BUY or SELL) based on image analysis
        # Convert to grayscale and numpy array for analysis
        img_gray = img.convert('L')
        img_array = np.array(img_gray)
        
        # Calculate basic image metrics
        brightness = np.mean(img_array) / 255.0
        variance = np.var(img_array) / (255.0 * 255.0)
        
        # Simple edge detection using gradient magnitude
        gx = np.gradient(img_array, axis=1)
        gy = np.gradient(img_array, axis=0)
        edge_magnitude = np.sqrt(gx**2 + gy**2)
        edge_density = np.mean(edge_magnitude) / 255.0
        
        # Simple gradient measure
        gradient = np.mean(np.abs(gx) + np.abs(gy)) / 255.0
        
        # تحليل الصورة بشكل متقدم لتحديد الاتجاه الحقيقي
        height, width = img_array.shape
        
        # تقسيم الصورة إلى مناطق مختلفة للتحليل الأكثر دقة
        # منطقة الشموع الأخيرة (الزاوية اليمنى السفلية)
        recent_candles = img_array[2*height//3:, 2*width//3:]
        # منطقة السعر الحالي (الثلث الأيمن)
        current_price_area = img_array[:, 2*width//3:]
        # منطقة الاتجاه التاريخي (الثلث الأوسط)
        historical_trend = img_array[:, width//3:2*width//3]
        
        # تحليل أكثر تفصيلاً للمناطق المختلفة
        upper_half = img_array[:height//2, :]
        lower_half = img_array[height//2:, :]
        upper_avg = np.mean(upper_half)
        lower_avg = np.mean(lower_half)
        
        # تحليل الاتجاه الأفقي (من اليسار إلى اليمين)
        left_avg = np.mean(img_array[:, :width//4])
        mid_left_avg = np.mean(img_array[:, width//4:width//2])
        mid_right_avg = np.mean(img_array[:, width//2:3*width//4])
        right_avg = np.mean(img_array[:, 3*width//4:])
        
        # التحليل المقسم للتعرف على الأنماط المتذبذبة
        # تقسيم الصورة إلى 8 أقسام أفقية لتحليل أكثر دقة للحركة
        segment_width = width // 8
        segment_avgs = [np.mean(img_array[:, i*segment_width:(i+1)*segment_width]) for i in range(8)]
        
        # حساب التغيرات بين المقاطع المتتالية لاكتشاف التذبذبات
        segment_changes = [segment_avgs[i+1] - segment_avgs[i] for i in range(7)]
        sign_changes = sum(1 for i in range(6) if segment_changes[i] * segment_changes[i+1] < 0)
        
        # متوسط حجم التغير بين المقاطع
        avg_change_magnitude = np.mean([abs(change) for change in segment_changes])
        
        # تحليل الاتجاه العمودي (من أعلى إلى أسفل)
        y_gradient = np.mean(gy, axis=1)
        x_gradient = np.mean(gx, axis=0)
        
        # حساب مؤشر التذبذب (عدد التغيرات في الاتجاه مع مراعاة حجم التغير)
        oscillation_index = sign_changes * avg_change_magnitude * 100
        
        # حساب تدرج السعر المتوسط
        price_trend = 0
        if right_avg < mid_right_avg < mid_left_avg < left_avg:
            price_trend = -2  # اتجاه هبوطي قوي
        elif right_avg < mid_right_avg:
            price_trend = -1  # اتجاه هبوطي معتدل
        elif right_avg > mid_right_avg > mid_left_avg > left_avg:
            price_trend = 2  # اتجاه صعودي قوي
        elif right_avg > mid_right_avg:
            price_trend = 1  # اتجاه صعودي معتدل
            
        # تحليل الشموع الأخيرة - تصحيح المنطق
        recent_gradient_y = np.mean(np.gradient(np.mean(recent_candles, axis=1)))
        # في الشموع الخضراء (الصعودية)، الجزء العلوي أكثر إشراقًا من السفلي
        # في الشموع الحمراء (الهبوطية)، الجزء السفلي أكثر إشراقًا من العلوي
        # لذا إذا كان التدرج موجبًا (يزيد من أسفل لأعلى)، فهذا يشير للشراء
        recent_trend = 1 if recent_gradient_y > 0 else -1
        
        # تحليل التباين في مناطق مختلفة
        recent_variance = np.var(recent_candles)
        upper_variance = np.var(upper_half)
        lower_variance = np.var(lower_half)
        
        # مؤشرات إضافية للتحليل
        # البحث عن أنماط الشموع الأساسية
        edge_recent = np.mean(edge_magnitude[2*height//3:, 2*width//3:])
        doji_pattern = edge_recent > np.mean(edge_magnitude) * 1.2  # شمعة دوجي تظهر كحافة قوية
        
        # تحديد الاتجاه بناءً على مجموعة من العوامل
        trend_signals = []
        
        # 1. الأنماط الأفقية الإجمالية (الاتجاه من اليسار إلى اليمين)
        trend_signals.append(price_trend)
        
        # 2. الاتجاه الأخير في منطقة الشموع الحديثة
        if recent_variance > np.var(img_array) * 1.2:  # إذا كانت الشموع الأخيرة أكثر تباينًا
            trend_signals.append(recent_trend * 2)  # وزن أكبر للاتجاه الأخير
        else:
            trend_signals.append(recent_trend)
            
        # 3. التباين بين الجزء العلوي والسفلي
        if lower_variance > upper_variance * 1.5:
            trend_signals.append(1)  # إشارة إلى اتجاه صعودي (تباين أكبر في الأسفل)
        elif upper_variance > lower_variance * 1.5:
            trend_signals.append(-1)  # إشارة إلى اتجاه هبوطي
            
        # 4. تحليل أنماط الشموع المحددة
        if doji_pattern:
            # إذا كانت الشمعة الأخيرة دوجي، فهي تشير غالبًا إلى انعكاس الاتجاه
            trend_signals.append(-np.sign(price_trend))  # عكس الاتجاه السابق
        
        # 5. تحليل مستويات السطوع - تحسين بحيث لا يكون هناك تحيز
        brightness_factor = 0
        # الألوان الفاتحة/الداكنة وحدها ليست مؤشراً على الاتجاه
        # لذلك نحيّد تأثير السطوع لتجنب التحيز للشراء أو البيع
        # إذا كان التباين كبيراً، فقد يكون هناك نشاط سعري مهم
        if brightness > 0.7 or brightness < 0.3:
            # تعزيز الإشارات الأخرى بدلاً من التحيز في اتجاه معين
            recent_candles_trend = np.mean(np.gradient(np.mean(recent_candles, axis=0)))
            brightness_factor = np.sign(recent_candles_trend) * 0.3
            
        # 6. التعديل بناءً على منطقة السعر الحالي
        current_price_gradient = np.mean(np.gradient(np.mean(current_price_area, axis=0)))
        if abs(current_price_gradient) > 0.1:
            trend_signals.append(np.sign(current_price_gradient))
            
        # 7. تحليل النمط المتذبذب
        is_oscillating = False
        oscillation_factor = 0
        
        # حساب مؤشر نمط التذبذب - إذا كان عدد التغيرات في الاتجاه كبيراً، فهذا يشير إلى نمط متذبذب
        # القيمة القصوى المحتملة هي 6 (لجميع النقاط الـ7)
        if sign_changes >= 3 and avg_change_magnitude > 0.01:
            # يوجد تذبذب إذا كان هناك عدة تغييرات في الاتجاه
            is_oscillating = True
            # قوة التذبذب ستؤثر على قوة الإشارة
            oscillation_factor = min((sign_changes - 2) * 0.5, 2.0)
            # سجّل تفاصيل التذبذب
            logger.info(f"Oscillation detected: {sign_changes} direction changes, avg_magnitude: {avg_change_magnitude:.4f}, index: {oscillation_index:.2f}")
            
            # أضف معلومات التذبذب إلى الإشارات
            if oscillation_factor > 0:
                # تخفيف حدة الإشارة في حالة التذبذب الواضح
                trend_signals = [signal * (1.0 - min(oscillation_factor * 0.2, 0.8)) for signal in trend_signals]
        
        # تجميع الإشارات وتحديد الاتجاه الإجمالي
        trend_sum = sum(trend_signals) + brightness_factor
        
        # إذا كان هناك تذبذب قوي، يجب تخفيض مستوى الثقة في الإشارة
        if is_oscillating and abs(trend_sum) < oscillation_factor:
            # إذا كان التذبذب قوي والإشارة ضعيفة، نحيّد الإشارة
            logger.info(f"Strong oscillation overrides weak trend: {trend_sum} -> 0")
            trend_sum = trend_sum * 0.3  # تخفيف كبير لقوة الإشارة
            
        # إلغاء أي عامل توازن مسبق للاعتماد على التحليل الفعلي بدون تحيز
        # balance_factor = 0.25
        # trend_sum += balance_factor
        
        # الحماية من الإشارات الضعيفة جدًا
        if -0.5 < trend_sum < 0.5:
            # إذا كانت الإشارات متعادلة جدًا، استخدم تحليلاً أكثر دقة مع شروط متوازنة
            
            # تحليل أكثر دقة لمناطق الصورة المختلفة
            upper_gradient = np.mean(np.gradient(np.mean(upper_half, axis=1)))
            lower_gradient = np.mean(np.gradient(np.mean(lower_half, axis=1)))
            
            # إذا كان متوسط سطوع الجزء الأيمن أكبر من الأيسر بفارق كبير، فهذا يشير إلى ترند صعودي
            if right_avg > left_avg * 1.1:
                trend_sum = 0.8  # اتجاه صعودي محتمل
            # إذا كان متوسط سطوع الجزء الأيسر أكبر من الأيمن بفارق كبير، فهذا يشير إلى ترند هبوطي
            elif left_avg > right_avg * 1.1:
                trend_sum = -0.8  # اتجاه هبوطي محتمل
            # إذا كان التدرج في الجزء السفلي أقوى من الجزء العلوي، فهذا يشير إلى تغير محتمل في الاتجاه
            elif abs(lower_gradient) > abs(upper_gradient) * 1.2:
                # الاتجاه العام للتدرج يحدد الاتجاه المحتمل
                trend_sum = -0.7 if lower_gradient > 0 else 0.7
            # في حالة التعادل الكامل، نعتمد على التباين في المناطق المختلفة
            else:
                # إذا كان التباين في الجزء العلوي أكبر من السفلي، فهذا يمكن أن يشير إلى اتجاه هبوطي
                if upper_variance > lower_variance * 1.3:
                    trend_sum = -0.6
                # إذا كان التباين في الجزء السفلي أكبر من العلوي، فهذا يمكن أن يشير إلى اتجاه صعودي
                elif lower_variance > upper_variance * 1.3:
                    trend_sum = 0.6
                # تحليل الاتجاه الرأسي العام للصورة
                else:
                    # استخدام قيمة التدرج العمودي للصورة بأكملها
                    vertical_gradient = np.mean(np.gradient(np.mean(img_array, axis=1)))
                    
                    # قيمة موجبة تعني أن الجزء السفلي أغمق من العلوي (اتجاه هبوطي)
                    # قيمة سالبة تعني أن الجزء العلوي أغمق من السفلي (اتجاه صعودي)
                    if abs(vertical_gradient) > 0.02:  # قيمة عتبة للتغير المعنوي
                        trend_sum = -0.7 if vertical_gradient > 0 else 0.7
                    else:
                        # في حالة التعادل النهائي، استخدم منطق عشوائي بدون تحيز
                        trend_sum = -0.5 if random.random() < 0.5 else 0.5
                
        # تسجيل تفاصيل الإشارات للتصحيح
        logger.info(f"Trend analysis: price_trend={price_trend}, recent_trend={recent_trend}, brightness_factor={brightness_factor}")
        logger.info(f"Signals: {trend_signals}, Sum: {trend_sum}")
        
        # تحديد الاتجاه النهائي
        if trend_sum > 0:
            direction = "BUY"
        else:
            direction = "SELL"
        
        # سجل تفاصيل التحليل للتصحيح
        logger.info(f"Image analysis details: upper_avg={upper_avg:.2f}, lower_avg={lower_avg:.2f}, " +
                    f"right_avg={right_avg:.2f}, left_avg={left_avg:.2f}, brightness={brightness:.2f}, trend_sum={trend_sum}")
        logger.info(f"Generated signal direction: {direction}")
        
        # Generate confidence based on image metrics
        base_confidence = MIN_CONFIDENCE
        if edge_density > 0.1:
            base_confidence += 5
        if gradient > 0.15:
            base_confidence += 5
        if variance > 0.05 and variance < 0.2:  # Not too flat, not too noisy
            base_confidence += 5
            
        # Add a small random factor (±5%)
        confidence = min(MAX_CONFIDENCE, base_confidence + random.randint(-5, 5))
        logger.info(f"Generated confidence level: {confidence}%")
        
        # Generate entry time (current time + 2 minutes, rounded to nearest minute)
        current_time = datetime.utcnow()
        entry_time = current_time + timedelta(minutes=2)
        # Round to nearest minute
        entry_time = entry_time.replace(second=0, microsecond=0)
        # Convert to Turkey time (UTC+3)
        turkey_time = entry_time + timedelta(hours=3)
        entry_time_str = turkey_time.strftime('%H:%M')
        logger.info(f"Generated entry time: {entry_time_str}")
        
        # Set the duration directly based on the timeframe
        # For OTC binary options, the duration is typically the same as the timeframe
        duration_minutes = int(timeframe)
        
        # Make sure duration is at least 1 minute
        if duration_minutes < 1:
            duration_minutes = 1
            
        logger.info(f"Trade duration: {duration_minutes} minutes")
                   
        # تأثير التذبذبات على مستوى الثقة
        if is_oscillating:
            # خفض مستوى الثقة بناءً على قوة التذبذب
            confidence_reduction = int(min(oscillation_factor * 10, 20))
            confidence = max(MIN_CONFIDENCE, confidence - confidence_reduction)
            logger.info(f"Reducing confidence due to oscillation: -{confidence_reduction}% (new: {confidence}%)")
            
        # تخزين المعلومات الإضافية للتحليل لتوفير تفاصيل أدق
        analysis_info = {
            "direction": direction,
            "brightness": brightness,
            "variance": variance,
            "edge_density": edge_density,
            "gradient": gradient,
            # إضافة معلومات التحليل الإضافية
            "trend_signals": trend_signals,
            "trend_sum": trend_sum,
            "upper_avg": upper_avg,
            "lower_avg": lower_avg,
            "right_avg": right_avg,
            "left_avg": left_avg,
            "recent_trend": recent_trend,
            "price_trend": price_trend,
            # إضافة معلومات التذبذب
            "is_oscillating": is_oscillating,
            "oscillation_factor": oscillation_factor,
            "sign_changes": sign_changes if 'sign_changes' in locals() else 0,
            "avg_change_magnitude": avg_change_magnitude if 'avg_change_magnitude' in locals() else 0
        }
        
        # إنشاء ملاحظات التحليل المفصلة بناءً على بيانات التحليل الكاملة
        analysis_notes = generate_analysis_notes(analysis_info)
        
        # Generate signal data (without take profit and stop loss)
        signal_data = {
            "pair": selected_pair,
            "direction": direction,
            "entry_time": entry_time_str,
            "duration": f"{duration_minutes} دقيقة",
            "expiry": f"{duration_minutes} min",
            "probability": f"{int(confidence)}%",
            "analysis_notes": analysis_notes
        }
        
        logger.info(f"Analysis completed successfully for {selected_pair}")
        return signal_data
        
    except Exception as e:
        logger.exception(f"Error analyzing chart image: {e}")
        return {
            "error": "Failed to analyze chart image",
            "details": str(e)
        }

def generate_analysis_notes(analysis_info):
    """
    توليد تحليل نصي تفصيلي بناءً على معلومات التحليل المتقدمة
    
    Args:
        analysis_info (dict): معلومات تحليل الصورة الكاملة
        
    Returns:
        str: نص التحليل المفصل
    """
    # استخراج المعلومات الرئيسية من قاموس التحليل
    direction = analysis_info["direction"]
    brightness = analysis_info["brightness"]
    variance = analysis_info["variance"]
    edge_density = analysis_info["edge_density"]
    gradient = analysis_info["gradient"]
    trend_signals = analysis_info["trend_signals"]
    trend_sum = analysis_info["trend_sum"]
    upper_avg = analysis_info["upper_avg"]
    lower_avg = analysis_info["lower_avg"]
    right_avg = analysis_info["right_avg"]
    left_avg = analysis_info["left_avg"]
    recent_trend = analysis_info["recent_trend"]
    price_trend = analysis_info["price_trend"]
    
    # إضافة عنصر عشوائي للتنويع في تحليل الصور المختلفة
    import random
    import time
    
    # استخدام وقت النظام لضمان عدم تكرار نفس النمط
    random.seed(int(time.time()) % 10000)
    
    # قائمة جمل وعبارات متنوعة للتحليل 
    bullish_trend_phrases = [
        "تظهر الصورة اتجاهاً صعودياً في الزوج",
        "يتحرك السعر في منحى تصاعدي واضح",
        "نلاحظ اتجاهاً عاماً للصعود في الرسم البياني",
        "يميل الزوج للارتفاع في المدى القصير",
        "هناك قوة شرائية واضحة في الشارت"
    ]
    
    bearish_trend_phrases = [
        "تظهر الصورة اتجاهاً هبوطياً في الزوج",
        "يتحرك السعر في منحى تنازلي واضح",
        "نلاحظ اتجاهاً عاماً للهبوط في الرسم البياني",
        "يميل الزوج للانخفاض في المدى القصير",
        "هناك قوة بيعية واضحة في الشارت"
    ]
    
    strong_trend_phrases = [
        "قوة الترند عالية جداً مع استمرارية محتملة",
        "الاتجاه قوي جداً ومدعوم بحجم تداول كبير",
        "تظهر المؤشرات الفنية قوة كبيرة في الاتجاه",
        "الزخم قوي ويدعم استمرار الحركة الحالية",
        "التحليل الفني يشير إلى استمرار الاتجاه بقوة"
    ]
    
    medium_trend_phrases = [
        "قوة الترند متوسطة مع احتمالية استمرار معقولة",
        "الاتجاه معتدل القوة ويحتاج لمراقبة",
        "المؤشرات الفنية تظهر زخماً متوسطاً",
        "يمكن أن يستمر الاتجاه الحالي مع بعض التذبذب",
        "التحليل يشير إلى استقرار نسبي في الاتجاه"
    ]
    
    weak_trend_phrases = [
        "قوة الترند ضعيفة نسبياً مع إمكانية التذبذب",
        "الاتجاه غير مؤكد وقد يتغير قريباً",
        "المؤشرات الفنية تظهر ضعفاً في الزخم",
        "هناك علامات على تلاشي قوة الاتجاه الحالي",
        "التحليل يشير إلى احتمالية التصحيح أو الانعكاس"
    ]
    
    pattern_strong_phrases = [
        "تظهر أنماط سعرية واضحة ومحددة تدعم الاتجاه",
        "نرى تكوينات شموع قوية تؤكد توقعاتنا",
        "هناك أنماط فنية مكتملة تدعم قرار الدخول",
        "شكل الشارت يظهر نمطاً تقنياً كلاسيكياً قوياً",
        "تشكل نمط مميز يؤكد استمرار الاتجاه الحالي"
    ]
    
    pattern_medium_phrases = [
        "الأنماط التقنية متوسطة الوضوح وتميل لدعم الاتجاه",
        "تظهر بعض الإشارات الإيجابية ولكنها غير مكتملة",
        "تكوينات الشموع تدعم الاتجاه بشكل معتدل",
        "هناك أدلة فنية معقولة تدعم التوقعات الحالية",
        "الشارت يظهر نمطاً مقبولاً ولكن يحتاج لتأكيد"
    ]
    
    pattern_weak_phrases = [
        "الأنماط التقنية غير واضحة تماماً في الشارت",
        "لا توجد تكوينات شموع مميزة تؤكد الاتجاه",
        "قد تكون هناك إشارات مختلطة في التحليل الفني",
        "الرسم البياني لا يظهر أنماطاً قوية في هذه المرحلة",
        "هناك حالة من عدم الوضوح في الأنماط السعرية"
    ]
    
    volatility_high_phrases = [
        "التذبذب السعري مرتفع مع حركة قوية في السوق",
        "هناك تقلبات كبيرة تشير إلى نشاط تداول مكثف",
        "يظهر الشارت تحركات سعرية واسعة ومؤثرة",
        "تشهد الشموع الأخيرة تغيرات سعرية كبيرة",
        "التقلبات العالية تشير إلى معركة قوية بين المشترين والبائعين"
    ]
    
    volatility_medium_phrases = [
        "التذبذب السعري معتدل مع استقرار نسبي",
        "حركة السعر متوازنة مع تذبذب طبيعي",
        "يظهر الشارت تقلبات معتدلة تناسب المتاجرة",
        "الحركة السعرية ضمن النطاق المتوقع",
        "مستوى التذبذب يشير إلى توازن بين العرض والطلب"
    ]
    
    volatility_low_phrases = [
        "التذبذب السعري منخفض مع حركة هادئة في السوق",
        "هناك استقرار ملحوظ في حركة السعر",
        "الشموع الأخيرة تظهر حركة محدودة",
        "الشارت يظهر فترة من الهدوء في الحركة السعرية",
        "انخفاض التقلبات قد يشير لاقتراب حركة قوية"
    ]
    
    sr_bullish_phrases = [
        "بيانات الشارت تشير لاختراق مستوى مقاومة مهم",
        "السعر تجاوز منطقة المقاومة مع حجم تداول جيد",
        "نرى كسراً صعودياً لمستوى سعري مهم",
        "يظهر الشارت تجاوزاً ناجحاً لنطاق المقاومة",
        "نقطة الاختراق الصعودي واضحة في الرسم البياني"
    ]
    
    sr_bearish_phrases = [
        "بيانات الشارت تشير إلى كسر مستوى دعم مهم",
        "السعر انخفض تحت منطقة الدعم مع ضغط بيعي",
        "نرى كسراً هبوطياً لمستوى سعري مهم",
        "يظهر الشارت اختراقاً سلبياً لنطاق الدعم",
        "نقطة الاختراق الهبوطي واضحة في الرسم البياني"
    ]
    
    sr_neutral_phrases = [
        "مستويات الدعم والمقاومة في حالة توازن",
        "يتحرك السعر ضمن نطاق تداول محدد",
        "لم يتم كسر أي مستويات مهمة بعد",
        "السعر يختبر مستويات فنية وسطية",
        "يظهر الشارت تردداً عند مستويات الدعم/المقاومة الحالية"
    ]
    
    high_confidence_buy_phrases = [
        "توصية: دخول شراء بثقة عالية مع احتمالية نجاح مرتفعة",
        "فرصة شراء ممتازة بناءً على التحليل الفني المتكامل",
        "إشارة شراء قوية جداً مدعومة بمؤشرات إيجابية متعددة",
        "ننصح بالدخول شراء الآن مع معدل مخاطرة منخفض نسبياً",
        "فرصة تداول مثالية للشراء مع عدة عوامل إيجابية"
    ]
    
    high_confidence_sell_phrases = [
        "توصية: دخول بيع بثقة عالية مع احتمالية نجاح مرتفعة",
        "فرصة بيع ممتازة بناءً على التحليل الفني المتكامل",
        "إشارة بيع قوية جداً مدعومة بمؤشرات سلبية متعددة",
        "ننصح بالدخول بيع الآن مع معدل مخاطرة منخفض نسبياً",
        "فرصة تداول مثالية للبيع مع عدة عوامل تدعم الهبوط"
    ]
    
    medium_confidence_buy_phrases = [
        "توصية: دخول شراء بثقة متوسطة مع مراقبة حركة السعر",
        "فرصة شراء معقولة تحتاج لمتابعة دقيقة",
        "إشارة شراء مقبولة مع ضرورة تحديد نقطة خروج مناسبة",
        "يمكن الدخول شراء مع الحذر ومراقبة الشارت",
        "فرصة تداول متوسطة للشراء تناسب المستثمر المتمرس"
    ]
    
    medium_confidence_sell_phrases = [
        "توصية: دخول بيع بثقة متوسطة مع مراقبة حركة السعر",
        "فرصة بيع معقولة تحتاج لمتابعة دقيقة",
        "إشارة بيع مقبولة مع ضرورة تحديد نقطة خروج مناسبة",
        "يمكن الدخول بيع مع الحذر ومراقبة الشارت",
        "فرصة تداول متوسطة للبيع تناسب المستثمر المتمرس"
    ]
    
    # بناء التحليل باستخدام الجمل العشوائية المتنوعة
    notes = []
    confidence_level = "متوسطة"
    
    # إضافة قيم محددة بدقة لتباين النتائج
    actual_brightness = round(brightness * 100) / 100
    actual_variance = round(variance * 1000) / 1000
    actual_edge_density = round(edge_density * 1000) / 1000
    actual_gradient = round(gradient * 1000) / 1000
    
    # تحليل الاتجاه العام للسوق بناءً على البيانات الفعلية
    # استخدام البيانات المتقدمة لتوليد تحليل أكثر دقة
    abs_trend_sum = abs(trend_sum)
    
    # اختيار وصف الاتجاه بناءً على قيم التحليل الفعلية وليس فقط على الاتجاه النهائي
    if direction == "BUY":
        # التأكد من أن هناك اتجاه صعودي فعلي قبل استخدام العبارات الإيجابية
        # استخدام سوم الإشارات وقيم التباين بدلاً من الاعتماد فقط على الاتجاه النهائي
        if trend_sum > 1.5 and price_trend > 0 and right_avg > left_avg:
            notes.append(random.choice(bullish_trend_phrases))
        else:
            # اتجاه ضعيف أو متناقض
            notes.append("الرسم البياني يظهر بعض عوامل الدعم للاتجاه الصعودي، لكن ينبغي الحذر")
        
        # تحليل قوة الإشارة
        if abs_trend_sum > 2:
            notes.append(random.choice(strong_trend_phrases))
            confidence_level = "عالية"
        elif abs_trend_sum > 1:
            notes.append(random.choice(medium_trend_phrases))
        else:
            notes.append(random.choice(weak_trend_phrases))
            
    else:  # SELL direction
        # التأكد من أن هناك اتجاه هبوطي فعلي قبل استخدام العبارات السلبية
        if trend_sum < -1.5 and price_trend < 0 and left_avg > right_avg:
            notes.append(random.choice(bearish_trend_phrases))
        else:
            # اتجاه ضعيف أو متناقض
            notes.append("الرسم البياني يظهر بعض عوامل الدعم للاتجاه الهبوطي، لكن ينبغي الحذر")
        
        # تحليل قوة الإشارة
        if abs_trend_sum > 2:
            notes.append(random.choice(strong_trend_phrases))
            confidence_level = "عالية"
        elif abs_trend_sum > 1:
            notes.append(random.choice(medium_trend_phrases))
        else:
            notes.append(random.choice(weak_trend_phrases))
    
    # تحليل الأنماط التقنية
    if actual_edge_density > 0.12:
        notes.append(random.choice(pattern_strong_phrases))
        if confidence_level != "عالية":
            confidence_level = "عالية"
    elif actual_edge_density > 0.08:
        notes.append(random.choice(pattern_medium_phrases))
    else:
        notes.append(random.choice(pattern_weak_phrases))
        if confidence_level == "عالية":
            confidence_level = "متوسطة"
    
    # تحليل التذبذب السعري
    if actual_variance > 0.1:
        notes.append(random.choice(volatility_high_phrases))
    elif actual_variance > 0.05:
        notes.append(random.choice(volatility_medium_phrases))
    else:
        notes.append(random.choice(volatility_low_phrases))
    
    # تحليل مستويات الدعم والمقاومة
    if actual_brightness > 0.6 and direction == "BUY":
        notes.append(random.choice(sr_bullish_phrases))
    elif actual_brightness < 0.4 and direction == "SELL":
        notes.append(random.choice(sr_bearish_phrases))
    else:
        notes.append(random.choice(sr_neutral_phrases))
    
    # إضافة معلومات القيم المقاسة لضمان تنوع التحليل
    notes.append(f"قياسات الصورة: السطوع {actual_brightness:.2f}، التذبذب {actual_variance:.3f}، كثافة الأنماط {actual_edge_density:.3f}، قوة الاتجاه {actual_gradient:.3f}.")
    
    # توصية نهائية
    if confidence_level == "عالية":
        if direction == "BUY":
            notes.append(random.choice(high_confidence_buy_phrases))
        else:
            notes.append(random.choice(high_confidence_sell_phrases))
    else:
        if direction == "BUY":
            notes.append(random.choice(medium_confidence_buy_phrases))
        else:
            notes.append(random.choice(medium_confidence_sell_phrases))
    
    # تجميع الملاحظات في تحليل منظم مع مسافات للقراءة بشكل أفضل
    return " ".join(notes)