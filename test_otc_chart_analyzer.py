import os
import sys
import json
from chart_analyzer import analyze_chart_image

def test_analyze_otc_chart(image_path, pair_symbol):
    """
    اختبار تحليل الشارت لأزواج OTC
    
    Args:
        image_path: مسار الصورة
        pair_symbol: رمز الزوج مع لاحقة OTC
    """
    print(f"\n=== تحليل شارت {pair_symbol} ===")
    
    # قراءة بيانات الصورة
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # تحليل الصورة باستخدام الأداة المطورة
    result = analyze_chart_image(image_data, pair_symbol, timeframe=1)
    
    # عرض نتيجة التحليل
    print(f"الاتجاه: {result['direction']}")
    print(f"الزوج: {result['pair']}")
    print(f"وقت الدخول: {result['entry_time']}")
    print(f"المدة: {result['duration']}")
    print(f"الاحتمالية: {result['probability']}")
    print(f"التحليل: {result['analysis_notes']}")
    
    return result

if __name__ == "__main__":
    # اختبار تحليل الأزواج الثلاثة
    print("بدء اختبار أداة تحليل الشارت للأزواج OTC...")

    # EUR/JPY OTC
    eurjpy_result = test_analyze_otc_chart('temp_images/eurjpy_otc.jpg', 'EUR/JPY-OTC')
    
    # AUD/CAD OTC
    audcad_result = test_analyze_otc_chart('temp_images/audcad_otc.jpg', 'AUD/CAD-OTC')
    
    # BHD/CNY OTC
    bhdcny_result = test_analyze_otc_chart('temp_images/bhdcny_otc.jpg', 'BHD/CNY-OTC')
    
    print("\n=== ملخص النتائج ===")
    print(f"EUR/JPY-OTC: {eurjpy_result['direction']} بنسبة {eurjpy_result['probability']}")
    print(f"AUD/CAD-OTC: {audcad_result['direction']} بنسبة {audcad_result['probability']}")
    print(f"BHD/CNY-OTC: {bhdcny_result['direction']} بنسبة {bhdcny_result['probability']}")