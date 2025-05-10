"""
نظام اختيار الأزواج التكيفي
يتيح اختيار أزواج التداول بشكل ذكي مع الأخذ في الاعتبار توافرها وأولويتها
"""

import logging
import random
import time
from datetime import datetime, timedelta
import os
import sys
import json

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adaptive_pair_selector")

# محاولة استيراد وحدات النظام
try:
    from advanced_error_logger import log_error, ErrorSeverity
except ImportError:
    # إنشاء دوال بديلة في حالة عدم توفر النظام المتقدم
    def log_error(message, severity=None, exception=None, context=None):
        logger.error(message)
    
    class ErrorSeverity:
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        CRITICAL = 4


class AdaptivePairSelector:
    """نظام اختيار الأزواج التكيفي مع ذاكرة للأزواج غير المتاحة"""
    
    def __init__(self, cache_file="pair_availability_cache.json", market_priority=0.7):
        """
        تهيئة نظام اختيار الأزواج التكيفي
        
        Args:
            cache_file: ملف تخزين بيانات توافر الأزواج
            market_priority: أولوية أزواج البورصة العادية (0-1)
        """
        self.cache_file = cache_file
        self.market_priority = market_priority
        
        # قائمة الأزواج ذات الأولوية العالية
        self.high_priority_pairs = [
            # أزواج البورصة العادية ذات الأولوية
            "EURUSD", "EURGBP", "EURJPY", "AUDJPY", "CADCHF",
            # أزواج OTC ذات الأولوية
            "EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC", "AUDJPY-OTC", "CADCHF-OTC"
        ]
        
        # ذاكرة توافر الأزواج
        self.pair_availability = self._load_availability_cache()
        
        # تاريخ آخر تطهير للذاكرة
        self.last_cache_cleanup = datetime.now()
        
        logger.info("✅ تم تهيئة نظام اختيار الأزواج التكيفي")
    
    def _load_availability_cache(self):
        """
        تحميل ذاكرة توافر الأزواج من الملف
        
        Returns:
            dict: بيانات توافر الأزواج
        """
        default_cache = {
            "market_pairs": {},  # توافر أزواج البورصة العادية
            "otc_pairs": {},     # توافر أزواج OTC
            "last_update": datetime.now().isoformat()
        }
        
        if not os.path.exists(self.cache_file):
            return default_cache
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # تحويل التواريخ من نصوص إلى كائنات تاريخ
            for pair_type in ['market_pairs', 'otc_pairs']:
                for pair, data in cache_data.get(pair_type, {}).items():
                    if 'last_check' in data:
                        data['last_check'] = datetime.fromisoformat(data['last_check'])
                    if 'unavailable_since' in data and data['unavailable_since']:
                        data['unavailable_since'] = datetime.fromisoformat(data['unavailable_since'])
                    else:
                        data['unavailable_since'] = None
            
            return cache_data
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في تحميل ذاكرة توافر الأزواج: {e}")
            return default_cache
    
    def _save_availability_cache(self):
        """حفظ ذاكرة توافر الأزواج في الملف"""
        try:
            # تحويل كائنات التاريخ إلى نصوص
            cache_to_save = {
                "market_pairs": {},
                "otc_pairs": {},
                "last_update": datetime.now().isoformat()
            }
            
            for pair_type in ['market_pairs', 'otc_pairs']:
                for pair, data in self.pair_availability.get(pair_type, {}).items():
                    cache_to_save[pair_type][pair] = data.copy()
                    if 'last_check' in data:
                        cache_to_save[pair_type][pair]['last_check'] = data['last_check'].isoformat()
                    if 'unavailable_since' in data and data['unavailable_since']:
                        cache_to_save[pair_type][pair]['unavailable_since'] = data['unavailable_since'].isoformat()
                    else:
                        cache_to_save[pair_type][pair]['unavailable_since'] = None
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_to_save, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في حفظ ذاكرة توافر الأزواج: {e}")
            return False
    
    def _cleanup_availability_cache(self):
        """تطهير ذاكرة توافر الأزواج القديمة"""
        now = datetime.now()
        
        # تطهير الذاكرة مرة واحدة كل 24 ساعة
        if (now - self.last_cache_cleanup).total_seconds() < 86400:
            return
        
        logger.info("🧹 تطهير ذاكرة توافر الأزواج القديمة")
        
        for pair_type in ['market_pairs', 'otc_pairs']:
            pairs_to_reset = []
            
            for pair, data in self.pair_availability.get(pair_type, {}).items():
                # إعادة التحقق من الأزواج غير المتاحة منذ أكثر من 48 ساعة
                if data.get('available') is False and data.get('unavailable_since'):
                    hours_unavailable = (now - data['unavailable_since']).total_seconds() / 3600
                    if hours_unavailable > 48:
                        pairs_to_reset.append(pair)
            
            # إعادة تعيين حالة الأزواج المحددة
            for pair in pairs_to_reset:
                self.pair_availability[pair_type][pair] = {
                    'available': None,  # غير معروف
                    'last_check': now,
                    'unavailable_since': None,
                    'check_count': 0
                }
        
        self.last_cache_cleanup = now
        self._save_availability_cache()
    
    def mark_pair_availability(self, pair_symbol, is_available, is_otc=False):
        """
        تحديد توافر زوج محدد
        
        Args:
            pair_symbol: رمز الزوج
            is_available: ما إذا كان الزوج متاحًا
            is_otc: ما إذا كان زوج OTC
            
        Returns:
            bool: نجاح العملية
        """
        pair_type = "otc_pairs" if is_otc else "market_pairs"
        now = datetime.now()
        
        # التأكد من وجود القاموس للنوع المحدد
        if pair_type not in self.pair_availability:
            self.pair_availability[pair_type] = {}
        
        # إذا كان الزوج غير موجود في الذاكرة، إضافته
        if pair_symbol not in self.pair_availability[pair_type]:
            self.pair_availability[pair_type][pair_symbol] = {
                'available': is_available,
                'last_check': now,
                'unavailable_since': None if is_available else now,
                'check_count': 1
            }
        else:
            # تحديث بيانات توافر الزوج
            pair_data = self.pair_availability[pair_type][pair_symbol]
            
            # زيادة عداد الفحص
            pair_data['check_count'] = pair_data.get('check_count', 0) + 1
            pair_data['last_check'] = now
            
            # إذا كان الزوج متاحًا سابقًا وأصبح غير متاح
            if pair_data.get('available') and not is_available:
                pair_data['unavailable_since'] = now
            
            # إذا كان الزوج غير متاح سابقًا وأصبح متاحًا
            if not pair_data.get('available') and is_available:
                pair_data['unavailable_since'] = None
            
            pair_data['available'] = is_available
        
        # حفظ الذاكرة بعد التحديث
        self._save_availability_cache()
        return True
    
    def is_pair_available(self, pair_symbol, is_otc=False, auto_mark=False):
        """
        التحقق مما إذا كان الزوج متاحًا
        
        Args:
            pair_symbol: رمز الزوج
            is_otc: ما إذا كان زوج OTC
            auto_mark: تحديد توافر الزوج تلقائيًا
            
        Returns:
            bool: ما إذا كان الزوج متاحًا
        """
        # التأكد من تنسيق رمز الزوج بشكل صحيح
        if pair_symbol is None:
            return False
            
        pair_symbol = pair_symbol.strip()
        
        # التحقق من قاعدة البيانات مباشرة
        if auto_mark:
            try:
                # التحقق من وجود الزوج في قاعدة البيانات
                import os, sys
                # إضافة المسار الجذر إلى مسارات النظام
                root_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                if root_path not in sys.path:
                    sys.path.append(root_path)
                
                from app import app
                if is_otc:
                    from models import OTCPair
                    with app.app_context():
                        # التحقق من وجود الزوج في قاعدة البيانات وأنه نشط
                        pair = OTCPair.query.filter_by(symbol=pair_symbol, is_active=True).first()
                        is_available = pair is not None
                        log_error(f"التحقق من توافر الزوج {pair_symbol} (OTC): {'✅ متاح' if is_available else '❌ غير متاح'}")
                else:
                    from models import MarketPair
                    with app.app_context():
                        # التحقق من وجود الزوج في قاعدة البيانات وأنه نشط
                        pair = MarketPair.query.filter_by(symbol=pair_symbol, is_active=True).first()
                        is_available = pair is not None
                        log_error(f"التحقق من توافر الزوج {pair_symbol} (عادي): {'✅ متاح' if is_available else '❌ غير متاح'}")
                
                # تحديث حالة الزوج في الذاكرة
                self.mark_pair_availability(pair_symbol, is_available, is_otc)
                return is_available
            except Exception as e:
                log_error(f"خطأ في التحقق من توافر الزوج {pair_symbol} من قاعدة البيانات: {e}")
        
        # التحقق من وجود بيانات عن الزوج في الذاكرة
        pair_type = "otc_pairs" if is_otc else "market_pairs"
        
        # التحقق من وجود بيانات عن الزوج
        if pair_type in self.pair_availability and pair_symbol in self.pair_availability[pair_type]:
            pair_data = self.pair_availability[pair_type][pair_symbol]
            
            # إذا كان توافر الزوج معروفًا وتم فحصه مؤخرًا
            if pair_data.get('available') is not None and pair_data.get('last_check'):
                # استخدام البيانات المخزنة إذا تم الفحص في آخر 8 ساعات
                time_since_check = (datetime.now() - pair_data['last_check']).total_seconds() / 3600
                if time_since_check < 8:
                    return pair_data['available']
        
        # لفحص حالات الأزواج ذات العائد المرتفع
        high_payout_pairs = [
            'EURUSD', 'EURGBP', 'EURJPY', 'AUDJPY', 'CADCHF',  # أزواج البورصة العادية
            'EURUSD-OTC', 'EURGBP-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'AUDJPY-OTC', 'CADCHF-OTC'  # أزواج OTC
        ]
        
        # إذا كان الزوج من قائمة الأزواج ذات العائد المرتفع، غالبًا ما يكون متاحًا
        if any(pair_symbol.upper() == p.upper() for p in high_payout_pairs):
            log_error(f"الزوج {pair_symbol} من الأزواج ذات العائد المرتفع، سيتم اعتباره متاحًا")
            is_available = True
            self.mark_pair_availability(pair_symbol, is_available, is_otc)
            return is_available
        
        # في حالة عدم توفر بيانات وعدم طلب التحديث التلقائي
        return True  # افتراضيًا متاح
    
    def should_retry_unavailable_pair(self, pair_symbol, is_otc=False):
        """
        تحديد ما إذا كان يجب إعادة تجربة زوج غير متاح
        
        Args:
            pair_symbol: رمز الزوج
            is_otc: ما إذا كان زوج OTC
            
        Returns:
            bool: ما إذا كان يجب إعادة تجربة الزوج
        """
        pair_type = "otc_pairs" if is_otc else "market_pairs"
        
        # التحقق من وجود بيانات عن الزوج
        if pair_type in self.pair_availability and pair_symbol in self.pair_availability[pair_type]:
            pair_data = self.pair_availability[pair_type][pair_symbol]
            
            # إذا كان الزوج غير متاح وتم تحديد وقت عدم التوافر
            if pair_data.get('available') is False and pair_data.get('unavailable_since'):
                # حساب المدة منذ أصبح الزوج غير متاح
                hours_unavailable = (datetime.now() - pair_data['unavailable_since']).total_seconds() / 3600
                
                # استراتيجية إعادة المحاولة المتكيفة:
                # - الساعة الأولى: إعادة المحاولة كل 10 دقائق
                # - الساعات 1-3: إعادة المحاولة كل 30 دقيقة
                # - الساعات 3-12: إعادة المحاولة كل ساعة
                # - الساعات 12-24: إعادة المحاولة كل 3 ساعات
                # - أكثر من 24 ساعة: إعادة المحاولة كل 6 ساعات
                
                if hours_unavailable < 1:
                    return (datetime.now() - pair_data['last_check']).total_seconds() >= 600  # 10 دقائق
                elif hours_unavailable < 3:
                    return (datetime.now() - pair_data['last_check']).total_seconds() >= 1800  # 30 دقيقة
                elif hours_unavailable < 12:
                    return (datetime.now() - pair_data['last_check']).total_seconds() >= 3600  # ساعة
                elif hours_unavailable < 24:
                    return (datetime.now() - pair_data['last_check']).total_seconds() >= 10800  # 3 ساعات
                else:
                    return (datetime.now() - pair_data['last_check']).total_seconds() >= 21600  # 6 ساعات
            
            # إذا كان الزوج متاحًا أو لم يتم تحديد وقت عدم التوافر
            return True
        
        # في حالة عدم وجود بيانات عن الزوج
        return True
    
    def get_optimal_pair(self, market_pairs, otc_pairs, force_market=False, force_otc=False):
        """
        الحصول على الزوج الأمثل للإشارة التالية
        
        Args:
            market_pairs: قائمة أزواج البورصة العادية
            otc_pairs: قائمة أزواج OTC
            force_market: إجبار استخدام أزواج البورصة العادية
            force_otc: إجبار استخدام أزواج OTC
            
        Returns:
            tuple: (الزوج المختار، ما إذا كان OTC)
        """
        # تطهير الذاكرة إذا لزم الأمر
        self._cleanup_availability_cache()
        
        # تحديد ما إذا كنا سنستخدم أزواج البورصة العادية أم أزواج OTC
        use_market_pairs = True
        if force_market:
            use_market_pairs = True
        elif force_otc:
            use_market_pairs = False
        else:
            # اختيار عشوائي مع مراعاة الأولوية
            use_market_pairs = random.random() < self.market_priority
        
        # قائمة الأزواج المتاحة للاختيار منها
        available_pairs = []
        is_otc = not use_market_pairs
        pairs_list = market_pairs if use_market_pairs else otc_pairs
        
        # معاينة الأزواج ذات الأولوية العالية أولاً
        high_priority_available = []
        
        for pair in pairs_list:
            pair_symbol = pair.symbol if hasattr(pair, 'symbol') else pair
            
            # تحديد ما إذا كان الزوج ذو أولوية عالية
            is_high_priority = pair_symbol in self.high_priority_pairs
            
            # التحقق من توافر الزوج
            if self.is_pair_available(pair_symbol, is_otc):
                if is_high_priority:
                    high_priority_available.append(pair)
                available_pairs.append(pair)
        
        # إذا وجدت أزواج ذات أولوية عالية متاحة، استخدامها بنسبة 80%
        if high_priority_available and random.random() < 0.8:
            selected_pair = random.choice(high_priority_available)
            logger.info(f"✅ تم اختيار زوج ذو أولوية عالية: {selected_pair}")
            return selected_pair, is_otc
        
        # إذا وجدت أزواج متاحة، اختيار واحد منها عشوائيًا
        if available_pairs:
            selected_pair = random.choice(available_pairs)
            logger.info(f"✅ تم اختيار زوج متاح: {selected_pair}")
            return selected_pair, is_otc
        
        # إذا لم توجد أزواج متاحة من النوع المطلوب، تجربة النوع الآخر
        if use_market_pairs and not force_market:
            logger.warning("⚠️ لم يتم العثور على أزواج بورصة عادية متاحة، محاولة استخدام أزواج OTC")
            return self.get_optimal_pair(market_pairs, otc_pairs, force_market=False, force_otc=True)
        elif not use_market_pairs and not force_otc:
            logger.warning("⚠️ لم يتم العثور على أزواج OTC متاحة، محاولة استخدام أزواج البورصة العادية")
            return self.get_optimal_pair(market_pairs, otc_pairs, force_market=True, force_otc=False)
        
        # إذا لم يتم العثور على أي أزواج متاحة على الإطلاق
        log_error("❌ لم يتم العثور على أي أزواج متاحة للتداول", ErrorSeverity.HIGH, context="pair_selection")
        return None, False
    
    def list_all_pairs_status(self):
        """
        الحصول على حالة جميع الأزواج
        
        Returns:
            dict: حالة توافر جميع الأزواج
        """
        result = {
            "market_pairs": {},
            "otc_pairs": {},
            "summary": {
                "total_pairs": 0,
                "available_pairs": 0,
                "unavailable_pairs": 0,
                "unknown_pairs": 0
            }
        }
        
        for pair_type in ['market_pairs', 'otc_pairs']:
            if pair_type in self.pair_availability:
                for pair, data in self.pair_availability[pair_type].items():
                    result[pair_type][pair] = {
                        "available": data.get('available'),
                        "last_check": data.get('last_check'),
                        "unavailable_since": data.get('unavailable_since'),
                        "check_count": data.get('check_count', 0)
                    }
                    
                    # تحديث الملخص
                    result["summary"]["total_pairs"] += 1
                    if data.get('available') is True:
                        result["summary"]["available_pairs"] += 1
                    elif data.get('available') is False:
                        result["summary"]["unavailable_pairs"] += 1
                    else:
                        result["summary"]["unknown_pairs"] += 1
        
        return result


# إنشاء كائن عالمي لنظام اختيار الأزواج التكيفي
pair_selector = AdaptivePairSelector()


# دوال مساعدة للاستخدام المباشر في البرنامج
def get_optimal_trading_pair(market_pairs, otc_pairs, force_market=False, force_otc=False):
    """
    الحصول على زوج التداول الأمثل للإشارة التالية
    
    Args:
        market_pairs: قائمة أزواج البورصة العادية
        otc_pairs: قائمة أزواج OTC
        force_market: إجبار استخدام أزواج البورصة العادية
        force_otc: إجبار استخدام أزواج OTC
        
    Returns:
        tuple: (الزوج المختار، ما إذا كان OTC)
    """
    return pair_selector.get_optimal_pair(market_pairs, otc_pairs, force_market, force_otc)


def mark_pair_availability(pair_symbol, is_available, is_otc=False):
    """
    تحديد توافر زوج محدد
    
    Args:
        pair_symbol: رمز الزوج
        is_available: ما إذا كان الزوج متاحًا
        is_otc: ما إذا كان زوج OTC
    """
    return pair_selector.mark_pair_availability(pair_symbol, is_available, is_otc)


def get_pairs_status():
    """
    الحصول على حالة جميع الأزواج
    
    Returns:
        dict: حالة توافر الأزواج
    """
    return pair_selector.list_all_pairs_status()


# تنفيذ اختبار عند تشغيل الملف مباشرة
if __name__ == "__main__":
    # بيانات اختبار
    test_market_pairs = ["EURUSD", "EURGBP", "EURJPY", "AUDJPY", "CADCHF"]
    test_otc_pairs = ["EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC", "USDJPY-OTC"]
    
    # تحديد بعض الأزواج كغير متاحة للاختبار
    mark_pair_availability("EURUSD", False, False)
    mark_pair_availability("EURJPY-OTC", False, True)
    
    # اختبار الحصول على الزوج الأمثل
    for _ in range(5):
        pair, is_otc = get_optimal_trading_pair(test_market_pairs, test_otc_pairs)
        print(f"الزوج المختار: {pair} ({'OTC' if is_otc else 'بورصة عادية'})")
    
    # عرض حالة جميع الأزواج
    print(json.dumps(get_pairs_status(), indent=2, default=str))