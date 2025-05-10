"""
اختبار المحلل المطور للرسوم البيانية
"""

import io
import os
import sys
import logging
import numpy as np
from PIL import Image
from datetime import datetime

# استيراد المحلل المطور
from improved_chart_analyzer import analyze_chart_image

# تكوين نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_chart_image(image_path, pair_name, timeframe=1):
    """
    اختبار تحليل الرسم البياني باستخدام المحلل المطور
    
    Args:
        image_path: مسار ملف الصورة
        pair_name: اسم زوج التداول
        timeframe: الإطار الزمني بالدقائق
    """
    try:
        # قراءة ملف الصورة
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        # التحقق من حجم الصورة
        image_size = len(image_data)
        logger.info(f"Image size: {image_size} bytes")
        
        if image_size == 0:
            logger.error("Image file is empty!")
            return None
            
        # تحليل الرسم البياني باستخدام المحلل المطور
        logger.info(f"==== تحليل الرسم البياني بالمحلل المطور ====")
        logger.info(f"الصورة: {os.path.basename(image_path)}")
        logger.info(f"الزوج: {pair_name}")
        logger.info(f"الإطار الزمني: {timeframe} دقيقة")
        
        # تنفيذ التحليل
        result = analyze_chart_image(image_data, pair_name, timeframe)
        
        # عرض نتائج التحليل
        logger.info("==== نتائج التحليل ====")
        logger.info(f"الاتجاه: {result.get('direction', 'غير معروف')}")
        logger.info(f"الاحتمالية: {result.get('probability', 'غير معروفة')}")
        logger.info(f"وقت الدخول: {result.get('entry_time', 'غير معروف')}")
        logger.info(f"المدة: {result.get('duration', 'غير معروفة')} دقيقة")
        logger.info(f"ملاحظات التحليل: {result.get('analysis_notes', 'لا توجد')}")
        
        # عرض تفاصيل إضافية إذا كانت متوفرة
        if 'analysis_info' in result:
            info = result['analysis_info']
            logger.info("==== تفاصيل التحليل ====")
            logger.info(f"مجموع الاتجاه: {info.get('trend_sum', 'غير متوفر')}")
            logger.info(f"مؤشر التذبذب: {info.get('oscillation_index', 'غير متوفر')}")
            logger.info(f"عدد الشموع المتتالية: {info.get('consecutive_candles', 'غير متوفر')}")
            logger.info(f"حالة التذبذب: {'متذبذب' if info.get('is_oscillating', False) else 'غير متذبذب'}")
            
        logger.info("========================")
        
        return result
        
    except Exception as e:
        logger.error(f"خطأ أثناء اختبار الصورة: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# قائمة بالصور للاختبار
test_images = [
    {
        "path": "attached_assets/Screenshot_2025-05-08-03-34-00-378_com.android.chrome.jpg",
        "pair": "AUD/NZD OTC",
        "expected": "SELL"
    },
    {
        "path": "attached_assets/Screenshot_2025-05-08-03-28-18-338_com.android.chrome.jpg",
        "pair": "AUD/NZD OTC",
        "expected": "SELL"
    },
    {
        "path": "attached_assets/Screenshot_2025-05-07-02-07-33-867_com.android.chrome.jpg",
        "pair": "AUD/NZD OTC",
        "expected": "SELL"
    },
    {
        "path": "attached_assets/Screenshot_2025-05-07-13-08-49-405_com.android.chrome-edit.jpg",
        "pair": "EUR/USD OTC",
        "expected": "BUY"
    },
    {
        "path": "attached_assets/Screenshot_2025-05-08-02-57-19-535_com.android.chrome.jpg",
        "pair": "EUR/USD OTC",
        "expected": "BUY"
    }
]

if __name__ == "__main__":
    # اختبار جميع الصور في القائمة
    results = []
    for test in test_images:
        try:
            logger.info(f"\n\n==== اختبار الصورة: {test['path']} ====")
            result = test_chart_image(test["path"], test["pair"])
            if result:
                correct = (result["direction"] == test["expected"])
                logger.info(f"النتيجة المتوقعة: {test['expected']}, النتيجة الفعلية: {result['direction']}")
                logger.info(f"التوافق: {'✓' if correct else '✗'}")
                
                results.append({
                    "path": test["path"],
                    "pair": test["pair"],
                    "expected": test["expected"],
                    "actual": result["direction"],
                    "probability": result["probability"],
                    "correct": correct
                })
        except Exception as e:
            logger.error(f"خطأ في اختبار الصورة {test['path']}: {str(e)}")
    
    # عرض ملخص النتائج
    logger.info("\n\n==== ملخص نتائج الاختبار ====")
    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    
    if total_count > 0:
        accuracy = correct_count / total_count * 100
        logger.info(f"الدقة الإجمالية: {accuracy:.2f}% ({correct_count}/{total_count})")
        
        for i, r in enumerate(results):
            logger.info(f"{i+1}. {r['pair']} - المتوقع: {r['expected']}, الفعلي: {r['actual']} ({r['probability']}) - {'✓' if r['correct'] else '✗'}")
    else:
        logger.info("لم يتم إجراء أي اختبار بنجاح.")