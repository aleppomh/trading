"""
ملف القوالب الخاص بالدومين - يحتوي على رؤوس القالب والمتغيرات العامة
"""

from custom_domain_config import CUSTOM_DOMAIN

# روابط مواقع التواصل الاجتماعي
SOCIAL_LINKS = {
    "telegram": "https://t.me/Tradefreet",
    "twitter": "https://twitter.com/trading_elite",
    "instagram": "https://instagram.com/trading_elite_pro",
    "facebook": "https://facebook.com/trading.elite.pro"
}

# إعدادات قالب الموقع
SITE_SETTINGS = {
    "site_name": "Trading Elite Pro",
    "site_tagline": "إشارات تداول دقيقة وذكية",
    "site_description": "منصة تداول ذكية توفر إشارات دقيقة لتداول العملات OTC",
    "site_keywords": "تداول, إشارات, فوركس, OTC, بوكيت أوبشن, Pocket Option",
    "site_author": "Trading Elite Pro Team",
    "site_email": "contact@design-note-sync-lyvaquny.replit.app",
    "site_phone": "+90 123 456 7890",
    "copyright_year": "2025",
}

# روابط ثابتة للمنصة وقناة Trading Elite Pro
AFFILIATE_LINKS = {
    "pocket_option": "https://pocket.click/register?utm_source=affiliate&a=k1EstfG8TSRtg2&ac=mosto&code=50START",
    "trading_elite": f"https://{CUSTOM_DOMAIN}",
    "telegram_channel": "https://t.me/Tradefreet"
}

# وظيفة للحصول على رابط الموقع الكامل مع الدومين
def get_full_url(path="/"):
    """الحصول على رابط كامل مع الدومين"""
    if CUSTOM_DOMAIN:
        return f"https://{CUSTOM_DOMAIN}{path}"
    else:
        return path