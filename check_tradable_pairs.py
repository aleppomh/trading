"""
برنامج للتحقق من الأزواج المتاحة للتداول في الوقت الحالي
"""
import logging
import sys
from datetime import datetime
import pytz

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# استيراد الدوال من ملفات الأزواج
from market_pairs import get_tradable_pairs_with_good_payout as get_market_tradable_pairs
from market_pairs import is_pair_tradable_now as is_market_pair_tradable
from pocket_option_otc_pairs import get_pairs_with_good_payout as get_otc_tradable_pairs

# الحصول على الوقت الحالي بتوقيت جرينتش وتوقيت تركيا
utc_now = datetime.now(pytz.UTC)
turkey_now = datetime.now(pytz.timezone('Europe/Istanbul'))

# عرض الوقت الحالي
print(f"الوقت الحالي (UTC): {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"الوقت الحالي (GMT+3): {turkey_now.strftime('%Y-%m-%d %H:%M:%S')}")

# عرض اليوم الحالي
print(f"اليوم الحالي: {turkey_now.strftime('%A')}")

# فحص الأزواج المتاحة من البورصة العادية
market_pairs = get_market_tradable_pairs()
print(f"\nعدد أزواج البورصة العادية المتاحة: {len(market_pairs)}")
if market_pairs:
    print("قائمة أزواج البورصة العادية المتاحة:")
    for pair in market_pairs:
        print(f"  - {pair}")
else:
    print("لا توجد أزواج بورصة عادية متاحة في الوقت الحالي")
    
    # فحص سبب عدم توفر الأزواج
    from market_pairs import get_all_valid_pairs, get_pairs_with_good_payout
    
    all_pairs = get_all_valid_pairs()
    good_payout_pairs = get_pairs_with_good_payout()
    
    print(f"\nإجمالي أزواج البورصة العادية: {len(all_pairs)}")
    print(f"أزواج البورصة العادية ذات العائد الجيد: {len(good_payout_pairs)}")
    
    print("\nفحص حالة بعض الأزواج المعروفة:")
    test_pairs = ['EURUSD', 'GBPUSD', 'GOLD', 'SILVER', 'DOW']
    for pair in test_pairs:
        is_tradable = is_market_pair_tradable(pair, log_details=True)
        print(f"  - {pair}: {'متاح' if is_tradable else 'غير متاح'}")

# فحص الأزواج المتاحة من OTC
otc_pairs = get_otc_tradable_pairs()
print(f"\nعدد أزواج OTC المتاحة: {len(otc_pairs)}")
if otc_pairs:
    print("قائمة الأزواج OTC المتاحة:")
    for pair in otc_pairs[:10]:  # عرض أول 10 أزواج فقط
        print(f"  - {pair}")
    if len(otc_pairs) > 10:
        print(f"  ... و {len(otc_pairs) - 10} زوج آخر")