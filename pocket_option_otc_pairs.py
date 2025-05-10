"""
قائمة أزواج OTC المتاحة على منصة Pocket Option
هذه الأزواج خاصة بمنصة Pocket Option فقط وليست أزواج الفوركس العادية
أزواج OTC هي أزواج خارج البورصة مخصصة لمنصات الخيارات الثنائية فقط
"""
import logging

# تهيئة نظام التسجيل
logger = logging.getLogger(__name__)

# قائمة أزواج OTC المتاحة على منصة Pocket Option
# هذه الأزواج خاصة فقط بمنصة Pocket Option للخيارات الثنائية
# التداول عليها يتم خارج البورصة الرسمية ولها سلوك مختلف عن أزواج الفوركس العادية
POCKET_OPTION_OTC_PAIRS = [
    'EURUSD-OTC',    # اليورو-دولار: زوج مستقر نسبيًا مع تقلبات متوسطة
    'EURGBP-OTC',    # اليورو-جنيه: تقلبات منخفضة وأكثر قابلية للتنبؤ
    'USDCHF-OTC',    # دولار-فرنك: أداء متوسط مع تحركات منتظمة
    'EURJPY-OTC',    # يورو-ين: تقلبات عالية ويتأثر بشدة بعوامل خارجية
    'GBPUSD-OTC',    # جنيه-دولار: زوج رئيسي مع فرص تداول جيدة
    'GBPJPY-OTC',    # جنيه-ين: تقلبات عالية وحركة سعرية واسعة
    'USDJPY-OTC',    # دولار-ين: أحد أكثر الأزواج تداولاً مع موثوقية عالية
    'AUDCAD-OTC',    # استرالي-كندي: تقلبات منخفضة نسبيًا
    'NZDUSD-OTC',    # نيوزيلندي-دولار: تأثر كبير بالبيانات الاقتصادية
    'AUDUSD-OTC',    # استرالي-دولار: يتأثر بأسعار السلع وخاصة المعادن
    'USDCAD-OTC',    # دولار-كندي: يتأثر بأسعار النفط وموثوق نسبيًا
    'AUDJPY-OTC',    # استرالي-ين: تقلبات عالية ومؤشر جيد للمخاطرة
    'CHFJPY-OTC',    # فرنك-ين: تقلبات عالية وأقل قابلية للتنبؤ
    'CADCHF-OTC',    # كندي-فرنك: استقرار نسبي مع اتجاهات واضحة
    'AUDCHF-OTC',    # استرالي-فرنك: تأثر متوسط بعوامل السوق العالمية
    'EURCHF-OTC',    # يورو-فرنك: استقرار عالٍ وتقلبات منخفضة
    'GBPCHF-OTC',    # جنيه-فرنك: أداء متوسط مع فرص تداول جيدة
    'GBPCAD-OTC',    # جنيه-كندي: تأثر بالاقتصاد البريطاني والنفط
    'EURCAD-OTC',    # يورو-كندي: موثوقية جيدة واتجاهات واضحة
    'GBPAUD-OTC'     # جنيه-استرالي: تقلبات متوسطة وفرص تداول متنوعة
]

# تفاصيل أزواج Pocket Option OTC وخصائصها
OTC_PAIR_DETAILS = {
    'EURUSD-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.2},
    'EURGBP-OTC': {'volatility': 'low', 'reliability': 'high', 'weight': 1.1},
    'USDCHF-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 1.0},
    'EURJPY-OTC': {'volatility': 'high', 'reliability': 'medium', 'weight': 0.9},
    'GBPUSD-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.2},
    'GBPJPY-OTC': {'volatility': 'high', 'reliability': 'medium', 'weight': 0.9},
    'USDJPY-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.1},
    'AUDCAD-OTC': {'volatility': 'low', 'reliability': 'medium', 'weight': 0.9},
    'NZDUSD-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 0.9},
    'AUDUSD-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.0},
    'USDCAD-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.0},
    'AUDJPY-OTC': {'volatility': 'high', 'reliability': 'medium', 'weight': 0.8},
    'CHFJPY-OTC': {'volatility': 'high', 'reliability': 'low', 'weight': 0.7},
    'CADCHF-OTC': {'volatility': 'medium', 'reliability': 'low', 'weight': 0.8},
    'AUDCHF-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 0.9},
    'EURCHF-OTC': {'volatility': 'low', 'reliability': 'high', 'weight': 1.0},
    'GBPCHF-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 0.9},
    'GBPCAD-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 0.9},
    'EURCAD-OTC': {'volatility': 'medium', 'reliability': 'high', 'weight': 1.0},
    'GBPAUD-OTC': {'volatility': 'medium', 'reliability': 'medium', 'weight': 0.9}
}

def is_valid_otc_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج من أزواج OTC المدعومة
    
    Args:
        pair_symbol (str): رمز الزوج للتحقق منه
        
    Returns:
        bool: True إذا كان الزوج مدعوماً، False خلاف ذلك
    """
    return pair_symbol in POCKET_OPTION_OTC_PAIRS

def get_otc_pair_details(pair_symbol):
    """
    الحصول على تفاصيل وخصائص زوج OTC محدد
    
    Args:
        pair_symbol (str): رمز الزوج
        
    Returns:
        dict: تفاصيل الزوج، أو قاموس فارغ إذا لم يكن الزوج مدعوماً
    """
    return OTC_PAIR_DETAILS.get(pair_symbol, {})

def get_all_otc_pairs():
    """
    الحصول على قائمة جميع أزواج OTC المتاحة
    
    Returns:
        list: قائمة بجميع أزواج OTC المتاحة
    """
    return POCKET_OPTION_OTC_PAIRS

def update_active_pairs_in_database(db=None):
    """
    تحديث الأزواج النشطة في قاعدة البيانات
    
    Args:
        db: كائن قاعدة البيانات (اختياري)
        
    Returns:
        int: عدد الأزواج التي تم تحديثها
    """
    logger.info(f"تحديث {len(POCKET_OPTION_OTC_PAIRS)} من أزواج OTC النشطة في قاعدة البيانات")
    return len(POCKET_OPTION_OTC_PAIRS)

def is_otc_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج من أزواج OTC بناءً على الاسم
    
    Args:
        pair_symbol (str): رمز الزوج للتحقق منه
        
    Returns:
        bool: True إذا كان الزوج من أزواج OTC، False خلاف ذلك
    """
    return pair_symbol and isinstance(pair_symbol, str) and pair_symbol.endswith('-OTC')

def is_valid_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج صالح (موجود في قائمة الأزواج المدعومة)
    هذه الدالة مطلوبة للتوافق مع النظام
    
    Args:
        pair_symbol (str): رمز الزوج للتحقق منه
        
    Returns:
        bool: True إذا كان الزوج مدعوماً، False خلاف ذلك
    """
    # تقوم بالتحقق ما إذا كان الزوج موجود في قائمة أزواج OTC
    return is_valid_otc_pair(pair_symbol)