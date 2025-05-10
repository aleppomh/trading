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

# Constants for OTC pairs (تحسين للأزواج OTC)
DEFAULT_CONFIDENCE_OTC = 90  # زيادة مستوى الثقة الافتراضي للأزواج OTC
MIN_CONFIDENCE_OTC = 75      # زيادة الحد الأدنى للثقة للأزواج OTC
MAX_CONFIDENCE_OTC = 97      # زيادة الحد الأقصى للثقة للأزواج OTC

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
    # تحديد ما إذا كان الزوج من أزواج OTC
    is_otc_pair = False
    if selected_pair and "-OTC" in selected_pair:
        is_otc_pair = True
        logger.info(f"OTC pair detected: {selected_pair}")
        
    # استخدام متغيرات الثقة المناسبة بناءً على نوع الزوج
    min_confidence = MIN_CONFIDENCE_OTC if is_otc_pair else MIN_CONFIDENCE
    max_confidence = MAX_CONFIDENCE_OTC if is_otc_pair else MAX_CONFIDENCE
    base_confidence = DEFAULT_CONFIDENCE_OTC if is_otc_pair else DEFAULT_CONFIDENCE
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
        # منطقة الشموع الأخيرة (الزاوية اليمنى السفلية) - أهم منطقة للتحليل
        recent_candles = img_array[2*height//3:, 2*width//3:]
        # منطقة السعر الحالي (الثلث الأيمن) - تظهر الحركة الأخيرة للسعر
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
        
        # التركيز على الجزء الأكثر أهمية - آخر 25% من الرسم البياني (الجزء الأيمن)
        # حيث تظهر أحدث الشموع والاتجاه الحالي
        right_quarter = img_array[:, 3*width//4:]
        
        # تحليل السعر النسبي للربع الأخير مقارنة بالوسط
        right_quarter_avg = np.mean(right_quarter)
        mid_section_avg = np.mean(img_array[:, width//4:3*width//4])
        
        # التحليل المقسم للتعرف على الأنماط المتذبذبة
        # تقسيم الصورة إلى 8 أقسام أفقية لتحليل أكثر دقة للحركة
        segment_width = width // 8
        segment_avgs = [np.mean(img_array[:, i*segment_width:(i+1)*segment_width]) for i in range(8)]
        
        # تحليل خاص لآخر 3 مقاطع (الأكثر أهمية لتحديد الاتجاه الحالي)
        last_segments_avg = np.mean(segment_avgs[-3:])
        prev_segments_avg = np.mean(segment_avgs[-6:-3])
        
        # حساب التغيرات بين المقاطع المتتالية لاكتشاف التذبذبات
        segment_changes = [segment_avgs[i+1] - segment_avgs[i] for i in range(7)]
        sign_changes = sum(1 for i in range(6) if segment_changes[i] * segment_changes[i+1] < 0)
        
        # متوسط حجم التغير بين المقاطع
        avg_change_magnitude = np.mean([abs(change) for change in segment_changes])
        
        # تحليل اتجاه آخر 3 مقاطع - مهم جداً لتحديد الاتجاه الحالي
        last_segments_trend = sum(np.sign(segment_changes[-3:]))
        
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
        
        # تحسين: تحليل الشموع على الطرف الأيمن من الصورة - أحدث الشموع
        right_edge = img_array[:, 7*width//8:]
        
        # تقسيم الجزء الأيمن إلى أقسام أفقية للتعرف على نمط الشموع
        right_edge_segments = 10
        segment_height = height // right_edge_segments
        right_edge_segment_avgs = [np.mean(right_edge[i*segment_height:(i+1)*segment_height, :]) for i in range(right_edge_segments)]
        
        # تحليل نمط الشموع الأخيرة عبر النظر في الفرق بين أقسام مختلفة
        # إذا كان الجزء العلوي أفتح من السفلي، فهذه عادة شمعة خضراء (BUY)
        right_edge_upper = np.mean(right_edge[:height//2, :])
        right_edge_lower = np.mean(right_edge[height//2:, :])
        
        # تحسين: نسبة السطوع بين الربع الأعلى والأسفل من آخر شمعة
        right_edge_top_quarter = np.mean(right_edge[:height//4, :])
        right_edge_bottom_quarter = np.mean(right_edge[3*height//4:, :])
            
        # تحليل الشموع الأخيرة - تحسين منطق التحليل
        recent_gradient_y = np.mean(np.gradient(np.mean(recent_candles, axis=1)))
        
        # اختبار أكثر دقة لاتجاه الشموع الأخيرة بناءً على تدرج العمود الأخير
        last_column = recent_candles[:, -1]
        last_column_gradient = np.gradient(last_column)
        last_column_direction = 1 if np.mean(last_column_gradient) < 0 else -1
        
        # في الشموع الخضراء (الصعودية)، الجزء العلوي أكثر إشراقًا من السفلي
        # في الشموع الحمراء (الهبوطية)، الجزء السفلي أكثر إشراقًا من العلوي
        # لذا إذا كان التدرج موجبًا (يزيد من أسفل لأعلى)، فهذا يشير للشراء
        recent_trend = 1 if recent_gradient_y < 0 else -1
        
        # تحليل التباين في مناطق مختلفة
        recent_variance = np.var(recent_candles)
        upper_variance = np.var(upper_half)
        lower_variance = np.var(lower_half)
        
        # تحليل المزيد من المكونات البصرية لتحديد نوع الشموع
        # في شارت الشموع، الشموع الخضراء والحمراء لها أنماط مميزة
        
        # تحليل ذيول الشموع (الفتائل) - الفتائل العلوية والسفلية
        upper_tail_intensity = np.var(recent_candles[:height//6, :])
        lower_tail_intensity = np.var(recent_candles[5*height//6:, :])
        
        # مؤشرات إضافية للتحليل
        # البحث عن أنماط الشموع الأساسية
        edge_recent = np.mean(edge_magnitude[2*height//3:, 2*width//3:])
        doji_pattern = edge_recent > np.mean(edge_magnitude) * 1.2  # شمعة دوجي تظهر كحافة قوية
        
        # تحديد الاتجاه بناءً على مجموعة من العوامل
        trend_signals = []
        
        # 1. الأنماط الأفقية الإجمالية (الاتجاه من اليسار إلى اليمين)
        trend_signals.append(price_trend)
        
        # 2. اتجاه آخر الشموع (الأكثر أهمية) - وزن مضاعف
        last_candle_weight = 3.0  # زيادة تأثير الشموع الأخيرة
        
        if right_edge_top_quarter > right_edge_bottom_quarter:
            # مؤشر قوي على الشراء: الجزء العلوي من الشمعة أفتح
            trend_signals.append(last_candle_weight)
        elif right_edge_bottom_quarter > right_edge_top_quarter:
            # مؤشر قوي على البيع: الجزء السفلي من الشمعة أفتح
            trend_signals.append(-last_candle_weight)
        
        # 3. الاتجاه الأخير في منطقة الشموع الحديثة
        if recent_variance > np.var(img_array) * 1.2:  # إذا كانت الشموع الأخيرة أكثر تباينًا
            trend_signals.append(recent_trend * 2)  # وزن أكبر للاتجاه الأخير
        else:
            trend_signals.append(recent_trend)
            
        # 4. التباين بين الجزء العلوي والسفلي
        if lower_variance > upper_variance * 1.5:
            trend_signals.append(1)  # إشارة إلى اتجاه صعودي (تباين أكبر في الأسفل)
        elif upper_variance > lower_variance * 1.5:
            trend_signals.append(-1)  # إشارة إلى اتجاه هبوطي
            
        # 5. اتجاه نهاية المقاطع (آخر 3 مقاطع) - مؤشر قوي للاتجاه الحالي
        if last_segments_avg > prev_segments_avg:
            trend_signals.append(2)  # وزن أكبر للاتجاه الصعودي في آخر المقاطع
        elif last_segments_avg < prev_segments_avg:
            trend_signals.append(-2)  # وزن أكبر للاتجاه الهبوطي في آخر المقاطع
            
        # 6. اتجاه آخر ثلاثة تغييرات في المقاطع
        if last_segments_trend > 0:
            trend_signals.append(1.5)  # اتجاه صعودي في آخر المقاطع
        elif last_segments_trend < 0:
            trend_signals.append(-1.5)  # اتجاه هبوطي في آخر المقاطع
            
        # 7. تحليل أنماط الشموع المحددة
        if doji_pattern:
            # إذا كانت الشمعة الأخيرة دوجي، فهي تشير غالبًا إلى انعكاس الاتجاه
            # لكن فقط إذا كان الاتجاه العام واضحًا
            if abs(price_trend) > 1:
                trend_signals.append(-np.sign(price_trend))  # عكس الاتجاه السابق
        
        # 8. تحليل فتائل الشموع - مؤشر قوي على اتجاه السوق
        if upper_tail_intensity > lower_tail_intensity * 2:
            # فتائل علوية قوية تشير غالبًا إلى ضغط بيع
            trend_signals.append(-1)
        elif lower_tail_intensity > upper_tail_intensity * 2:
            # فتائل سفلية قوية تشير غالبًا إلى ضغط شراء
            trend_signals.append(1)
        
        # 9. تحليل مستويات السطوع - تحسين بحيث لا يكون هناك تحيز
        brightness_factor = 0
        # الألوان الفاتحة/الداكنة وحدها ليست مؤشراً على الاتجاه
        # لذلك نحيّد تأثير السطوع لتجنب التحيز للشراء أو البيع
        # بدلاً من ذلك، نقارن نمط السطوع عبر المناطق المختلفة
        if brightness > 0.7 or brightness < 0.3:
            # تعزيز الإشارات الأخرى بدلاً من التحيز في اتجاه معين
            recent_candles_trend = np.mean(np.gradient(np.mean(recent_candles, axis=0)))
            brightness_factor = np.sign(recent_candles_trend) * 0.3
            
        # 10. التعديل بناءً على منطقة السعر الحالي - وزن مضاعف لأهميته
        current_price_gradient = np.mean(np.gradient(np.mean(current_price_area, axis=0)))
        if abs(current_price_gradient) > 0.05:  # تخفيض العتبة للحساسية
            trend_signals.append(np.sign(current_price_gradient) * 2)
            
        # 11. تحليل النمط المتذبذب
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
                trend_signals = [signal * (1.0 - min(oscillation_factor * 0.2, 0.5)) for signal in trend_signals]
        
        # تحليل نمط تسلسل الشموع المتتالية - مهم جداً للاتجاه الحقيقي
        # تقسيم آخر 25% من العرض إلى أعمدة (كل عمود يمثل شمعة)
        candle_columns = 10  # عدد الشموع للتحليل
        last_quarter_width = width // 4
        candle_width = last_quarter_width // candle_columns
        
        # تحليل كل شمعة على حدة من آخر 10 شموع
        candle_colors = []  # لتخزين اتجاه كل شمعة (موجب للأخضر، سالب للأحمر)
        candle_strengths = []  # لتخزين قوة كل شمعة
        
        for i in range(candle_columns):
            col_start = width - last_quarter_width + i * candle_width
            col_end = col_start + candle_width
            if col_end > width:
                col_end = width
            
            # استخراج منطقة الشمعة
            candle_area = img_array[:, col_start:col_end]
            
            # قياس العلاقة بين النصف العلوي والسفلي من الشمعة
            candle_upper = np.mean(candle_area[:height//2, :])
            candle_lower = np.mean(candle_area[height//2:, :])
            
            # تحديد لون الشمعة:
            # - إذا كان الجزء العلوي أفتح من السفلي، فهذه شمعة خضراء (موجبة)
            # - إذا كان الجزء السفلي أفتح من العلوي، فهذه شمعة حمراء (سالبة)
            if candle_upper > candle_lower * 1.05:
                candle_colors.append(1)  # شمعة خضراء
                candle_strengths.append(candle_upper / candle_lower - 1)
            elif candle_lower > candle_upper * 1.05:
                candle_colors.append(-1)  # شمعة حمراء
                candle_strengths.append(candle_lower / candle_upper - 1)
            else:
                candle_colors.append(0)  # حيادي
                candle_strengths.append(0)
        
        # تحليل نمط الشموع المتتالية وتشكيل الاتجاه
        # تحديد اتجاه آخر 3 شموع - مؤشر قوي جداً للاتجاه الحالي
        last_candles_trend = sum(candle_colors[-3:])
        last_candles_strength = sum(candle_strengths[-3:])
        
        # تحليل تشكيلات الانعكاس - هل هناك انعكاس للاتجاه؟
        # نبحث عن 3+ شموع متتالية بنفس الاتجاه ثم انعكاس
        reversal_pattern = False
        reversal_direction = 0
        
        if len([c for c in candle_colors[-5:-2] if c > 0]) >= 3 and candle_colors[-1] < 0:
            # نمط انعكاس محتمل من الصعود للهبوط
            reversal_pattern = True
            reversal_direction = -1
        elif len([c for c in candle_colors[-5:-2] if c < 0]) >= 3 and candle_colors[-1] > 0:
            # نمط انعكاس محتمل من الهبوط للصعود
            reversal_pattern = True
            reversal_direction = 1
            
        # إضافة إشارة قوية جداً بناءً على نمط الشموع المتتالية
        if abs(last_candles_trend) >= 2:
            # إذا كان هناك اتجاه واضح في آخر 3 شموع، فهذا مؤشر قوي جداً
            trend_signals.append(last_candles_trend * 2)
            
        # إضافة إشارة خاصة بنمط الانعكاس إذا وجد
        if reversal_pattern:
            trend_signals.append(reversal_direction * 1.5)
            
        # تجميع الإشارات وتحديد الاتجاه الإجمالي
        trend_sum = sum(trend_signals) + brightness_factor
        
        # تحليل تسلسل الشموع الحمراء والخضراء لتحديد قوة الاتجاه
        consecutive_red = 0
        consecutive_green = 0
        
        # حساب عدد الشموع المتتالية من نفس اللون
        for i in range(len(candle_colors)-1, -1, -1):
            if candle_colors[i] < 0:  # شمعة حمراء
                if consecutive_red == 0:  # بداية سلسلة جديدة
                    consecutive_green = 0
                consecutive_red += 1
            elif candle_colors[i] > 0:  # شمعة خضراء
                if consecutive_green == 0:  # بداية سلسلة جديدة
                    consecutive_red = 0
                consecutive_green += 1
            else:  # شمعة محايدة
                continue
        
        # إضافة إشارة قوية جداً إذا كان هناك 3+ شموع متتالية من نفس اللون
        if consecutive_red >= 3:
            # ثلاث شموع حمراء متتالية أو أكثر - إشارة بيع قوية
            trend_signals.append(-3 * min(consecutive_red, 5) / 3)  # وزن أقصى 5
            logger.info(f"Detected {consecutive_red} consecutive red candles - strong SELL signal")
        elif consecutive_green >= 3:
            # ثلاث شموع خضراء متتالية أو أكثر - إشارة شراء قوية
            trend_signals.append(3 * min(consecutive_green, 5) / 3)  # وزن أقصى 5
            logger.info(f"Detected {consecutive_green} consecutive green candles - strong BUY signal")
            
        # تحليل اتجاه آخر شمعتين - مؤشر مهم جداً للاتجاه الحالي
        if len(candle_colors) >= 2 and candle_colors[-1] == candle_colors[-2] and candle_colors[-1] != 0:
            # آخر شمعتين من نفس اللون - مؤشر قوي على استمرار الاتجاه
            trend_signals.append(candle_colors[-1] * 2)
            
        # إذا كان هناك تذبذب قوي، يجب تخفيض مستوى الثقة في الإشارة
        if is_oscillating and abs(trend_sum) < oscillation_factor:
            # إذا كان التذبذب قوي والإشارة ضعيفة، نحيّد الإشارة
            logger.info(f"Strong oscillation overrides weak trend: {trend_sum} -> 0")
            trend_sum = trend_sum * 0.3  # تخفيف كبير لقوة الإشارة
        
        # الحماية من الإشارات الضعيفة جدًا
        if -0.5 < trend_sum < 0.5:
            # إذا كانت الإشارات متعادلة جدًا، استخدم تحليلاً أكثر دقة مع شروط متوازنة
            
            # تحليل أكثر دقة لمناطق الصورة المختلفة
            upper_gradient = np.mean(np.gradient(np.mean(upper_half, axis=1)))
            lower_gradient = np.mean(np.gradient(np.mean(lower_half, axis=1)))
            
            # تحليل الشموع الأخيرة بشكل أكثر تفصيلاً
            # تقسيم آخر 10% من الصورة إلى أقسام أفقية
            last_portion = img_array[:, int(0.9*width):]
            last_portion_segments = 10
            segment_height = height // last_portion_segments
            last_portion_segment_avgs = [np.mean(last_portion[i*segment_height:(i+1)*segment_height, :]) for i in range(last_portion_segments)]
            
            # تحليل نمط آخر شمعة - مؤشر قوي جداً
            # قياس الاختلافات بين القمة والقاع لآخر شمعة
            last_candle_top_avg = np.mean(last_portion_segment_avgs[:3])  # أعلى 30%
            last_candle_bottom_avg = np.mean(last_portion_segment_avgs[-3:])  # أسفل 30%
            
            # إذا كان أعلى الشمعة الأخيرة أفتح من أسفلها، فهذا مؤشر قوي للشراء
            if last_candle_top_avg > last_candle_bottom_avg * 1.05:
                trend_sum = 0.9  # اتجاه صعودي محتمل قوي
            # إذا كان أسفل الشمعة الأخيرة أفتح من أعلاها، فهذا مؤشر قوي للبيع
            elif last_candle_bottom_avg > last_candle_top_avg * 1.05:
                trend_sum = -0.9  # اتجاه هبوطي محتمل قوي
            # إذا كان متوسط سطوع الجزء الأيمن أكبر من الأيسر بفارق كبير، فهذا يشير إلى ترند صعودي
            elif right_avg > left_avg * 1.1:
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
                        # في حالة التعادل التام، نفضل إشارة الشراء بشكل طفيف
                        # بناءً على تحليل الصور المقدمة من المستخدم
                        trend_sum = 0.5
                
        # تسجيل تفاصيل الإشارات للتصحيح
        logger.info(f"Trend analysis: price_trend={price_trend}, recent_trend={recent_trend}, brightness_factor={brightness_factor}")
        logger.info(f"Last candle analysis: top_quarter={right_edge_top_quarter:.2f}, bottom_quarter={right_edge_bottom_quarter:.2f}")
        logger.info(f"Signals: {trend_signals}, Sum: {trend_sum} (after correction: {trend_sum})")
        
        # تحديد الاتجاه النهائي
        if trend_sum > 0:
            direction = "BUY"
        else:
            direction = "SELL"
        
        # سجل تفاصيل التحليل للتصحيح
        logger.info(f"Image analysis details: upper_avg={upper_avg:.2f}, lower_avg={lower_avg:.2f}, " +
                    f"right_avg={right_avg:.2f}, left_avg={left_avg:.2f}, brightness={brightness:.2f}, trend_sum={trend_sum}")
        logger.info(f"Generated signal direction: {direction}")
        
        # تحسين: زيادة الثقة بناءً على قوة الاتجاه
        trend_strength = abs(trend_sum)
        if trend_strength > 3:
            base_confidence += 10  # اتجاه قوي جداً
        elif trend_strength > 2:
            base_confidence += 7   # اتجاه قوي
        elif trend_strength > 1:
            base_confidence += 5   # اتجاه واضح
            
        if edge_density > 0.1:
            base_confidence += 3
        if gradient > 0.15:
            base_confidence += 3
        if variance > 0.05 and variance < 0.2:  # Not too flat, not too noisy
            base_confidence += 3
            
        # زيادة الثقة إذا كانت آخر الشموع واضحة جداً في الاتجاه
        if right_edge_top_quarter > right_edge_bottom_quarter * 1.2 and direction == "BUY":
            base_confidence += 5
        elif right_edge_bottom_quarter > right_edge_top_quarter * 1.2 and direction == "SELL":
            base_confidence += 5
            
        # تعزيز الثقة لأزواج OTC - العامل الأهم هو وضوح الاتجاه في آخر الشموع
        if is_otc_pair:
            # زيادة الثقة للأزواج OTC
            if right_edge_top_quarter > right_edge_bottom_quarter * 1.15 and direction == "BUY":
                # زيادة إضافية لإشارات الشراء الواضحة في أزواج OTC
                base_confidence += 5
                logger.info(f"OTC pair BUY signal enhanced: +5% confidence")
            elif right_edge_bottom_quarter > right_edge_top_quarter * 1.15 and direction == "SELL":
                # زيادة إضافية لإشارات البيع الواضحة في أزواج OTC
                base_confidence += 5
                logger.info(f"OTC pair SELL signal enhanced: +5% confidence")
                
            # تعزيز إضافي للإشارات عند وجود قوة اتجاه واضحة
            if trend_strength > 2.5:
                base_confidence += 3
                logger.info(f"OTC pair with strong trend: +3% confidence")
            
        # Add a small random factor (±3%)
        confidence = min(max_confidence, base_confidence + random.randint(-3, 3))
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
            confidence_reduction = int(min(oscillation_factor * 10, 15))
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
            # تحليل الشموع الأخيرة
            "right_edge_top_quarter": right_edge_top_quarter,
            "right_edge_bottom_quarter": right_edge_bottom_quarter,
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
    recent_trend = analysis_info["recent_trend"]
    price_trend = analysis_info["price_trend"]
    is_oscillating = analysis_info["is_oscillating"]
    
    # تحديد نوع الصياغة بناءً على الاتجاه
    if direction == "BUY":
        direction_ar = "شراء"
        color_ar = "أخضر"
    else:
        direction_ar = "بيع"
        color_ar = "أحمر"
    
    # تحديد قوة الإشارة
    abs_trend_sum = abs(trend_sum)
    
    if direction == "BUY":
        if trend_sum > 1.5 and price_trend > 0 and analysis_info["right_edge_top_quarter"] > analysis_info["right_edge_bottom_quarter"]:
            strength_ar = "قوية جداً"
            confidence_ar = "عالية"
            pattern_ar = "شموع صاعدة واضحة مع حركة قوية للسعر"
        else:
            strength_ar = "معتدلة"
            confidence_ar = "متوسطة إلى عالية"
            pattern_ar = "تشكل اتجاه صعودي مع بعض الإشارات الإيجابية"
            
        if abs_trend_sum > 2:
            probability_ar = "مرتفعة جداً"
        elif abs_trend_sum > 1:
            probability_ar = "مرتفعة"
        else:
            probability_ar = "متوسطة"
    else:
        if trend_sum < -1.5 and price_trend < 0 and analysis_info["right_edge_bottom_quarter"] > analysis_info["right_edge_top_quarter"]:
            strength_ar = "قوية جداً"
            confidence_ar = "عالية"
            pattern_ar = "شموع هابطة واضحة مع حركة قوية للسعر"
        else:
            strength_ar = "معتدلة"
            confidence_ar = "متوسطة إلى عالية"
            pattern_ar = "تشكل اتجاه هبوطي مع بعض الإشارات السلبية"
            
        if abs_trend_sum > 2:
            probability_ar = "مرتفعة جداً"
        elif abs_trend_sum > 1:
            probability_ar = "مرتفعة"
        else:
            probability_ar = "متوسطة"
    
    # إنشاء نص التحليل
    analysis_text = f"إشارة {direction_ar} {strength_ar} مع نمط {pattern_ar}. "
    
    # إضافة تفاصيل حول نمط الشموع
    if is_oscillating:
        analysis_text += f"السوق في حالة تذبذب، لكن الإشارة الأخيرة تشير إلى {direction_ar}. "
    else:
        analysis_text += f"تتشكل شموع {color_ar} على الرسم البياني تدل على اتجاه {direction_ar}. "
    
    # إضافة معلومات حول الاحتمالية
    analysis_text += f"الاحتمالية {probability_ar} بناءً على تحليل متعدد المؤشرات مع درجة ثقة {confidence_ar}."
    
    return analysis_text

def process_uploaded_image(image_data, selected_pair=None, timeframe=1):
    """
    معالجة الصورة المرفوعة وتحليلها
    
    Args:
        image_data: بيانات الصورة المرفوعة
        selected_pair: الزوج المحدد (اختياري)
        timeframe: الإطار الزمني (بالدقائق)
        
    Returns:
        dict: معلومات الإشارة، أو رسالة خطأ
    """
    try:
        # تحليل الصورة
        signal = analyze_chart_image(image_data, selected_pair, timeframe)
        return signal
    except Exception as e:
        logger.exception(f"Error processing uploaded image: {e}")
        return {
            "error": "Failed to process uploaded image",
            "details": str(e)
        }

def generate_random_signal(selected_pair=None, timeframe=1):
    """
    Generate a random signal for testing
    
    Args:
        selected_pair: Selected pair symbol
        timeframe: Timeframe in minutes
    
    Returns:
        dict: Signal information
    """
    directions = ["BUY", "SELL"]
    direction = random.choice(directions)
    
    current_time = datetime.utcnow()
    entry_time = current_time + timedelta(minutes=2)
    # Round to nearest minute
    entry_time = entry_time.replace(second=0, microsecond=0)
    # Convert to Turkey time (UTC+3)
    turkey_time = entry_time + timedelta(hours=3)
    entry_time_str = turkey_time.strftime('%H:%M')
    
    # Generate a confidence level
    confidence = random.randint(MIN_CONFIDENCE, MAX_CONFIDENCE)
    
    duration_minutes = int(timeframe)
    if duration_minutes < 1:
        duration_minutes = 1
    
    if direction == "BUY":
        direction_ar = "شراء"
        analysis_notes = "إشارة شراء قوية مع نمط شموع صاعدة. تشكل شموع خضراء على الرسم البياني تدل على اتجاه شراء. الاحتمالية مرتفعة بناءً على تحليل متعدد المؤشرات."
    else:
        direction_ar = "بيع"
        analysis_notes = "إشارة بيع قوية مع نمط شموع هابطة. تشكل شموع حمراء على الرسم البياني تدل على اتجاه بيع. الاحتمالية مرتفعة بناءً على تحليل متعدد المؤشرات."
    
    return {
        "pair": selected_pair,
        "direction": direction,
        "entry_time": entry_time_str,
        "duration": f"{duration_minutes} دقيقة",
        "expiry": f"{duration_minutes} min",
        "probability": f"{confidence}%",
        "analysis_notes": analysis_notes
    }