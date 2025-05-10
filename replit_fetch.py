"""
مكون متطور للحفاظ على رابط Replit نشطًا باستخدام تقنيات متعددة
يستخدم هذا المكون مزيجًا من الطلبات HTTP ومراقبة الحالة لضمان استمرار عمل البوت
"""
import threading
import time
import logging
import requests
import os
import socket
import random
from datetime import datetime

# رابط المشروع الخاص بك (يتم تحديثه تلقائيًا)
DEFAULT_PROJECT_URL = "https://f5fb8356-b420-4e32-b2b6-05ac9d1a1c71-00-3blbjrsd87z4d.janeway.replit.dev/"

# الفاصل الزمني للجلب بالثواني (كل 2 دقائق)
FETCH_INTERVAL = 120  # تم تقليله من 240 إلى 120 ثانية للحفاظ على استمرار العمل

# الفاصل الزمني للجلب الثانوي (30 ثانية)
SECONDARY_FETCH_INTERVAL = 30

# إعداد السجل
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# الحصول على رابط Replit ديناميكيًا
def get_replit_url():
    """
    الحصول على رابط Replit الديناميكي من متغيرات البيئة
    """
    try:
        # محاولة القراءة من ملف التكوين المتاح في بيئة Replit
        if os.path.exists('/etc/replit/cluster-url'):
            with open('/etc/replit/cluster-url', 'r') as f:
                cluster_url = f.read().strip()
                repl_slug = os.environ.get('REPL_SLUG', 'repl')
                return f"https://{repl_slug}.{cluster_url}/"
    except Exception as e:
        logger.warning(f"لم نتمكن من الحصول على رابط Replit الديناميكي: {e}")
    
    # العودة إلى الرابط الافتراضي إذا فشلت المحاولة
    return DEFAULT_PROJECT_URL

# الحصول على عنوان IP الحالي
def get_current_ip():
    """
    الحصول على عنوان IP الحالي للخادم
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"لم نتمكن من الحصول على عنوان IP: {e}")
        return "127.0.0.1"

# جلب موقع الويب الأساسي
def fetch_site():
    """
    وظيفة لجلب موقع الويب للحفاظ عليه نشطًا
    """
    # الحصول على رابط المشروع
    project_url = get_replit_url()
    
    # تمديد الانتظار العشوائي (1-5 ثواني) لتجنب تزامن الطلبات
    time.sleep(random.uniform(1, 5))
    
    while True:
        try:
            # إضافة معلمات عشوائية لتجنب التخزين المؤقت
            current_time = int(time.time())
            params = {
                "keep_alive": current_time,
                "client_id": socket.gethostname(),
                "ip": get_current_ip()
            }
            
            # إرسال طلب الجلب
            response = requests.get(f"{project_url}ping", params=params, timeout=15)
            
            # سجل النجاح أو الفشل
            if response.status_code == 200:
                logger.info(f"Alive ping successful. Status code: {response.status_code}")
            else:
                logger.warning(f"Received non-200 response: {response.status_code}, {response.text[:100]}")
                
        except requests.RequestException as e:
            logger.error(f"HTTP error fetching site: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching site: {e}")
            
        # انتظار الفاصل الزمني المحدد مع تمديد عشوائي لتجنب التزامن
        next_interval = FETCH_INTERVAL + random.uniform(-5, 5)
        logger.info(f"Next ping in {next_interval:.1f} seconds")
        time.sleep(next_interval)

# جلب موقع الويب الثانوي (بصيغة مختلفة)
def fetch_secondary():
    """
    خيط ثانوي للجلب بفاصل زمني أقصر وطريقة مختلفة
    """
    # تمديد الانتظار العشوائي (10-20 ثانية) للفصل بين الطلبات الأساسية والثانوية
    time.sleep(random.uniform(10, 20))
    
    while True:
        try:
            # استخدام مسار مختلف كل مرة
            paths = ['/', '/ping', '/signal_status']
            path = random.choice(paths)
            
            # الحصول على رابط المشروع
            project_url = get_replit_url()
            
            # استخدام عميل جلسة مختلف
            with requests.Session() as session:
                # إضافة معلمات عشوائية
                params = {
                    "ts": datetime.now().timestamp(),
                    "r": random.random(),
                    "secondary": "true"
                }
                
                # إضافة ترويسات مخصصة للتمويه
                headers = {
                    "User-Agent": "KeepAliveBot/1.0",
                    "Accept": "application/json",
                    "X-Keep-Alive": "true"
                }
                
                # إرسال الطلب
                response = session.get(f"{project_url}{path}", 
                                      params=params, 
                                      headers=headers,
                                      timeout=10)
                
                # تسجيل النتيجة بمستوى أقل (تفاصيل)
                logger.debug(f"Secondary ping to {path} - Status: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Secondary ping failed: {e}")
            
        # انتظار الفاصل الزمني الثانوي
        time.sleep(SECONDARY_FETCH_INTERVAL + random.uniform(-2, 2))

# بدء نظام الجلب
def start_fetcher():
    """
    بدء خيوط متعددة للجلب في الخلفية
    """
    # خيط الجلب الأساسي
    primary_thread = threading.Thread(target=fetch_site, name="primary_fetcher")
    primary_thread.daemon = True
    primary_thread.start()
    
    # خيط الجلب الثانوي
    secondary_thread = threading.Thread(target=fetch_secondary, name="secondary_fetcher")
    secondary_thread.daemon = True
    secondary_thread.start()
    
    logger.info("Replit Fetch thread started")
    return primary_thread, secondary_thread