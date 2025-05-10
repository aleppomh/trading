"""
وحدة إدارة إعدادات الإعلانات في لوحة التحكم
"""

import logging
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

# Importamos solo el modelo sin importar db directamente
from models import AdSettings

logger = logging.getLogger(__name__)

# تعريف مسار صفحة إعدادات الإعلانات
def admin_ads_settings():
    """صفحة إعدادات الإعلانات في لوحة التحكم"""
    
    try:
        # استيراد داخلي لتجنب التعارضات الدائرية
        from app import db
        
        # الحصول على الإعدادات الحالية
        settings = AdSettings.query.first()
        
        # إذا لم تكن هناك إعدادات، قم بإنشاء إعدادات افتراضية
        if not settings:
            settings = AdSettings()
            settings.ads_enabled = False
            settings.max_ads_per_page = 3
            settings.show_in_homepage = True
            settings.show_in_dashboard = False
            settings.show_in_results = True
            db.session.add(settings)
            db.session.commit()
    except Exception as e:
        logger.error(f"خطأ في تهيئة إعدادات الإعلانات: {e}")
        # إنشاء كائن فارغ مؤقت لتجنب الأخطاء
        settings = AdSettings()
        settings.ads_enabled = False
        settings.max_ads_per_page = 0
    
    # إذا كان الطلب من نوع POST، قم بتحديث الإعدادات
    if request.method == 'POST':
        try:
            # تحديث البيانات من النموذج
            settings.ads_enabled = 'ads_enabled' in request.form
            settings.show_in_homepage = 'show_in_homepage' in request.form
            settings.show_in_dashboard = 'show_in_dashboard' in request.form
            settings.show_in_results = 'show_in_results' in request.form
            
            # تحديث معرفات AdSense
            settings.adsense_client_id = request.form.get('adsense_client_id', '')
            settings.adsense_slot_id_header = request.form.get('adsense_slot_id_header', '')
            settings.adsense_slot_id_sidebar = request.form.get('adsense_slot_id_sidebar', '')
            settings.adsense_slot_id_content = request.form.get('adsense_slot_id_content', '')
            settings.adsense_slot_id_footer = request.form.get('adsense_slot_id_footer', '')
            
            # تحديث الحد الأقصى للإعلانات في الصفحة
            try:
                settings.max_ads_per_page = int(request.form.get('max_ads_per_page', 3))
            except ValueError:
                settings.max_ads_per_page = 3
            
            # حفظ التغييرات
            db.session.commit()
            
            # عرض رسالة نجاح
            flash('تم حفظ إعدادات الإعلانات بنجاح', 'success')
            logger.info(f"تم تحديث إعدادات الإعلانات بواسطة {current_user.username}")
            
        except Exception as e:
            # في حالة حدوث خطأ، قم بالتراجع عن التغييرات
            db.session.rollback()
            flash(f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}', 'danger')
            logger.error(f"خطأ في حفظ إعدادات الإعلانات: {e}")
    
    # عرض صفحة الإعدادات
    return render_template('admin/ads_settings.html', settings=settings)

# دالة مساعدة للحصول على إعدادات الإعلانات
def get_ad_settings():
    """
    الحصول على إعدادات الإعلانات الحالية
    
    Returns:
        AdSettings: كائن إعدادات الإعلانات
    """
    try:
        # استيراد داخلي لتجنب التعارضات الدائرية
        from app import db
        
        settings = AdSettings.query.first()
        if not settings:
            settings = AdSettings()
            settings.ads_enabled = False
            settings.max_ads_per_page = 3
            settings.show_in_homepage = True
            settings.show_in_dashboard = False
            settings.show_in_results = True
            db.session.add(settings)
            db.session.commit()
        
        return settings
    except Exception as e:
        logger.error(f"خطأ في الحصول على إعدادات الإعلانات: {e}")
        # إنشاء كائن فارغ مؤقت لتجنب الأخطاء
        dummy_settings = AdSettings()
        dummy_settings.ads_enabled = False
        dummy_settings.max_ads_per_page = 0
        dummy_settings.show_in_homepage = False
        dummy_settings.show_in_dashboard = False
        dummy_settings.show_in_results = False
        dummy_settings.adsense_client_id = ""
        dummy_settings.adsense_slot_id_header = ""
        dummy_settings.adsense_slot_id_sidebar = ""
        dummy_settings.adsense_slot_id_content = ""
        dummy_settings.adsense_slot_id_footer = ""
        return dummy_settings

# دالة مساعدة لتحديد ما إذا كان يجب عرض الإعلانات في صفحة معينة
def should_show_ads(page_type='homepage'):
    """
    تحديد ما إذا كان يجب عرض الإعلانات في صفحة معينة
    
    Args:
        page_type (str): نوع الصفحة ('homepage', 'dashboard', 'results')
        
    Returns:
        bool: True إذا كان يجب عرض الإعلانات، False خلاف ذلك
    """
    try:
        settings = get_ad_settings()
        
        # التحقق من تفعيل الإعلانات بشكل عام
        if not bool(settings.ads_enabled):
            return False
        
        # التحقق من نوع الصفحة
        if page_type == 'homepage':
            return bool(settings.show_in_homepage)
        elif page_type == 'dashboard':
            return bool(settings.show_in_dashboard)
        elif page_type == 'results':
            return bool(settings.show_in_results)
        
    except Exception as e:
        logger.error(f"Error in should_show_ads: {e}")
        return False
    
    # افتراضيًا، لا تعرض الإعلانات
    return False