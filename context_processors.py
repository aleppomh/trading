"""
معالجات السياق العام للتطبيق
تستخدم لحقن البيانات المشتركة في جميع قوالب التطبيق
"""
import logging
from flask import request

logger = logging.getLogger(__name__)

def setup_ad_context_processors(app):
    """
    إعداد معالجات السياق الخاصة بالإعلانات
    
    Args:
        app: تطبيق Flask
    """
    @app.context_processor
    def inject_ad_settings():
        """
        حقن إعدادات الإعلانات في جميع القوالب
        """
        try:
            # Import here to avoid circular imports
            from admin_ads import get_ad_settings, should_show_ads
            
            settings = get_ad_settings()
            return {
                'ad_settings': settings,
                'should_show_ads': should_show_ads,
                'page_type': request.endpoint
            }
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات الإعلانات: {e}")
            return {
                'ad_settings': None,
                'should_show_ads': lambda x: False,
                'page_type': request.endpoint
            }