"""
نظام تحديد نوع زوج التداول (OTC أو بورصة عادية)
يتعامل مع تصنيف الأزواج وإدارة طريقة عرضها في الرسائل
"""

import logging

# إعداد السجل
logger = logging.getLogger(__name__)

def identify_pair_type(pair_symbol, skip_db_check=False):
    """
    تحديد ما إذا كان الزوج من أزواج OTC أم من البورصة العادية
    
    Args:
        pair_symbol (str): رمز الزوج
        skip_db_check (bool): تخطي التحقق من قاعدة البيانات
        
    Returns:
        tuple: (is_otc, display_name) - نوع الزوج وطريقة عرضه
    """
    # التعريف الأولي
    is_otc = "-OTC" in pair_symbol
    display_name = pair_symbol
    
    # لمعالجة أزواج البورصة العادية التي تحمل لاحقة OTC عن طريق الخطأ
    if not skip_db_check:
        try:
            # محاولة التحقق من طبيعة الزوج من قاعدة البيانات
            from app import app
            from models import OTCPair, MarketPair
            
            with app.app_context():
                # نقوم أولاً بالبحث عن الزوج كما هو
                otc_pair = OTCPair.query.filter_by(symbol=pair_symbol).first()
                
                # إذا وجدنا الزوج في قائمة OTC، فهو بالتأكيد زوج OTC
                if otc_pair:
                    is_otc = True
                    display_name = pair_symbol  # الاحتفاظ باسم الزوج كما هو مع -OTC
                else:
                    # البحث عن اسم الزوج بدون لاحقة OTC في البورصة العادية
                    base_symbol = pair_symbol.replace("-OTC", "")
                    market_pair = MarketPair.query.filter_by(symbol=base_symbol).first()
                    
                    if market_pair:
                        is_otc = False
                        display_name = base_symbol  # عرض اسم الزوج بدون لاحقة OTC
                    else:
                        # إذا لم نجد الزوج في أي من القائمتين، نعتمد على الاسم
                        is_otc = "-OTC" in pair_symbol
                        # نبقي على الاسم كما هو إذا كان زوج OTC، وإلا نزيل اللاحقة
                        display_name = pair_symbol if is_otc else pair_symbol.replace("-OTC", "")
                        
                        logger.warning(f"لم يتم العثور على الزوج {pair_symbol} في قاعدة البيانات، تم اعتباره {'زوج OTC' if is_otc else 'زوج بورصة عادية'} بناءً على الاسم")
        
        except Exception as e:
            logger.error(f"حدث خطأ أثناء محاولة تحديد نوع الزوج من قاعدة البيانات: {e}")
            # في حالة حدوث أي خطأ، نعتمد على الطريقة التقليدية
            is_otc = "-OTC" in pair_symbol
            display_name = pair_symbol if is_otc else pair_symbol.replace("-OTC", "")
    
    # للتأكد من اتساق اسم العرض
    if is_otc and "-OTC" not in display_name:
        display_name = f"{display_name}-OTC"
    elif not is_otc and "-OTC" in display_name:
        display_name = display_name.replace("-OTC", "")
    
    return is_otc, display_name