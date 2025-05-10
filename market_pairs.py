"""
قوائم أزواج السوق وأزواج OTC
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# أزواج OTC الافتراضية
DEFAULT_OTC_PAIRS = [
    "EUR/USD-OTC",
    "EUR/JPY-OTC",
    "AUD/CAD-OTC",
    "USD/JPY-OTC", 
    "GBP/JPY-OTC",
    "USD/CHF-OTC",
    "EUR/GBP-OTC",
    "AUD/JPY-OTC",
    "NZD/USD-OTC",
    "GBP/USD-OTC",
    "USD/CAD-OTC",
    "EUR/AUD-OTC",
    "AUD/NZD-OTC",
    "USD/NOK-OTC",
    "USD/SEK-OTC",
    "USD/SGD-OTC",
    "USD/HUF-OTC",
    "EUR/NOK-OTC",
    "EUR/SEK-OTC",
    "EUR/ZAR-OTC",
    "USD/ZAR-OTC",
    "USD/MXN-OTC",
    "EUR/MXN-OTC",
    "USD/PLN-OTC",
    "EUR/PLN-OTC",
    "USD/CZK-OTC",
    "EUR/CZK-OTC",
    "BHD/CNY-OTC"
]

# أزواج السوق الرئيسية الافتراضية
DEFAULT_MARKET_PAIRS = [
    "EUR/USD",
    "USD/JPY",
    "GBP/USD",
    "AUD/USD",
    "USD/CAD",
    "USD/CHF",
    "NZD/USD",
    "EUR/GBP",
    "EUR/JPY",
    "GBP/JPY",
    "EUR/CHF",
    "AUD/JPY",
    "GBP/CHF",
    "EUR/CAD",
    "AUD/CAD",
    "AUD/NZD"
]

def get_default_otc_pairs():
    """
    الحصول على قائمة أزواج OTC الافتراضية
    
    Returns:
        list: قائمة أزواج OTC
    """
    return DEFAULT_OTC_PAIRS

def get_default_market_pairs():
    """
    الحصول على قائمة أزواج السوق الرئيسية الافتراضية
    
    Returns:
        list: قائمة أزواج السوق
    """
    return DEFAULT_MARKET_PAIRS

def is_otc_pair(pair_symbol):
    """
    التحقق مما إذا كان الزوج من أزواج OTC
    
    Args:
        pair_symbol (str): رمز الزوج
    
    Returns:
        bool: True إذا كان زوج OTC، False خلاف ذلك
    """
    return "-OTC" in pair_symbol or pair_symbol in DEFAULT_OTC_PAIRS

def get_all_available_pairs():
    """
    الحصول على جميع الأزواج المتاحة (OTC والسوق)
    
    Returns:
        list: قائمة جميع الأزواج
    """
    return DEFAULT_OTC_PAIRS + DEFAULT_MARKET_PAIRS

def get_pairs_by_type(pair_type="all"):
    """
    الحصول على قائمة الأزواج حسب النوع
    
    Args:
        pair_type (str): نوع الأزواج ('otc', 'market', 'all')
    
    Returns:
        list: قائمة الأزواج
    """
    if pair_type.lower() == "otc":
        return DEFAULT_OTC_PAIRS
    elif pair_type.lower() == "market":
        return DEFAULT_MARKET_PAIRS
    else:
        return DEFAULT_OTC_PAIRS + DEFAULT_MARKET_PAIRS

def update_active_pairs_in_database(db=None):
    """
    تحديث الأزواج النشطة في قاعدة البيانات
    
    Args:
        db (SQLAlchemy): نسخة قاعدة البيانات SQLAlchemy
    
    Returns:
        bool: نجاح العملية
    """
    logger.info("تحديث الأزواج النشطة في قاعدة البيانات")
    
    # إذا لم يتم توفير قاعدة بيانات، نرجع True للتوافق مع الكود الحالي
    if not db:
        logger.warning("لم يتم توفير قاعدة بيانات، تخطي التحديث")
        return True
    
    try:
        # محاولة الحصول على صنف MarketPair من ملف models
        from models import MarketPair
        
        # تحديث الأزواج OTC
        for pair in DEFAULT_OTC_PAIRS:
            # التحقق إذا كان الزوج موجود
            existing_pair = db.session.query(MarketPair).filter_by(symbol=pair).first()
            
            if existing_pair:
                # تحديث الزوج الموجود
                existing_pair.is_otc = True
                existing_pair.is_active = True
                existing_pair.updated_at = datetime.now()
            else:
                # إنشاء زوج جديد
                new_pair = MarketPair(
                    symbol=pair,
                    is_otc=True,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(new_pair)
        
        # تحديث أزواج السوق
        for pair in DEFAULT_MARKET_PAIRS:
            # التحقق إذا كان الزوج موجود
            existing_pair = db.session.query(MarketPair).filter_by(symbol=pair).first()
            
            if existing_pair:
                # تحديث الزوج الموجود
                existing_pair.is_otc = False
                existing_pair.is_active = True
                existing_pair.updated_at = datetime.now()
            else:
                # إنشاء زوج جديد
                new_pair = MarketPair(
                    symbol=pair,
                    is_otc=False,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(new_pair)
        
        # حفظ التغييرات
        db.session.commit()
        logger.info(f"تم تحديث {len(DEFAULT_OTC_PAIRS)} زوج OTC و {len(DEFAULT_MARKET_PAIRS)} زوج سوق بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تحديث الأزواج: {str(e)}")
        
        # التراجع عن التغييرات في حالة الخطأ
        if db:
            db.session.rollback()
        
        return False