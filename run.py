"""
الملف الرئيسي لتشغيل التطبيق
يمكن تشغيله مباشرة باستخدام: python run.py
"""

import os
import sys
import logging
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env إذا كان موجوداً
load_dotenv()

# إعداد سجل الأحداث
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# التأكد من وجود قاعدة البيانات
if not os.environ.get('DATABASE_URL'):
    logger.error("لم يتم تعيين متغير DATABASE_URL البيئي")
    logger.info("يرجى التأكد من تعيين متغيرات البيئة المطلوبة")
    sys.exit(1)

# استيراد التطبيق
try:
    from trading_bot.app import create_app
    from trading_bot.config import active_config
    
    # إنشاء تطبيق Flask
    app = create_app(active_config)
    
    # تشغيل التطبيق
    if __name__ == "__main__":
        host = os.environ.get("FLASK_HOST", "0.0.0.0")
        port = int(os.environ.get("FLASK_PORT", 5000))
        debug = os.environ.get("FLASK_DEBUG", "False").lower() in ('true', '1', 't')
        
        logger.info(f"بدء تشغيل التطبيق على {host}:{port} (وضع التصحيح: {debug})")
        
        app.run(host=host, port=port, debug=debug)
        
except Exception as e:
    logger.exception(f"خطأ أثناء بدء تشغيل التطبيق: {str(e)}")
    sys.exit(1)