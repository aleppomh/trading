import os
import logging
import base64
import io
import re
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from chart_analyzer import analyze_chart_image
# استيراد إعدادات الدومين المخصص
try:
    from custom_domain_config import CUSTOM_DOMAIN, ALLOWED_DOMAINS
except ImportError:
    CUSTOM_DOMAIN = None
    ALLOWED_DOMAINS = ["*.replit.app"]

# Configure logging with file output
import sys
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# إعدادات الدومين المخصص
if CUSTOM_DOMAIN:
    # تطبيق إعدادات الدومين المخصص دائمًا بغض النظر عن البيئة
    logger.info(f"تم تكوين الدومين المخصص: {CUSTOM_DOMAIN}")
    # لا نقوم بتعيين SERVER_NAME لتجنب مشاكل التوجيه في بيئة التطوير
    # app.config['SERVER_NAME'] = CUSTOM_DOMAIN
    app.config['PREFERRED_URL_SCHEME'] = 'https'
else:
    logger.info(f"لم يتم تكوين دومين مخصص")

# تكوين CORS للسماح بالوصول من جميع الدومينات المسموح بها
from flask_cors import CORS
# استخدام * للسماح بالوصول من أي دومين - أكثر أمانًا للتطوير
CORS(app, supports_credentials=True)

# Initialize CSRFProtect
csrf = CSRFProtect()
csrf.init_app(app)

# Exempt API routes from CSRF protection
csrf.exempt('generate_signal_api')
csrf.exempt('delete_user')
csrf.exempt('update_user')
csrf.exempt('update_admin')
csrf.exempt('delete_admin')
csrf.exempt('delete_channel')
csrf.exempt('delete_otc_pair')
csrf.exempt('user_analyze_chart')  # Exempt chart analysis route
csrf.exempt('analyze_chart')  # Exempt admin chart analysis route

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_signals.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension
db.init_app(app)

from models import Admin, User, Signal, ApprovedChannel, OTCPair, ChartAnalysis, BotConfiguration, AdSettings
from bot.telegram_bot import setup_bot
from bot.signal_generator import generate_signal
from bot.utils import is_admin, admin_required
# Login manager already imported at the top
# from flask_login import LoginManager, login_user, logout_user, current_user, login_required

# استيراد دالة تنسيق معرف قناة تيليجرام
try:
    # تجربة استيراد من المجلد الرئيسي أولاً
    from utils import format_telegram_channel_id
    logger.info("تم استيراد format_telegram_channel_id من utils")
except ImportError:
    # نسخ الدالة مباشرة هنا كحل إضافي
    logger.warning("فشل استيراد format_telegram_channel_id، سيتم تعريفها محلياً")
    def format_telegram_channel_id(channel_id):
        """
        تنسيق معرف قناة تيليجرام لضمان أنه بالصيغة الصحيحة
        
        Args:
            channel_id (str): معرف القناة المدخل
            
        Returns:
            str: معرف القناة المنسق بشكل صحيح للاستخدام مع API تيليجرام
        """
        # إزالة أي مسافات
        channel_id = str(channel_id).strip()
        
        # إذا كان المعرف يبدأ بـ @ فهذا اسم مستخدم وليس معرف رقمي
        if channel_id.startswith('@'):
            return channel_id
            
        # التحقق من أنها قناة عامة بمعرف رقمي
        # إذا كان معرف رقمي، يجب أن يبدأ بـ -100
        if channel_id.lstrip('-').isdigit():
            # إزالة أي - في البداية للتعامل مع المعرف بشكل نظيف
            channel_id = channel_id.lstrip('-')
            
            # التحقق مما إذا كان المعرف يبدأ بـ 100 بالفعل
            if channel_id.startswith('100'):
                channel_id = '-' + channel_id
            else:
                channel_id = '-100' + channel_id
        
        return channel_id

# Initialize flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# إضافة معالجات السياق لإعدادات الإعلانات
from context_processors import setup_ad_context_processors
setup_ad_context_processors(app)


# Initialize bot
bot = None
with app.app_context():
    # Get active bot config from database
    active_bot_config = BotConfiguration.query.filter_by(is_active=True).first()
    if active_bot_config:
        logger.info(f"Using bot configuration: {active_bot_config.name} (ID: {active_bot_config.id})")
        os.environ["TELEGRAM_BOT_TOKEN"] = active_bot_config.api_token
        bot = setup_bot(app)
    else:
        logger.warning("No active bot configuration found, using default bot setup")
        bot = setup_bot(app)

# Import signal checking function
from bot.signal_generator import check_signal_results

# تأكد من إيقاف وإزالة جميع المهام المجدولة - يتم التعامل معها الآن في signal_manager.py
try:
    # نحاول إيقاف أي scheduler موجود
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.shutdown(wait=False)
    logging.info("تم إيقاف جميع المهام المجدولة")
except:
    pass

# وقت آخر إرسال للإشارة
last_signal_time = None
# المدة المطلوبة بين الإشارات بالثواني (5 دقائق = 300 ثانية)
SIGNAL_INTERVAL_SECONDS = 300

# دالة مخصصة للتحقق مما إذا كان وقت إرسال إشارة جديدة - معطلة
def is_time_to_generate_signal():
    """تم تعطيل هذه الدالة واستبدالها بدالة مماثلة في signal_manager.py"""
    logger.info("تم تعطيل دالة is_time_to_generate_signal في app.py - استخدم signal_manager.py بدلًا من ذلك")
    return False  # دائمًا ترجع False لمنع إنشاء إشارات من هنا

# دالة مخصصة لتوليد إشارة جديدة - WRAPPER ONLY
def generate_new_signal(force=False):
    """
    IMPORTANT: This wrapper function ensures compatibility with the new signal system
    MODIFIED to respect the 4-6 minute interval and support forced signal generation
    
    Args:
        force (bool): إذا كانت True، سيتم إنشاء إشارة جديدة بغض النظر عن الفاصل الزمني
    
    Returns:
        bool: True إذا تم إنشاء إشارة جديدة، False خلاف ذلك
    """
    global last_signal_time
    
    # لا نحتاج لسياق التطبيق هنا بعد الآن لأننا لا نقوم بعمليات قاعدة البيانات بشكل مباشر
    # التحقق من وقت آخر إشارة والفارق الزمني
    current_time = datetime.utcnow()
    
    # إذا لم يتم تسجيل وقت إشارة سابق
    if last_signal_time is None:
        last_signal_time = current_time - timedelta(seconds=SIGNAL_INTERVAL_SECONDS)
    
    # حساب الفارق الزمني بين الوقت الحالي وآخر إشارة
    time_diff_seconds = (current_time - last_signal_time).total_seconds()
    
    # شرط إنشاء الإشارة:
    # 1. إذا كان الوضع إجباري (force=True)، أو
    # 2. إذا مرت المدة الزمنية المطلوبة (تم ضبطها الآن على 4-6 دقائق)
    if force or time_diff_seconds >= MIN_SIGNAL_INTERVAL_SECONDS:
        # التحقق من وجود قفل مركزي
        if signal_manager.acquire_db_lock():
            try:
                # تسجيل وقت إرسال الإشارة
                last_signal_time = current_time
                
                if force:
                    logger.warning(f"🔥 إنشاء إشارة جديدة بشكل إجباري (مرت {time_diff_seconds:.2f} ثانية)")
                else:
                    logger.info(f"وقت مناسب لإنشاء إشارة جديدة (مرت {time_diff_seconds:.2f} ثانية)")
                
                # إنشاء الإشارة الجديدة
                with app.app_context():
                    if force:
                        logger.warning("Signal generation FORCED via app.py (wrapper)")
                    else:
                        logger.info("Signal generation requested via app.py (wrapper)")
                    _real_generate_new_signal()
                
                # تحرير القفل المركزي
                signal_manager.release_db_lock()
                return True
            except Exception as e:
                logger.error(f"خطأ في توليد الإشارة: {e}")
                logger.exception("تفاصيل الخطأ:")
                
                # تحرير القفل المركزي في حالة حدوث خطأ
                signal_manager.release_db_lock()
                return False
        else:
            if force:
                logger.warning("❌ لم يتم الحصول على القفل المركزي، لا يمكن إنشاء إشارة حتى في الوضع الإجباري")
            else:
                logger.info("لم يتم الحصول على القفل المركزي، لا يمكن إنشاء إشارة")
            return False
    else:
        # لم يحن وقت الإشارة بعد
        logger.info(f"لم يحن وقت إنشاء إشارة جديدة بعد (منذ آخر إشارة: {time_diff_seconds:.2f} ثانية)")
        return False
        
# المكون الفعلي لتوليد الإشارات - يتم استدعاؤه من generate_new_signal wrapper
def _real_generate_new_signal():
    """Generate a new signal every 5 minutes exactly - actual implementation"""
    with app.app_context():
        # تسجيل بداية العملية
        logger.info("=== SIGNAL GENERATION STARTED (source: central signal system) ===")
        active_bots = BotConfiguration.query.filter_by(is_active=True).all()
        
        # If there are active bots, generate signals
        if active_bots:
            logger.info(f"Found {len(active_bots)} active bots")
            
            # Make sure bot is initialized
            current_bot = bot
            if not current_bot:
                logger.warning("Bot was not initialized, attempting to reinitialize")
                active_bot_config = active_bots[0]
                os.environ["TELEGRAM_BOT_TOKEN"] = active_bot_config.api_token
                current_bot = setup_bot(app)
                
            # استيراد نماذج الأزواج
            from models import OTCPair, MarketPair
            
            # الحصول على جميع أزواج OTC النشطة
            otc_pairs = OTCPair.query.filter_by(is_active=True).all()
            logger.info(f"Found {len(otc_pairs)} active OTC pairs")
            
            # الحصول على جميع أزواج البورصة العادية النشطة
            market_pairs = MarketPair.query.filter_by(is_active=True).all()
            logger.info(f"Found {len(market_pairs)} active regular exchange pairs")
            
            if not otc_pairs and not market_pairs:
                logger.error("No active pairs found (neither OTC nor regular exchange), cannot generate signal")
                return
            
            # تحديد نوع الزوج للإشارة - تفضيل أزواج البورصة العادية بنسبة 70%
            import random
            
            use_market_pairs = random.random() < 0.7  # 70% فرصة لاستخدام أزواج البورصة العادية
            
            # تسجيل بيانات مفصلة لفهم عملية الاختيار
            random_value = random.random()
            logger.info(f"DEBUG - Random value: {random_value} (< 0.7 means use market pairs)")
            logger.info(f"DEBUG - Market pairs count: {len(market_pairs)}, OTC pairs count: {len(otc_pairs)}")
            logger.info(f"DEBUG - First few market pairs: {[p.symbol for p in market_pairs[:5] if market_pairs]}")
            logger.info(f"DEBUG - First few OTC pairs: {[p.symbol for p in otc_pairs[:5] if otc_pairs]}")
            
            # اختيار نوع الزوج المناسب
            if use_market_pairs and market_pairs:
                # استخدام البورصة العادية
                pair_list = market_pairs
                pair_type = "regular exchange"
                logger.info("Using REGULAR EXCHANGE pairs for signal generation")
            elif otc_pairs:
                # استخدام OTC
                pair_list = otc_pairs
                pair_type = "OTC"
                logger.info("Using OTC pairs for signal generation")
            else:
                # لا توجد أزواج متاحة
                logger.error("No suitable pairs available at this time")
                return
            
            # استخدام نظام اختيار الأزواج التكيفي إذا كان متاحاً
            try:
                # محاولة استيراد نظام اختيار الأزواج التكيفي
                from adaptive_pair_selector import get_optimal_trading_pair, mark_pair_availability
                
                logger.info("Using adaptive pair selection system for optimal pair choice")
                
                # الحصول على الزوج الأمثل باستخدام النظام التكيفي
                force_market = use_market_pairs and len(market_pairs) > 0
                force_otc = not use_market_pairs and len(otc_pairs) > 0
                
                selected_pair, is_otc = get_optimal_trading_pair(
                    market_pairs, 
                    otc_pairs,
                    force_market=force_market,
                    force_otc=force_otc
                )
                
                # إذا تم العثور على زوج مناسب، استخدامه
                if selected_pair:
                    pair = selected_pair
                    # تحديث نوع الزوج إذا تغير
                    if is_otc:
                        pair_type = "OTC"
                    else:
                        pair_type = "regular exchange"
                    
                    logger.info(f"Adaptive pair selector chose: {pair.symbol} as {pair_type} pair")
                else:
                    # في حالة فشل النظام التكيفي، العودة إلى الاختيار العشوائي
                    logger.warning("Adaptive pair selector failed to find suitable pair, falling back to random selection")
                    pair = random.choice(pair_list)
            except Exception as e:
                logger.warning(f"Adaptive pair selector not available or failed: {e}, using random selection")
                # اختيار زوج عشوائي من القائمة المحددة
                pair = random.choice(pair_list)
            logger.info(f"Randomly selected {pair_type} pair: {pair.symbol} (ID: {pair.id})")
            
            # Generate and send the signal
            try:
                # إذا كان الزوج من النوع OTC، نمرره مباشرة
                # تحقق إذا كان الزوج متاح حاليًا للتداول (ميزة ذكية لتجاوز الأزواج غير المتاحة)
                from bot.signal_generator import check_pair_availability
                
                if pair_type == "OTC":
                    # تحقق ما إذا كان الزوج OTC متاح
                    if check_pair_availability(pair):
                        signal = generate_signal(current_bot, pair.id, is_doubling=False)
                        if signal:
                            logger.info(f"Successfully generated automated signal for OTC pair {pair.symbol}")
                        else:
                            logger.error("Failed to generate automated signal for OTC pair")
                    else:
                        # اختيار زوج OTC آخر متاح للتداول
                        logger.warning(f"⚠️ OTC pair {pair.symbol} is not available for trading, finding another pair")
                        available_pairs = []
                        
                        # فحص جميع الأزواج OTC النشطة
                        for p in otc_pairs:
                            if check_pair_availability(p):
                                available_pairs.append(p)
                        
                        if available_pairs:
                            # اختيار زوج متاح عشوائيًا
                            available_pair = random.choice(available_pairs)
                            logger.info(f"✅ Found alternative OTC pair: {available_pair.symbol}")
                            signal = generate_signal(current_bot, available_pair.id, is_doubling=False)
                            if signal:
                                logger.info(f"Successfully generated automated signal for alternative OTC pair {available_pair.symbol}")
                            else:
                                logger.error("Failed to generate automated signal for alternative OTC pair")
                        else:
                            logger.error("❌ No available OTC pairs found for trading at this time")
                            
                else:
                    # بالنسبة لأزواج البورصة العادية، نحتاج إلى معالجة خاصة
                    # لأن نظام الإشارات مصمم للعمل مع أزواج OTC فقط في قاعدة البيانات
                    
                    # تحقق ما إذا كان الزوج متاح
                    if check_pair_availability(pair):
                        # نحاول العثور على زوج OTC مطابق (للتوافق)
                        otc_symbol = pair.symbol + "-OTC" if not pair.symbol.endswith("-OTC") else pair.symbol
                        otc_pair = OTCPair.query.filter_by(symbol=otc_symbol).first()
                        
                        if not otc_pair:
                            # إذا لم نجد زوج OTC مقابل، نحاول العثور على زوج OTC بديل جيد
                            # أولاً، نحاول استخدام أحد الأزواج ذات العائد المرتفع
                            preferred_pairs = ['EURUSD-OTC', 'EURGBP-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'AUDJPY-OTC', 'CADCHF-OTC']
                            
                            # البحث عن زوج مفضل نشط
                            for preferred_symbol in preferred_pairs:
                                preferred_pair = OTCPair.query.filter_by(symbol=preferred_symbol, is_active=True).first()
                                if preferred_pair:
                                    otc_pair = preferred_pair
                                    logger.info(f"✅ تم العثور على زوج OTC مفضل بديل: {preferred_pair.symbol}")
                                    break
                            
                            # إذا لم نجد أي زوج مفضل، نستخدم أي زوج OTC نشط
                            if not otc_pair:
                                otc_pair = OTCPair.query.filter_by(is_active=True).first()
                                if otc_pair:
                                    logger.info(f"✅ تم العثور على زوج OTC نشط: {otc_pair.symbol}")
                            
                        if otc_pair:
                            logger.info(f"Using OTC pair {otc_pair.symbol} as proxy for regular exchange pair {pair.symbol}")
                            
                            # قبل توليد الإشارة، قم بتسجيل معلومات الزوج الأصلي لاستخدامها في العرض
                            signal = generate_signal(current_bot, otc_pair.id, is_doubling=False)
                            
                            if signal:
                                logger.info(f"Successfully generated automated signal for regular exchange pair {pair.symbol}")
                            else:
                                logger.error("Failed to generate automated signal for regular exchange pair")
                        else:
                            logger.error("No OTC pairs available to use as proxy for regular exchange pair - this should never happen")
                    else:
                        # اختيار زوج بورصة عادية آخر متاح للتداول
                        logger.warning(f"⚠️ Market pair {pair.symbol} is not available for trading, finding another pair")
                        available_pairs = []
                        
                        # فحص جميع الأزواج العادية النشطة
                        for p in market_pairs:
                            if check_pair_availability(p):
                                available_pairs.append(p)
                        
                        if available_pairs:
                            # اختيار زوج متاح عشوائيًا
                            available_pair = random.choice(available_pairs)
                            logger.info(f"✅ Found alternative market pair: {available_pair.symbol}")
                            
                            # نحاول العثور على زوج OTC مطابق للزوج البديل
                            alt_otc_symbol = available_pair.symbol + "-OTC" if not available_pair.symbol.endswith("-OTC") else available_pair.symbol
                            alt_otc_pair = OTCPair.query.filter_by(symbol=alt_otc_symbol).first()
                            
                            # إنشاء قائمة من الأزواج المفضلة التي لها عائد مرتفع
                            preferred_pairs = ['EURUSD-OTC', 'EURGBP-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'AUDJPY-OTC', 'CADCHF-OTC']
                            
                            # إذا لم نجد زوج OTC مطابق، حاول استخدام أحد الأزواج المفضلة
                            if not alt_otc_pair:
                                logger.info(f"⚠️ لم يتم العثور على زوج OTC مطابق لـ {available_pair.symbol}، البحث عن زوج مفضل...")
                                
                                # البحث عن زوج مفضل نشط
                                for preferred_symbol in preferred_pairs:
                                    preferred_pair = OTCPair.query.filter_by(symbol=preferred_symbol, is_active=True).first()
                                    if preferred_pair:
                                        alt_otc_pair = preferred_pair
                                        logger.info(f"✅ تم العثور على زوج مفضل نشط: {preferred_pair.symbol}")
                                        break
                                
                                # إذا لم نجد أي زوج مفضل، استخدم أي زوج OTC نشط
                                if not alt_otc_pair:
                                    alt_otc_pair = OTCPair.query.filter_by(is_active=True).first()
                            
                            if alt_otc_pair:
                                logger.info(f"Using OTC pair {alt_otc_pair.symbol} as proxy for alternative market pair {available_pair.symbol}")
                                
                                # تعيين علامة توضح أن هذا زوج متاح فعلياً للتداول
                                # حتى يمكن للمستخدمين التداول عليه بدلاً من الزوج الأصلي غير المتاح
                                # دالة لفحص ما إذا كان الزوج في قائمة الأزواج ذات العائد الجيد
                                def is_pair_in_good_payout_list(pair_symbol):
                                    """التحقق مما إذا كان الزوج في قائمة الأزواج ذات العائد الجيد"""
                                    # قائمة الأزواج المعروفة بأنها ذات عائد جيد
                                    good_payout_pairs = [
                                        'EURUSD', 'EURGBP', 'EURJPY', 'AUDJPY', 'CADCHF',  # أزواج البورصة العادية
                                        'EURUSD-OTC', 'EURGBP-OTC', 'EURJPY-OTC', 'USDJPY-OTC', 'AUDJPY-OTC', 'CADCHF-OTC'  # أزواج OTC
                                    ]
                                    
                                    pair_symbol = pair_symbol.strip()
                                    
                                    # تطبيق فحص دقيق - تجاهل الفروق بين الأحرف الكبيرة والصغيرة
                                    if any(pair_symbol.upper() == good.upper() for good in good_payout_pairs):
                                        logger.info(f"✅ الزوج {pair_symbol} معروف أنه متاح في قائمة الأزواج الجيدة")
                                        return True
                                        
                                    # فحص أكثر مرونة - يبحث عن وجود الزوج ضمن قائمة الأزواج الجيدة
                                    if any(pair_symbol.upper() in good.upper() for good in good_payout_pairs):
                                        logger.info(f"⚠️ الزوج {pair_symbol} قد يكون متاحًا (تطابق جزئي مع الأزواج الجيدة)")
                                        return True
                                        
                                    logger.warning(f"❌ الزوج {pair_symbol} غير موجود في قائمة الأزواج ذات العائد الجيد")
                                    return False
                                if is_pair_in_good_payout_list(alt_otc_pair.symbol):
                                    logger.info(f"✅✅ الزوج {alt_otc_pair.symbol} متاح فعلياً للتداول بعائد جيد")
                                
                                signal = generate_signal(current_bot, alt_otc_pair.id, is_doubling=False)
                                
                                if signal:
                                    logger.info(f"Successfully generated automated signal for alternative market pair {available_pair.symbol}")
                                else:
                                    logger.error("Failed to generate automated signal for alternative market pair")
                            else:
                                logger.error("No OTC pairs available to use as proxy - this should never happen")
                        else:
                            logger.error("❌ No available market pairs found for trading at this time")
                
            except Exception as e:
                logger.error(f"Error in signal generation: {e}")
                logger.exception("Detailed exception:")
        else:
            logger.info("No active bots found for signal generation")
            
        # تسجيل انتهاء العملية
        logger.info("=== SIGNAL GENERATION COMPLETED ===")
        
        # تسجيل موعد الإشارة التالية
        import signal_manager
        # تعيين وقت بداية أول إشارة تالية بعد 5 دقائق
        last_signal = Signal.query.filter_by(doubling_strategy=False).order_by(Signal.created_at.desc()).first()
        if last_signal:
            signal_manager.last_signal_time = last_signal.created_at
        else:
            # إذا لم تكن هناك إشارات سابقة
            signal_manager.last_signal_time = datetime.utcnow()
        
        # حساب الوقت المتبقي للإشارة التالية
        next_time = signal_manager.get_time_until_next_signal()
        minutes = next_time // 60
        seconds = next_time % 60
        logger.info(f"Next signal will be generated in {next_time} seconds ({minutes} minutes, {seconds} seconds)")
            

# دالة مخصصة للتحقق من الإشارات المنتهية
def check_expired_signals():
    """Check for expired signals for accurate results"""
    with app.app_context():
        logger.info("Manual signal checking started")
        check_signal_results(bot)

# هنا سنستخدم خيط منفصل للتحقق والإرسال بدلاً من جدولة APScheduler
import threading
import time

def signal_worker():
    """Worker thread to handle signal generation and checking - DISABLED"""
    logger.info("Signal worker thread disabled - using signal_manager.py instead")
    
    # تم تعطيل هذه الدالة واستبدالها بنظام signal_manager.py
    return

# قتل أي عمليات جدولة موجودة
try:
    from flask_apscheduler import APScheduler as FlaskAPScheduler
    flask_scheduler = FlaskAPScheduler()
    flask_scheduler.shutdown(wait=False)
    logger.info("تم إيقاف جدولة Flask-APScheduler")
except:
    logger.info("لم يتم العثور على Flask-APScheduler")

# تأكيد إضافي على حذف المهام
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    background_scheduler = BackgroundScheduler()
    background_scheduler.shutdown(wait=False)
    logger.info("تم إيقاف جدولة BackgroundScheduler")
except:
    logger.info("لم يتم العثور على BackgroundScheduler")

# حدد وقت البدء لضمان تسلسل سليم للإشارات
# تعيين وقت آخر إشارة ليكون قبل 5 دقائق تمامًا
last_signal_time = datetime.utcnow() - timedelta(seconds=SIGNAL_INTERVAL_SECONDS)
logger.info(f"تم تعيين وقت الإشارة الأخيرة إلى: {last_signal_time}")

# تعطيل نظام الإشارات القديم تمامًا

# بدء تشغيل نظام الإشارات الجديد (signal_manager.py)
import signal_manager

def configure_signal_manager():
    """ربط دوال مدير الإشارات بدوال التطبيق الحالية"""
    # تعريف دالة العمل التي سيتم استدعاؤها عند إنشاء إشارة
    def signal_worker_function():
        """الدالة التي يتم استدعاؤها من مدير الإشارات للتحقق وإنشاء الإشارات"""
        try:
            with app.app_context():
                # التحقق من الإشارات المنتهية
                check_expired_signals()
                
                # عندما يحين وقت إنشاء إشارة
                if signal_manager.is_time_to_generate_signal():
                    logger.info("🚀🚀🚀 حان وقت إنشاء إشارة جديدة - تم استدعاء الدالة من مدير الإشارات 🚀🚀🚀")
                    # تنفيذ الدالة الفعلية لإنشاء الإشارة
                    _real_generate_new_signal()
                    logger.info("✅✅✅ تم إنشاء إشارة جديدة بنجاح ✅✅✅")
        except Exception as e:
            logger.error(f"❌❌❌ خطأ في signal_worker_function: {e}")
            logger.exception("تفاصيل الخطأ:")
                
    # تعيين دالة العمل في مدير الإشارات
    signal_manager.worker_function = signal_worker_function
    
    # إعادة تهيئة المتغيرات لضمان عمل النظام
    signal_manager.is_signal_system_running = True  # تأكد من تشغيل النظام
    signal_manager.is_signal_generation_locked = False  # فك قفل توليد الإشارات
    signal_manager.last_signal_time = datetime.utcnow() - timedelta(seconds=signal_manager.SIGNAL_INTERVAL_SECONDS + 10)  # تعيين وقت منذ أكثر من 5 دقائق
    
    # بدء تشغيل نظام الإشارات أولاً - سيرسل إشارات كل 5 دقائق بالضبط
    signal_manager.start_signal_system()
    logger.info("✅✅✅ تم بدء تشغيل نظام الإشارات بنجاح (SIGNAL_INTERVAL = 300 ثانية / 5 دقائق) ✅✅✅")
    
    # إرسال إشارة فورية للتأكد من استئناف النظام بعد إعادة التشغيل
    try:
        with app.app_context():
            logger.info("↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓")
            logger.info("🔄 توليد إشارة فورية لاستئناف النظام بعد تحديثه")
            logger.info("🔄 إجبار النظام على توليد إشارة الآن بغض النظر عن الوقت")
            logger.info("↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑")
            
            # إنشاء إشارة جديدة مباشرة
            _real_generate_new_signal()
    except Exception as e:
        logger.error(f"❌❌❌ خطأ في إنشاء إشارة فورية: {e}")
        logger.exception("تفاصيل الخطأ:")

# تشغيل نظام الإشارات عند بدء التطبيق
try:
    logger.info("تهيئة نظام الإشارات المركزي...")
    configure_signal_manager()
    logger.info("تم بدء تشغيل نظام الإشارات المركزي بنجاح")
except Exception as e:
    logger.error(f"خطأ في بدء تشغيل نظام الإشارات: {e}")
    logger.exception("تفاصيل الخطأ:")

# Function to fix signal expiration times based on entry time and duration
def fix_signal_expiration_times():
    """Fix all signal expiration times to ensure they are correct based on entry time and duration"""
    try:
        with app.app_context():
            logger.info("Starting to fix signal expiration times")
            
            # Get all signals
            signals = Signal.query.all()
            logger.info(f"Found {len(signals)} signals to check")
            
            for signal in signals:
                try:
                    # Get current UTC time
                    current_time = datetime.utcnow()
                    
                    # Get the entry time in Turkey timezone (UTC+3)
                    entry_time_str = signal.entry_time  # Format: HH:MM
                    
                    # Convert entry time string to a datetime (today) in Turkey timezone
                    turkey_now = current_time + timedelta(hours=3)
                    entry_time_parts = entry_time_str.split(':')
                    
                    # Create the entry time datetime in Turkey timezone
                    turkey_entry_time = turkey_now.replace(
                        hour=int(entry_time_parts[0]), 
                        minute=int(entry_time_parts[1]), 
                        second=0, 
                        microsecond=0
                    )
                    
                    # If the constructed entry time is in the future (from the signal creation), 
                    # it likely means the signal was created yesterday
                    if turkey_entry_time > signal.created_at + timedelta(hours=3, minutes=10):
                        # Adjust to yesterday
                        turkey_entry_time = turkey_entry_time - timedelta(days=1)
                    
                    # Calculate the real expiration time (entry time + duration in Turkey timezone)
                    real_expiration_time_turkey = turkey_entry_time + timedelta(minutes=signal.duration)
                    
                    # Convert back to UTC for storage
                    real_expiration_time_utc = real_expiration_time_turkey - timedelta(hours=3)
                    
                    # Update the signal expiration time
                    signal.expiration_time = real_expiration_time_utc
                    
                    logger.info(f"Updated signal {signal.id}:")
                    logger.info(f"  - Entry time (Turkey): {turkey_entry_time}")
                    logger.info(f"  - Duration: {signal.duration} minutes")
                    logger.info(f"  - New expiration time (UTC): {real_expiration_time_utc}")
                
                except Exception as e:
                    logger.error(f"Error fixing signal {signal.id}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logger.info("Finished fixing signal expiration times")
            
    except Exception as e:
        logger.error(f"Error in fix_signal_expiration_times: {e}")
        logger.exception("Detailed exception:")
        db.session.rollback()

# Run the fix on startup (will only run once)
# fix_signal_expiration_times()

# Route for UptimeRobot to ping
@app.route('/ping', methods=['GET'])
def ping():
    """
    Simple endpoint for uptime monitoring services like UptimeRobot.
    Returns a 200 OK response to indicate the application is running.
    """
    from datetime import datetime
    return jsonify({
        "status": "ok",
        "message": "Application is running",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "uptime": "24/7 monitoring active"
    })

# Route to get signal system status
@app.route('/signal_status', methods=['GET'])
def signal_status():
    """
    أداة لمراقبة حالة نظام الإشارات وإعادة تشغيله إذا لزم الأمر
    """
    import signal_manager
    
    # التحقق مما إذا كان المستخدم قد طلب إعادة تشغيل النظام
    restart = request.args.get('restart', 'false').lower() == 'true'
    
    if restart:
        signal_manager.restart_signal_system()
        flash('تم إعادة تشغيل نظام الإشارات بنجاح', 'success')
    
    # الحصول على حالة النظام
    system_status = signal_manager.get_signal_status()
    
    # إضافة معلومات حول وقت الإشارة القادمة
    system_status['seconds_till_next_signal'] = signal_manager.get_time_until_next_signal()
    
    # إضافة معلومات أزواج البورصة العادية المتاحة للتداول
    from market_pairs import get_tradable_pairs, get_tradable_pairs_with_good_payout
    system_status['tradable_pairs_count'] = len(get_tradable_pairs())
    
    # الحصول على الأزواج ذات نسبة العائد الجيد (85% فأكثر)
    good_payout_pairs = get_tradable_pairs_with_good_payout()
    system_status['good_payout_pairs_count'] = len(good_payout_pairs)
    system_status['good_payout_pairs'] = good_payout_pairs[:20]  # إظهار أول 20 زوج فقط
    
    # إضافة معلومات الأزواج من قاعدة البيانات
    try:
        from models import OTCPair
        system_status['otc_pairs_count'] = OTCPair.query.filter_by(is_active=True).count()
        try:
            # التحقق إذا كان جدول أزواج البورصة العادية موجود
            from models import MarketPair
            system_status['market_pairs_count'] = MarketPair.query.filter_by(is_active=True).count()
        except:
            system_status['market_pairs_count'] = "لا يوجد جدول للأزواج"
    except Exception as e:
        system_status['error'] = str(e)
    
    # Check if JSON format is requested
    if request.args.get('format') == 'json':
        return jsonify(system_status)
    
    # إضافة زر لإعادة تشغيل النظام
    restart_url = url_for('signal_status', restart='true')
    
    return render_template(
        'signal_status.html', 
        status=system_status,
        restart_url=restart_url
    )

# Route to manually fix signal expiration times
@app.route('/admin/fix_signals', methods=['GET'])
@admin_required
def fix_signals():
    """Manually trigger the signal expiration time fixer"""
    fix_signal_expiration_times()
    flash('تم تصحيح أوقات انتهاء الإشارات بنجاح', 'success')
    return redirect(url_for('admin_panel'))

# Index route (homepage)
@app.route('/', methods=['GET'])
def index():
    # Get language preference from query parameter
    lang = request.args.get('lang', 'ar')
    
    # Check if user is logged in
    user = None
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user = current_user
    
    # Render the appropriate template based on language
    if lang == 'en':
        return render_template('index_en.html', lang=lang, user=user)
    elif lang == 'tr':
        return render_template('index_tr.html', lang=lang, user=user)
    else:
        # Default to Arabic
        return render_template('index.html', lang=lang, user=user)

# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username')  # يمكن أن يكون اسم المستخدم أو معرف تيليجرام
        password = request.form.get('password')
        
        # البحث عن المشرف بواسطة اسم المستخدم أو معرف تيليجرام
        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.telegram_id == identifier)
        ).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.id
            app.logger.info(f"Admin logged in successfully: {admin.username}")
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('admin_panel'))
        else:
            app.logger.warning(f"Failed login attempt for: {identifier}")
            flash('اسم المستخدم/معرف تيليجرام أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('login.html')

# Admin panel route
@app.route('/admin', methods=['GET'])
@admin_required
def admin_panel():
    # Get current admin user
    admin_id = session.get('admin_id')
    admin = Admin.query.get(admin_id)
    
    if not admin:
        session.clear()
        flash('Admin session expired. Please login again.', 'danger')
        return redirect(url_for('login'))
    
    users = User.query.all()
    admins = Admin.query.all()
    approved_channels = ApprovedChannel.query.all()
    otc_pairs = OTCPair.query.all()
    signals = Signal.query.order_by(Signal.created_at.desc()).limit(20).all()
    bots = BotConfiguration.query.all()
    
    # Calculate counts for statistics
    users_count = User.query.filter_by(is_active=True).count()
    signals_count = Signal.query.count()
    bots_count = BotConfiguration.query.filter_by(is_active=True).count()
    channels_count = ApprovedChannel.query.count()
    
    # Calculate success rate
    success_signals = Signal.query.filter_by(result='WIN').count()
    success_rate = 0
    if signals_count > 0:
        success_rate = round((success_signals / signals_count) * 100)
    
    return render_template(
        'admin_panel.html',
        admin=admin,
        users=users, 
        admins=admins,
        approved_channels=approved_channels,
        otc_pairs=otc_pairs,
        signals=signals,
        bots=bots,
        users_count=users_count,
        signals_count=signals_count,
        bots_count=bots_count,
        channels_count=channels_count,
        success_rate=success_rate
    )

# Route for adding users
@app.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        telegram_id = request.form.get('telegram_id')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        pocket_option_id = request.form.get('pocket_option_id', '')
        language_code = request.form.get('language_code', 'ar')
        is_active = 'is_active' in request.form
        is_premium = 'is_premium' in request.form
        
        # Parse expiration date if provided
        expiration_date_str = request.form.get('expiration_date')
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
            except ValueError:
                expiration_date = datetime.now() + timedelta(days=30)
        else:
            expiration_date = datetime.now() + timedelta(days=30)
        
        # التحقق من البيانات المدخلة
        if not telegram_id:
            flash('معرف تيليجرام مطلوب', 'error')
            return redirect(url_for('admin_panel'))
            
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(telegram_id=telegram_id).first()
            if existing_user:
                # تحديث معلومات المستخدم الموجود
                app.logger.info(f"Updating user with Telegram ID: {telegram_id}")
                existing_user.username = username
                if password:
                    existing_user.password_hash = generate_password_hash(password)
                existing_user.first_name = first_name
                existing_user.last_name = last_name
                existing_user.pocket_option_id = pocket_option_id
                existing_user.language_code = language_code
                existing_user.is_active = is_active
                existing_user.is_premium = is_premium
                existing_user.expiration_date = expiration_date
                db.session.commit()
                app.logger.info(f"Successfully updated user: {username} ({telegram_id})")
                flash('تم تحديث المستخدم بنجاح', 'success')
            else:
                # إنشاء مستخدم جديد
                app.logger.info(f"Creating new user with Telegram ID: {telegram_id}")
                new_user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    pocket_option_id=pocket_option_id,
                    language_code=language_code,
                    is_active=is_active,
                    is_premium=is_premium,
                    expiration_date=expiration_date
                )
                if password:
                    new_user.password_hash = generate_password_hash(password)
                db.session.add(new_user)
                db.session.commit()
                app.logger.info(f"Successfully created new user: {username} ({telegram_id})")
                flash('تم إضافة المستخدم بنجاح', 'success')
            
            return redirect(url_for('admin_panel'))
            
        except Exception as e:
            # مناولة أي استثناءات قد تحدث أثناء العملية
            db.session.rollback()
            error_msg = str(e)
            app.logger.error(f"Error adding/updating user: {error_msg}")
            flash(f'خطأ في إضافة/تحديث المستخدم: {error_msg}', 'danger')
            return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

# Route for deleting users - both URL formats for compatibility
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    app.logger.info(f"Deleting/deactivating user with ID: {user_id}")
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    
    flash('تم إلغاء تفعيل المستخدم بنجاح', 'success')
    return redirect(url_for('admin_panel'))

# طريقة بديلة لتحديث المستخدم
@app.route('/user/update', methods=['POST'])
@admin_required
def update_user_alt():
    try:
        user_id = request.form.get('user_id', type=int)
        if not user_id:
            flash('معرف المستخدم مطلوب', 'error')
            return redirect(url_for('admin_panel'))
            
        user = User.query.get_or_404(user_id)
        
        app.logger.info(f"Updating user with ID: {user_id}")
        
        # تحقق مما إذا كان النموذج هو نموذج تمديد صلاحية فقط
        # في هذه الحالة، ستكون expiration_days موجودة فقط
        expiration_days = request.form.get('expiration_days', type=int)
        is_extension_only = (expiration_days and 
                             'telegram_id' not in request.form and 
                             'username' not in request.form and 
                             'password' not in request.form and 
                             'pocket_option_id' not in request.form)
        
        if is_extension_only:
            # إذا كان النموذج هو فقط لتمديد الصلاحية، نحتفظ بجميع بيانات المستخدم الحالية
            app.logger.info(f"Extension only for user ID: {user_id}, adding {expiration_days} days")
            
            # تحديث تاريخ انتهاء الصلاحية فقط
            if user.expiration_date and user.expiration_date > datetime.utcnow():
                user.expiration_date = user.expiration_date + timedelta(days=expiration_days)
            else:
                user.expiration_date = datetime.utcnow() + timedelta(days=expiration_days)
            
            # لا تغير حالة التفعيل - احتفظ بالحالة الحالية
            # نحن لا نعيّن is_active هنا

            db.session.commit()
            app.logger.info(f"Successfully extended expiration for user ID: {user_id} to {user.expiration_date}")
            flash('تم تمديد صلاحية المستخدم بنجاح', 'success')
            
        else:
            # هذا هو المسار العادي لتحديث المستخدم
            telegram_id = request.form.get('telegram_id')
            username = request.form.get('username')
            password = request.form.get('password')
            pocket_option_id = request.form.get('pocket_option_id')
            first_name = request.form.get('first_name', user.first_name)
            last_name = request.form.get('last_name', user.last_name)
            is_active = 'is_active' in request.form
            is_premium = 'is_premium' in request.form
            
            # التحقق من صحة البيانات
            if not telegram_id:
                flash('معرف تيليجرام مطلوب', 'error')
                return redirect(url_for('admin_panel'))
                
            # Update user information
            user.telegram_id = telegram_id
            user.username = username
            user.pocket_option_id = pocket_option_id
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.is_premium = is_premium
            
            # Update password if provided
            if password and password.strip():
                user.password_hash = generate_password_hash(password)
            
            # Update expiration date if provided
            if expiration_days:
                # If user already has an expiration date, extend from there
                if user.expiration_date and user.expiration_date > datetime.utcnow():
                    user.expiration_date = user.expiration_date + timedelta(days=expiration_days)
                else:
                    # Otherwise set from current date
                    user.expiration_date = datetime.utcnow() + timedelta(days=expiration_days)
            
            db.session.commit()
            app.logger.info(f"Successfully updated user ID: {user_id}, Username: {username}, Telegram ID: {telegram_id}")
            flash('تم تحديث بيانات المستخدم بنجاح', 'success')
        
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        error_msg = str(e)
        app.logger.error(f"Error updating user {user_id}: {error_msg}")
        flash(f'خطأ في تحديث المستخدم: {error_msg}', 'danger')
        
    return redirect(url_for('admin_panel'))


# Route for updating users - both URL formats for compatibility
@app.route('/update_user/<int:user_id>', methods=['POST'])
@app.route('/admin/update_user/<int:user_id>', methods=['POST'])
@admin_required
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        app.logger.info(f"Updating user with ID: {user_id}")
        
        telegram_id = request.form.get('telegram_id')
        username = request.form.get('username')
        password = request.form.get('password')
        pocket_option_id = request.form.get('pocket_option_id')
        expiration_days = request.form.get('expiration_days', type=int)
        first_name = request.form.get('first_name', user.first_name)
        last_name = request.form.get('last_name', user.last_name)
        is_active = 'is_active' in request.form
        is_premium = 'is_premium' in request.form
        
        # التحقق من صحة البيانات
        if not telegram_id:
            flash('معرف تيليجرام مطلوب', 'error')
            return redirect(url_for('admin_panel'))
            
        # Update user information
        user.telegram_id = telegram_id
        user.username = username
        user.pocket_option_id = pocket_option_id
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = is_active
        user.is_premium = is_premium
        
        # Update password if provided
        if password and password.strip():
            user.password_hash = generate_password_hash(password)
        
        # Update expiration date if provided
        if expiration_days:
            # If user already has an expiration date, extend from there
            if user.expiration_date and user.expiration_date > datetime.utcnow():
                user.expiration_date = user.expiration_date + timedelta(days=expiration_days)
            else:
                # Otherwise set from current date
                user.expiration_date = datetime.utcnow() + timedelta(days=expiration_days)
        
        db.session.commit()
        app.logger.info(f"Successfully updated user ID: {user_id}, Username: {username}, Telegram ID: {telegram_id}")
        flash('تم تحديث بيانات المستخدم بنجاح', 'success')
        
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        error_msg = str(e)
        app.logger.error(f"Error updating user {user_id}: {error_msg}")
        flash(f'خطأ في تحديث المستخدم: {error_msg}', 'danger')
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/get_admin_data/<int:admin_id>', methods=['GET'])
@admin_required
def get_admin_data(admin_id):
    """الحصول على بيانات المشرف بتنسيق JSON"""
    admin = Admin.query.get_or_404(admin_id)
    
    return jsonify({
        "id": admin.id,
        "username": admin.username,
        "telegram_id": admin.telegram_id,
        "is_moderator": admin.is_moderator
    })

@app.route('/admin/get_bot_data/<int:bot_id>', methods=['GET'])
@admin_required
def get_bot_data(bot_id):
    """الحصول على بيانات البوت بتنسيق JSON"""
    bot = BotConfiguration.query.get_or_404(bot_id)
    
    return jsonify({
        "id": bot.id,
        "name": bot.name,
        "api_token": bot.api_token,
        "description": bot.description,
        "is_active": bot.is_active,
        "expiration_date": bot.expiration_date.isoformat() if bot.expiration_date else None
    })

@app.route('/admin/update_bot/<int:bot_id>', methods=['POST'])
@admin_required
def update_bot(bot_id):
    """تحديث بيانات البوت"""
    bot = BotConfiguration.query.get_or_404(bot_id)
    
    # تحديث البيانات من النموذج
    bot.name = request.form.get('name')
    bot.api_token = request.form.get('api_token')
    bot.description = request.form.get('description')
    bot.is_active = 'is_active' in request.form
    
    # تحديث تاريخ الانتهاء إذا كان موجودًا
    expiration_date_str = request.form.get('expiration_date')
    if expiration_date_str:
        try:
            bot.expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"success": False, "message": "تنسيق تاريخ الانتهاء غير صحيح"}), 400
    else:
        # إذا تم إرسال قيمة فارغة، قم بإزالة تاريخ الانتهاء
        bot.expiration_date = None
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "تم تحديث البوت بنجاح"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/admin/delete_bot/<int:bot_id>', methods=['POST'])
@admin_required
def delete_bot(bot_id):
    """حذف البوت"""
    bot = BotConfiguration.query.get_or_404(bot_id)
    
    try:
        db.session.delete(bot)
        db.session.commit()
        return jsonify({"success": True, "message": "تم حذف البوت بنجاح"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"حدث خطأ: {str(e)}"}), 500

# Route for adding admins
@app.route('/add_admin', methods=['POST'])
@admin_required
def add_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        telegram_id = request.form.get('telegram_id', '')
        is_moderator = 'is_moderator' in request.form
        
        if not username or not password:
            flash('اسم المستخدم وكلمة المرور مطلوبين', 'danger')
            return redirect(url_for('admin_panel'))
        
        # Check if admin already exists
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin and existing_admin.telegram_id != telegram_id:
            flash('اسم المستخدم موجود بالفعل', 'danger')
            return redirect(url_for('admin_panel'))
            
        existing_admin_by_telegram = None
        if telegram_id:
            existing_admin_by_telegram = Admin.query.filter_by(telegram_id=telegram_id).first()
        
        if existing_admin:
            existing_admin.username = username
            if password:
                existing_admin.password_hash = generate_password_hash(password)
            existing_admin.telegram_id = telegram_id
            existing_admin.is_moderator = is_moderator
            db.session.commit()
            flash('تم تحديث المشرف بنجاح', 'success')
        elif existing_admin_by_telegram:
            existing_admin_by_telegram.username = username
            if password:
                existing_admin_by_telegram.password_hash = generate_password_hash(password)
            existing_admin_by_telegram.is_moderator = is_moderator
            db.session.commit()
            flash('تم تحديث المشرف بنجاح', 'success')
        else:
            new_admin = Admin(
                username=username,
                password_hash=generate_password_hash(password),
                telegram_id=telegram_id,
                is_moderator=is_moderator
            )
            db.session.add(new_admin)
            db.session.commit()
            flash('تم إضافة المشرف بنجاح', 'success')
        
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

# Route for updating admins
@app.route('/update_admin/<int:admin_id>', methods=['POST'])
@admin_required
def update_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    
    # Prevent updating the main admin (except by the main admin)
    if admin.id == 1 and current_user.id != 1:
        flash('لا يمكن تعديل المشرف الرئيسي', 'danger')
        return redirect(url_for('admin_panel'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    telegram_id = request.form.get('telegram_id', '')
    is_moderator = 'is_moderator' in request.form
    
    # Update admin information
    admin.username = username
    admin.telegram_id = telegram_id
    admin.is_moderator = is_moderator
    
    # Update password if provided
    if password and password.strip():
        admin.password_hash = generate_password_hash(password)
    
    db.session.commit()
    flash('تم تحديث بيانات المشرف بنجاح', 'success')
    return redirect(url_for('admin_panel'))

# API route for deleting admins
@app.route('/api/admins/<int:admin_id>', methods=['DELETE', 'POST'])
@admin_required
def delete_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    
    # Prevent deleting the main admin
    if admin.id == 1:
        if request.method == 'DELETE':
            return jsonify({"status": "error", "message": "Cannot delete the main admin"}), 403
        else:
            flash('لا يمكن حذف المشرف الرئيسي', 'danger')
            return redirect(url_for('admin_panel'))
    
    db.session.delete(admin)
    db.session.commit()
    
    if request.method == 'DELETE':
        return jsonify({"status": "success", "message": "Admin deleted successfully"})
    else:
        flash('تم حذف المشرف بنجاح', 'success')
        return redirect(url_for('admin_panel'))

# Route for adding approved channels
@app.route('/admin/add_channel', methods=['POST'])
@app.route('/add_channel', methods=['POST'])  # Additional route for template compatibility
@admin_required
def add_channel():
    if request.method == 'POST':
        channel_id = request.form.get('channel_id')
        channel_name = request.form.get('channel_name', '')
        bot_id = request.form.get('bot_id')
        expiration_date_str = request.form.get('expiration_date')
        
        if not channel_id:
            flash('معرف القناة مطلوب', 'danger')
            return redirect(url_for('admin_panel'))
            
        # تنسيق معرف القناة بالشكل الصحيح للاستخدام مع API تيليجرام
        channel_id = format_telegram_channel_id(channel_id)
        
        # تحويل تاريخ الانتهاء إذا كان موجودًا
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
            except ValueError:
                flash('تنسيق تاريخ الانتهاء غير صحيح', 'warning')
        
        # Check if channel already exists
        existing_channel = ApprovedChannel.query.filter_by(channel_id=channel_id).first()
        if existing_channel:
            existing_channel.channel_name = channel_name
            if bot_id:
                existing_channel.bot_id = bot_id
            existing_channel.expiration_date = expiration_date
            db.session.commit()
            flash('تم تحديث القناة بنجاح', 'success')
        else:
            new_channel = ApprovedChannel(
                channel_id=channel_id,
                channel_name=channel_name,
                bot_id=bot_id,
                expiration_date=expiration_date
            )
            db.session.add(new_channel)
            db.session.commit()
            flash('تم إضافة القناة بنجاح', 'success')
        
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

# Route for adding bot configurations
@app.route('/admin/add_bot', methods=['POST'])
@app.route('/add_bot', methods=['POST'])  # Additional route for template compatibility
@admin_required
def add_bot():
    if request.method == 'POST':
        name = request.form.get('name')
        api_token = request.form.get('api_token')
        description = request.form.get('description', '')
        channels_input = request.form.get('channels', '[]')  # JSON string of channel IDs
        is_active = 'is_active' in request.form
        expiration_date_str = request.form.get('expiration_date')
        language = request.form.get('language', 'ar')  # اللغة الافتراضية هي العربية
        send_results = 'send_results' in request.form
        use_doubling = 'use_doubling' in request.form
        
        if not name or not api_token:
            flash('اسم البوت وتوكن API مطلوبان', 'danger')
            return redirect(url_for('admin_panel'))
        
        # تحويل تاريخ الانتهاء إذا كان موجودًا
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
            except ValueError:
                flash('تنسيق تاريخ الانتهاء غير صحيح', 'warning')
        
        # إعداد JSON للإعدادات بدلاً من مجرد قائمة القنوات
        import json
        # إذا كان المدخل يبدأ بـ [ وينتهي بـ ]، فهو قائمة قديمة من معرفات القنوات
        if channels_input.strip().startswith('[') and channels_input.strip().endswith(']'):
            # تخزين إعدادات البوت وقائمة القنوات معاً في حقل channels
            settings = {
                "language": language,
                "send_results": send_results,
                "use_doubling": use_doubling,
                "channel_ids": json.loads(channels_input)  # تحويل قائمة القنوات من نص إلى قائمة Python
            }
            channels = json.dumps(settings)
        else:
            # في حالة كان المدخل هو JSON للإعدادات بالفعل
            channels = channels_input
            
        new_bot = BotConfiguration(
            name=name,
            api_token=api_token,
            description=description,
            channels=channels,
            is_active=is_active,
            expiration_date=expiration_date
        )
        db.session.add(new_bot)
        db.session.commit()
        
        flash('تم إضافة البوت بنجاح', 'success')
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

# Route for toggling bot activation/deactivation
@app.route('/admin/toggle_bot/<int:bot_id>/<string:action>', methods=['POST'])
@admin_required
def toggle_bot(bot_id, action):
    """تفعيل أو تعطيل البوت"""
    bot = BotConfiguration.query.get_or_404(bot_id)
    
    if action == 'activate':
        bot.is_active = True
        message = 'تم تفعيل البوت بنجاح'
    elif action == 'deactivate':
        bot.is_active = False
        message = 'تم تعطيل البوت بنجاح'
    else:
        return jsonify({"success": False, "message": "إجراء غير صالح"}), 400
    
    db.session.commit()
    return jsonify({"success": True, "message": message})

# Route for getting channel data
@app.route('/admin/get_channel_data/<int:channel_id>', methods=['GET'])
@admin_required
def get_channel_data(channel_id):
    """الحصول على بيانات القناة بتنسيق JSON"""
    channel = ApprovedChannel.query.get_or_404(channel_id)
    
    channel_data = {
        'id': channel.id,
        'channel_id': channel.channel_id,
        'channel_name': channel.channel_name,
        'bot_id': channel.bot_id,
        'expiration_date': channel.expiration_date.isoformat() if channel.expiration_date else None,
        'created_at': channel.created_at.isoformat()
    }
    
    return jsonify(channel_data)

# Route for updating channel
@app.route('/admin/update_channel/<int:channel_id>', methods=['POST'])
@admin_required
def update_channel(channel_id):
    """تحديث بيانات القناة"""
    channel = ApprovedChannel.query.get_or_404(channel_id)
    
    channel_id_str = request.form.get('channel_id')
    channel_name = request.form.get('channel_name')
    bot_id = request.form.get('bot_id')
    expiration_date_str = request.form.get('expiration_date')
    
    # التحقق من أن المعرف ليس فارغًا
    if not channel_id_str:
        flash('معرف القناة مطلوب', 'danger')
        return redirect(url_for('admin_panel'))
        
    # تنسيق معرف القناة بالشكل الصحيح للاستخدام مع API تيليجرام
    channel_id_str = format_telegram_channel_id(channel_id_str)
    
    # تحويل تاريخ الانتهاء إذا كان موجودًا
    expiration_date = None
    if expiration_date_str:
        try:
            expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
        except ValueError:
            flash('تنسيق تاريخ الانتهاء غير صحيح', 'warning')
    
    try:
        channel.channel_id = channel_id_str
        channel.channel_name = channel_name
        channel.bot_id = bot_id
        channel.expiration_date = expiration_date
        
        db.session.commit()
        flash('تم تحديث القناة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating channel: {e}")
        flash('حدث خطأ أثناء تحديث القناة', 'danger')
        
    return redirect(url_for('admin_panel'))

# Route for deleting channel
@app.route('/admin/delete_channel/<int:channel_id>', methods=['POST'])
@admin_required
def delete_channel(channel_id):
    """حذف قناة"""
    channel = ApprovedChannel.query.get_or_404(channel_id)
    
    try:
        db.session.delete(channel)
        db.session.commit()
        flash('تم حذف القناة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting channel: {e}")
        flash('حدث خطأ أثناء حذف القناة', 'danger')
        
    return redirect(url_for('admin_panel'))

# Route for managing OTC pairs
@app.route('/admin/add_otc_pair', methods=['POST'])
@app.route('/add_otc_pair', methods=['POST'])  # Additional route for template compatibility
@admin_required
def add_otc_pair():
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        
        if not symbol:
            flash('رمز الزوج مطلوب', 'danger')
            return redirect(url_for('admin_panel'))
        
        # Check if OTC pair already exists
        existing_pair = OTCPair.query.filter_by(symbol=symbol).first()
        if existing_pair:
            flash('زوج التداول موجود بالفعل', 'danger')
            return redirect(url_for('admin_panel'))
        
        new_pair = OTCPair(symbol=symbol)
        db.session.add(new_pair)
        db.session.commit()
        flash('تم إضافة زوج التداول بنجاح', 'success')
        
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

# API route for deleting OTC pairs
@app.route('/api/otc_pairs/<int:pair_id>', methods=['DELETE'])
@admin_required
def delete_otc_pair(pair_id):
    otc_pair = OTCPair.query.get_or_404(pair_id)
    db.session.delete(otc_pair)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "OTC pair deleted successfully"})
    
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
        from models import AdSettings
        settings = AdSettings.query.first()
        
        # إذا لم تكن هناك إعدادات، أو كانت الإعلانات معطلة، لا تعرض الإعلانات
        if not settings or not settings.ads_enabled:
            return False
        
        # التحقق من نوع الصفحة
        if page_type == 'homepage':
            return settings.show_in_homepage
        elif page_type == 'dashboard':
            return settings.show_in_dashboard
        elif page_type == 'results':
            return settings.show_in_results
        
        # افتراضيًا، لا تعرض الإعلانات
        return False
    except Exception as e:
        logger.error(f"خطأ في should_show_ads: {e}")
        return False
    
# مسار إعدادات الإعلانات في لوحة التحكم
@app.route('/admin/ads-settings', methods=['GET', 'POST'])
@app.route('/admin_ads_settings', methods=['GET', 'POST'])  # مسار إضافي للتوافق مع القوالب الحالية
@admin_required
def admin_ads_settings():
    """صفحة إعدادات الإعلانات في لوحة التحكم"""
    
    # الحصول على الإعدادات الحالية
    settings = AdSettings.query.first()
    
    # إذا لم تكن هناك إعدادات، قم بإنشاء إعدادات افتراضية
    if not settings:
        settings = AdSettings()
        settings.ads_enabled = False
        settings.show_in_homepage = True
        settings.show_in_dashboard = False
        settings.show_in_results = True
        settings.max_ads_per_page = 3
        db.session.add(settings)
        db.session.commit()
    
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

# Webhook route for Telegram updates
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Process Telegram updates from webhook.
    This route receives updates from Telegram when a user interacts with the bot.
    It handles commands like /start to show the welcome message.
    """
    logger.info("Webhook received a request")
    if request.headers.get('content-type') == 'application/json':
        try:
            update_json = request.get_json(silent=True)
            logger.info(f"Webhook update received: {update_json}")
            
            # معالجة أمر /start بشكل مباشر باستخدام واجهة API
            if update_json and 'message' in update_json and 'text' in update_json['message'] and update_json['message']['text'] == '/start':
                user_id = update_json['message']['from']['id']
                chat_id = update_json['message']['chat']['id']
                first_name = update_json['message']['from'].get('first_name', 'User')
                language_code = update_json['message']['from'].get('language_code', 'ar')
                
                logger.info(f"Direct handling /start command for user {user_id} ({first_name}) in chat {chat_id}")
                
                # الإرسال المباشر عبر API - الطريقة الأكثر موثوقية
                try:
                    import requests
                    import time
                    
                    # 1. تفعيل الشاشة المتحركة للكتابة أولاً (نشاط البوت)
                    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                    action_url = f"https://api.telegram.org/bot{telegram_token}/sendChatAction"
                    action_payload = {
                        "chat_id": chat_id,
                        "action": "typing"
                    }
                    
                    action_response = requests.post(action_url, json=action_payload, timeout=5)
                    logger.info(f"Send action response: {action_response.status_code}")
                    
                    # إضافة تأخير قصير
                    time.sleep(1)
                    
                    # 2. إنشاء نص رسالة الترحيب
                    if language_code.lower() in ["ar", "arabic"]:
                        message_text = f"""*مرحباً {first_name}* 👋
        
*أهلا بك في بوت إشارات التداول المتقدم!* 🚀
        
🔹 هذا البوت يقدم إشارات تداول عالية الدقة للخيارات الثنائية
🔹 تم تطوير نظام الإشارات باستخدام خوارزميات ذكية للتحليل الفني
🔹 جميع الإشارات تتضمن:
   • رمز الزوج
   • توقيت الدخول
   • مدة التداول
   • نوع الصفقة (CALL/PUT)
   • احتمالية النجاح

🔰 *ستصلك الإشارات بشكل تلقائي كل 5 دقائق تقريباً*

للمزيد من المعلومات أو الاستفسارات، يرجى التواصل مع:
👨‍💻 @ALEPPOMH
        
*شكراً لاستخدامك خدماتنا* 🌟"""
                    else:
                        message_text = f"""*Welcome {first_name}* 👋
        
*Welcome to our Advanced Trading Signals Bot!* 🚀
        
🔹 This bot provides high-accuracy trading signals for binary options
🔹 Our signal system is developed using intelligent technical analysis algorithms
🔹 All signals include:
   • Pair symbol
   • Entry time
   • Trade duration
   • Trade type (CALL/PUT)
   • Success probability

🔰 *You will receive signals automatically approximately every 5 minutes*

For more information or inquiries, please contact:
👨‍💻 @ALEPPOMH
        
*Thank you for using our services* 🌟"""
                    
                    # 3. إرسال رسالة الترحيب مباشرة
                    message_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "📞 Contact Developer",
                                    "url": "https://t.me/ALEPPOMH"
                                }
                            ],
                            [
                                {
                                    "text": "🇺🇸 English",
                                    "callback_data": "lang_en"
                                },
                                {
                                    "text": "🇸🇦 العربية",
                                    "callback_data": "lang_ar"
                                }
                            ],
                            [
                                {
                                    "text": "📊 Sample Signal",
                                    "callback_data": "sample_signal"
                                }
                            ]
                        ]
                    }
                    
                    message_payload = {
                        "chat_id": chat_id,
                        "text": message_text,
                        "parse_mode": "Markdown",
                        "reply_markup": keyboard
                    }
                    
                    # محاولة الإرسال 3 مرات في حالة الفشل
                    success = False
                    error_message = ""
                    
                    for attempt in range(3):
                        try:
                            message_response = requests.post(message_url, json=message_payload, timeout=10)
                            message_response.raise_for_status()
                            message_result = message_response.json()
                            
                            if message_result.get("ok", False):
                                logger.info(f"Successfully sent welcome message directly via API (attempt {attempt+1})")
                                success = True
                                return '', 200
                            else:
                                error_message = message_result.get("description", "Unknown error")
                                logger.warning(f"API returned error on attempt {attempt+1}: {error_message}")
                        except Exception as send_error:
                            error_message = str(send_error)
                            logger.warning(f"Error sending welcome message (attempt {attempt+1}): {error_message}")
                        
                        # إذا فشلت المحاولة، ننتظر قبل إعادة المحاولة
                        if not success and attempt < 2:
                            time.sleep(2)
                    
                    # إذا وصلنا إلى هنا فقد فشلت جميع المحاولات
                    if not success:
                        logger.error(f"Failed to send welcome message after 3 attempts: {error_message}")
                        # سنستمر للطرق الاحتياطية
                
                except Exception as direct_api_error:
                    logger.error(f"Error in direct API welcome message: {direct_api_error}")
                    logger.exception("Direct API exception details:")
                
                # الطريقة الاحتياطية الأولى
                try:
                    from bot.welcome_sender import send_direct_welcome, send_welcome_from_all_bots
                    
                    logger.info(f"Backup method: Trying welcome_sender for user {user_id}")
                    result = send_direct_welcome(chat_id, first_name, language_code)
                    logger.info(f"welcome_sender result: {result}")
                    
                    if result.get("ok", False):
                        return '', 200
                except Exception as e:
                    logger.error(f"Error with welcome_sender: {e}")
                
                # الطريقة الاحتياطية الثانية
                try:
                    from bot.telegram_client import send_direct_welcome_message
                    
                    logger.info(f"Backup method: Trying telegram_client for user {user_id}")
                    result = send_direct_welcome_message(chat_id, first_name, language_code)
                    logger.info(f"telegram_client result: {result}")
                    
                    if result.get("ok", False):
                        return '', 200
                except Exception as e:
                    logger.error(f"Error with telegram_client: {e}")
            
            # استخدام كائن البوت من bot.telegram_bot (الطريقة التقليدية كآخر اختيار)
            from bot.telegram_bot import telegram_bot, setup_bot
            
            if telegram_bot is None:
                # إذا كان البوت غير متاح، نحاول تهيئته مرة أخرى
                logger.warning("Telegram bot is not initialized, trying to initialize it now")
                setup_bot(app)
                from bot.telegram_bot import telegram_bot
            
            # Process the update using the bot instance
            if telegram_bot:
                # تحويل البيانات إلى كائن Update
                from telegram import Update
                update_obj = Update.de_json(update_json, telegram_bot)
                
                # معالجة التحديث بشكل يدوي
                from bot.handlers import start_command
                
                # إذا كان التحديث يحتوي على رسالة وكانت الرسالة تحتوي على الأمر /start
                if update_obj and update_obj.message and update_obj.message.text == '/start':
                    logger.info("Processing /start command through bot instance (fallback)")
                    import asyncio
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(start_command(update_obj, None))
                        logger.info("Start command processed through bot instance")
                    except Exception as e:
                        logger.error(f"Error processing start command: {e}")
                        logger.exception("Start command exception details:")
                        
                        # محاولة أخيرة باستخدام واجهة برمجة التطبيقات مباشرة
                        try:
                            from bot.telegram_client import send_direct_welcome_message
                            result = send_direct_welcome_message(update_obj.effective_chat.id, update_obj.effective_user.first_name, update_obj.effective_user.language_code)
                            logger.info(f"Last resort direct API call result: {result}")
                        except Exception as last_error:
                            logger.error(f"Last resort error: {last_error}")
                else:
                    # دع كائن البوت الأساسي يعالج التحديث
                    from bot.telegram_bot import application
                    if application:
                        application.process_update(update_obj)
                        logger.info("Update processed by application")
                    else:
                        logger.error("Application instance is not available")
                
                logger.info("Update processed successfully")
            else:
                logger.error("Bot instance is not available")
                
                # محاولة استخدام العميل المباشر كملاذ أخير
                if update_json and 'message' in update_json and 'text' in update_json['message'] and update_json['message']['text'] == '/start':
                    try:
                        from bot.telegram_client import send_direct_welcome_message
                        user_id = update_json['message']['from']['id']
                        chat_id = update_json['message']['chat']['id']
                        first_name = update_json['message']['from'].get('first_name', 'User')
                        language_code = update_json['message']['from'].get('language_code', 'ar')
                        
                        result = send_direct_welcome_message(chat_id, first_name, language_code)
                        logger.info(f"Final fallback direct API call result: {result}")
                    except Exception as final_error:
                        logger.error(f"Final fallback error: {final_error}")
            
            return '', 200
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            logger.exception("Detailed exception:")
            return '', 500
    else:
        logger.warning(f"Invalid content type: {request.headers.get('content-type')}")
        return 'Content type must be application/json', 403

# Statistics route
@app.route('/statistics', methods=['GET'])
def statistics():
    # Get language preference from query parameter
    lang = request.args.get('lang', 'ar')
    
    # Get statistics data
    total_signals = Signal.query.count()
    successful_signals = Signal.query.filter_by(result='WIN').count()
    failed_signals = Signal.query.filter_by(result='LOSS').count()
    
    # Calculate success rate
    success_rate = 0
    if total_signals > 0:
        success_rate = round((successful_signals / total_signals) * 100)
    
    # Get today's signals
    today = datetime.utcnow().date()
    today_signals = Signal.query.filter(
        func.date(Signal.created_at) == today
    ).count()
    
    today_successful = Signal.query.filter(
        func.date(Signal.created_at) == today,
        Signal.result == 'WIN'
    ).count()
    
    today_success_rate = 0
    if today_signals > 0:
        today_success_rate = round((today_successful / today_signals) * 100)
    
    # Get weekly data
    weekly_data = {
        'dates': [],
        'success_rates': []
    }
    
    # For the past 7 days
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_signals = Signal.query.filter(
            func.date(Signal.created_at) == day
        ).count()
        
        day_successful = Signal.query.filter(
            func.date(Signal.created_at) == day,
            Signal.result == 'WIN'
        ).count()
        
        day_rate = 0
        if day_signals > 0:
            day_rate = round((day_successful / day_signals) * 100)
        
        weekly_data['dates'].append(day.strftime('%m/%d'))
        weekly_data['success_rates'].append(day_rate)
    
    # Get pair statistics
    pairs = OTCPair.query.all()
    pair_stats = []
    
    for pair in pairs:
        pair_signals = Signal.query.filter(Signal.pair_id == pair.id).count()
        if pair_signals == 0:
            continue
            
        pair_successful = Signal.query.filter(
            Signal.pair_id == pair.id,
            Signal.result == 'WIN'
        ).count()
        
        pair_success_rate = 0
        if pair_signals > 0:
            pair_success_rate = round((pair_successful / pair_signals) * 100)
        
        # Get buy signals
        buy_signals = Signal.query.filter(
            Signal.pair_id == pair.id,
            Signal.direction == 'BUY'
        ).count()
        
        buy_successful = Signal.query.filter(
            Signal.pair_id == pair.id,
            Signal.direction == 'BUY',
            Signal.result == 'WIN'
        ).count()
        
        buy_success_rate = 0
        if buy_signals > 0:
            buy_success_rate = round((buy_successful / buy_signals) * 100)
        
        # Get sell signals
        sell_signals = Signal.query.filter(
            Signal.pair_id == pair.id,
            Signal.direction == 'SELL'
        ).count()
        
        sell_successful = Signal.query.filter(
            Signal.pair_id == pair.id,
            Signal.direction == 'SELL',
            Signal.result == 'WIN'
        ).count()
        
        sell_success_rate = 0
        if sell_signals > 0:
            sell_success_rate = round((sell_successful / sell_signals) * 100)
        
        pair_stats.append({
            'symbol': pair.symbol,
            'total': pair_signals,
            'success_rate': pair_success_rate,
            'buy_signals': buy_signals,
            'buy_success_rate': buy_success_rate,
            'sell_signals': sell_signals,
            'sell_success_rate': sell_success_rate
        })
    
    # Sort by success rate (highest first)
    pair_stats.sort(key=lambda x: x['success_rate'], reverse=True)
    
    # Time distribution
    time_distribution = {
        'hours': [],
        'success_counts': [],
        'failure_counts': []
    }
    
    for hour in range(24):
        time_distribution['hours'].append(f"{hour}:00")
        
        hour_successful = Signal.query.filter(
            func.extract('hour', Signal.created_at) == hour,
            Signal.result == 'WIN'
        ).count()
        
        hour_failed = Signal.query.filter(
            func.extract('hour', Signal.created_at) == hour,
            Signal.result == 'LOSS'
        ).count()
        
        time_distribution['success_counts'].append(hour_successful)
        time_distribution['failure_counts'].append(hour_failed)
    
    # Compile stats
    stats = {
        'total_signals': total_signals,
        'successful_signals': successful_signals,
        'failed_signals': failed_signals,
        'success_rate': success_rate,
        'today_signals': today_signals,
        'today_success_rate': today_success_rate
    }
    
    return render_template(
        'statistics.html',
        lang=lang,
        stats=stats,
        weekly_data=weekly_data,
        pair_stats=pair_stats,
        time_distribution=time_distribution
    )

# Archive route
@app.route('/archive', methods=['GET'])
def archive():
    # Get language preference from query parameter
    lang = request.args.get('lang', 'ar')
    
    # Get archived signals with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Optional filter parameters
    pair_id = request.args.get('pair_id', type=int)
    direction = request.args.get('direction')
    result = request.args.get('result')
    
    # Build query
    query = Signal.query
    
    if pair_id:
        query = query.filter(Signal.pair_id == pair_id)
    
    if direction:
        query = query.filter(Signal.direction == direction)
    
    if result:
        query = query.filter(Signal.result == result)
    
    # Paginate results
    signals = query.order_by(Signal.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all pairs for filter dropdown
    pairs = OTCPair.query.all()
    
    # Just return placeholder template for now
    return render_template(
        'index.html', 
        lang=lang
    )

# خريطة الإشارات الحرارية
@app.route('/heatmap', methods=['GET'])
@admin_required
def heatmap():
    """صفحة خريطة الإشارات الحرارية التفاعلية"""
    return render_template('admin/heatmap.html')

# API endpoint لبيانات الإشارات للخريطة الحرارية
@app.route('/api/heatmap/signals', methods=['GET'])
@admin_required
def heatmap_signals():
    # الحصول على المعلمات
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    pair_id = request.args.get('pair_id')
    direction = request.args.get('direction')
    
    # بناء الاستعلام
    query = Signal.query
    
    # تطبيق المرشحات
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Signal.created_at >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # إضافة يوم كامل لتضمين اليوم الأخير بالكامل
            end_date = end_date + timedelta(days=1)
            query = query.filter(Signal.created_at < end_date)
        except ValueError:
            pass
    
    if pair_id and pair_id != 'all':
        query = query.filter(Signal.pair_id == pair_id)
    
    if direction and direction != 'all':
        query = query.filter(Signal.direction == direction)
    
    # الحصول على نتائج الاستعلام
    signals = query.order_by(Signal.created_at).all()
    
    # تحويل النتائج إلى تنسيق JSON
    signals_data = []
    for signal in signals:
        # الحصول على زوج العملات
        pair = OTCPair.query.get(signal.pair_id)
        pair_symbol = pair.symbol if pair else "Unknown"
        
        # تنسيق النتيجة
        result = signal.result
        if result not in ['WIN', 'LOSS']:
            result = 'EXPIRED'
            
        # تحويل الوقت إلى ساعات ودقائق
        hour = signal.created_at.hour
        minute = signal.created_at.minute
        day_of_week = signal.created_at.weekday()  # 0 = Monday, 6 = Sunday
        
        # إضافة البيانات
        signals_data.append({
            'id': signal.id,
            'pair': pair_symbol,
            'direction': signal.direction,
            'entry_time': signal.entry_time,
            'duration': signal.duration,
            'result': result,
            'created_at': signal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'hour': hour,
            'minute': minute,
            'day_of_week': day_of_week,
            'success_probability': signal.success_probability
        })
    
    return jsonify(signals_data)

# API endpoint للحصول على أزواج العملات للخريطة الحرارية
@app.route('/api/heatmap/pairs', methods=['GET'])
@admin_required
def heatmap_pairs():
    # الحصول على جميع الأزواج
    pairs = OTCPair.query.order_by(OTCPair.symbol).all()
    
    # تحويل النتائج إلى تنسيق JSON
    pairs_data = [{'id': pair.id, 'symbol': pair.symbol} for pair in pairs]
    
    return jsonify(pairs_data)

# API route for getting the latest signal
@app.route('/api/latest-signal', methods=['GET'])
def get_latest_signal():
    latest_signal = Signal.query.order_by(Signal.created_at.desc()).first()
    
    if latest_signal:
        pair = OTCPair.query.get(latest_signal.pair_id)
        expiration_minutes = "1 min"
        
        # Format the signal data
        signal_data = {
            "pair": pair.symbol,
            "direction": latest_signal.direction,
            "entry": latest_signal.entry_time,
            "duration": f"{latest_signal.duration} min",
            "expiration": expiration_minutes,
            "probability": f"{latest_signal.success_probability}%"
        }
        
        return jsonify(signal_data)
    else:
        # Return a demo signal if no signals exist yet
        demo_signal = {
            "pair": "EURUSD-OTC",
            "direction": "SELL",
            "entry": "14:30",
            "duration": "1 min",
            "expiration": "1 min",
            "probability": "85%"
        }
        
        return jsonify(demo_signal)

# إضافة مسار اختبار النماذج
@app.route('/test-forms')
def test_forms():
    """صفحة اختبار النماذج والأزرار - فقط للتطوير"""
    return render_template('test_forms.html')

# Route for logging out
@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# Public Chart Analysis route
@app.route('/chart-analysis', methods=['GET'])
def chart_analysis():
    # Check if user is logged in
    user = None
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        # Redirect to user chart analysis if logged in
        return redirect(url_for('user_chart_analysis'))
    
    # Get language preference from query parameter
    lang = request.args.get('lang', 'ar')
    
    # Get OTC pairs for the form
    otc_pairs = OTCPair.query.all()
    
    # Flash message to login
    flash('يرجى تسجيل الدخول لاستخدام أداة تحليل الشارت', 'info')
    
    # Redirect to login page
    return redirect(url_for('user_login'))

# Chart Analysis processing route
@app.route('/analyze-chart', methods=['POST'])
def analyze_chart():
    try:
        # Get uploaded file
        chart_image = request.files.get('chartImage')
        pair_id = request.form.get('pair')
        timeframe = request.form.get('timeframe', 1)
        
        if not chart_image or not pair_id:
            flash('Please provide both chart image and OTC pair', 'danger')
            return redirect(url_for('chart_analysis'))
        
        # Get the pair symbol
        otc_pair = OTCPair.query.get_or_404(pair_id)
        
        # Read and process the image
        image_data = chart_image.read()
        
        # Analyze the chart image
        analysis_result = analyze_chart_image(image_data, otc_pair.symbol, int(timeframe))
        
        if 'error' in analysis_result:
            flash(f"Analysis failed: {analysis_result['error']}", 'danger')
            return redirect(url_for('chart_analysis'))
        
        # Store result in session for retrieval
        session['chart_analysis_result'] = analysis_result
        
        # Get language preference from query parameter
        lang = request.args.get('lang', 'ar')
        
        # Redirect to chart analysis page to display result
        return redirect(url_for('chart_analysis', lang=lang))
    
    except Exception as e:
        logger.error(f"Error analyzing chart: {e}")
        flash(f"An error occurred during analysis: {str(e)}", 'danger')
        return redirect(url_for('chart_analysis'))

# User Registration
@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        telegram_id = request.form.get('telegram_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        pocket_option_id = request.form.get('pocket_option_id')
        referral_code = request.form.get('referral_code')
        
        # Validate input
        if not telegram_id or not password:
            flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
            return redirect(url_for('user_register'))
            
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'danger')
            return redirect(url_for('user_register'))
            
        # Check if user already exists
        existing_user = User.query.filter_by(telegram_id=telegram_id).first()
        if existing_user:
            flash('معرف تيليجرام مسجل بالفعل', 'danger')
            return redirect(url_for('user_register'))
            
        # Create new user
        new_user = User(
            telegram_id=telegram_id,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            pocket_option_id=pocket_option_id,
            referral_code=referral_code,
            language_code='ar',
            is_active=True,
            is_premium=True if referral_code else False,
            expiration_date=datetime.utcnow() + timedelta(days=30)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('تم تسجيل الحساب بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('user_login'))
        
    return render_template('user_register.html')

# User Login
@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        identifier = request.form.get('telegram_id')  # يمكن أن يكون اسم المستخدم أو معرف تيليجرام
        password = request.form.get('password')
        
        # البحث عن المستخدم بواسطة اسم المستخدم أو معرف تيليجرام
        user = User.query.filter(
            (User.username == identifier) | (User.telegram_id == identifier)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('هذا الحساب معطل. يرجى التواصل مع الإدارة', 'danger')
                return redirect(url_for('user_login'))
                
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            app.logger.info(f"User logged in successfully: {user.username or user.telegram_id}")
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('user_dashboard')
                
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(next_page)
        else:
            app.logger.warning(f"Failed login attempt for: {identifier}")
            flash('اسم المستخدم/معرف تيليجرام أو كلمة المرور غير صحيحة', 'danger')
            
    return render_template('user_login.html')

# User Dashboard
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    # Get user stats
    total_signals = Signal.query.count()
    successful_signals = Signal.query.filter_by(result='WIN').count()
    
    # Calculate success rate
    success_rate = 0
    if total_signals > 0:
        success_rate = round((successful_signals / total_signals) * 100)
    
    # Get today's signals
    today = datetime.utcnow().date()
    today_signals = Signal.query.filter(
        func.date(Signal.created_at) == today
    ).count()
    
    today_success = Signal.query.filter(
        func.date(Signal.created_at) == today,
        Signal.result == 'WIN'
    ).count()
    
    today_success_rate = 0
    if today_signals > 0:
        today_success_rate = round((today_success / today_signals) * 100)
    
    # Get user's chart analyses
    analysis_count = ChartAnalysis.query.filter_by(user_id=current_user.id).count()
    
    # Get recent signals
    recent_signals = Signal.query.order_by(Signal.created_at.desc()).limit(10).all()
    
    # Get latest active signal
    latest_signal = Signal.query.filter(
        Signal.result.is_(None)
    ).order_by(Signal.created_at.desc()).first()
    
    return render_template(
        'user_dashboard.html',
        user=current_user,
        total_signals=total_signals,
        successful_signals=successful_signals,
        success_rate=success_rate,
        today_signals=today_signals,
        today_success_rate=today_success_rate,
        analysis_count=analysis_count,
        recent_signals=recent_signals,
        latest_signal=latest_signal
    )

# User Logout
@app.route('/user/logout')
@login_required
def user_logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('index'))

# Chart Analysis for users (updated)
@app.route('/user/chart-analysis', methods=['GET'])
@login_required
def user_chart_analysis():
    # Get all OTC pairs for the form
    pairs = OTCPair.query.all()
    
    # Get user's previous analyses
    analysis_history = ChartAnalysis.query.filter_by(user_id=current_user.id).order_by(ChartAnalysis.created_at.desc()).all()
    
    # Create chart_images directory if it doesn't exist
    os.makedirs(os.path.join('static', 'chart_images'), exist_ok=True)
    
    return render_template(
        'chart_analysis.html',
        user=current_user,
        pairs=pairs,
        analysis_history=analysis_history,
        analysis_result=None
    )

# API route for analyzing chart
@app.route('/user/analyze-chart', methods=['POST'])
@login_required
def user_analyze_chart():
    if 'chart_image' not in request.files:
        flash('لم يتم تحديد صورة', 'danger')
        return redirect(url_for('user_chart_analysis'))
        
    file = request.files['chart_image']
    if file.filename == '':
        flash('لم يتم تحديد صورة', 'danger')
        return redirect(url_for('user_chart_analysis'))
    
    pair_id = request.form.get('pair_id')
    if not pair_id:
        flash('يرجى اختيار زوج OTC', 'danger')
        return redirect(url_for('user_chart_analysis'))
    
    pair = OTCPair.query.get(pair_id)
    if not pair:
        flash('زوج OTC غير موجود', 'danger')
        return redirect(url_for('user_chart_analysis'))
    
    timeframe = request.form.get('timeframe', 1, type=int)
    
    try:
        # Save the image
        image_data = file.read()
        
        # Log information about the uploaded image
        app.logger.info(f"Uploaded image size: {len(image_data)} bytes, pair: {pair.symbol}, timeframe: {timeframe}")
        
        # Generate secure filename and paths
        filename = secure_filename(f"{current_user.id}_{pair.symbol}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.jpg")
        image_path = os.path.join('chart_images', filename)
        full_image_path = os.path.join('static', image_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_image_path), exist_ok=True)
        app.logger.info(f"Directory path: {os.path.dirname(full_image_path)}")
        
        # Save the file
        try:
            with open(full_image_path, 'wb') as f:
                f.write(image_data)
            app.logger.info(f"Image saved successfully at: {full_image_path}")
        except Exception as file_error:
            app.logger.error(f"Error saving file: {str(file_error)}")
            flash(f'خطأ في حفظ الصورة: {str(file_error)}', 'danger')
            return redirect(url_for('user_chart_analysis'))
        
        # Analyze the chart using chart_analyzer.py with proper error handling
        try:
            app.logger.info("Starting chart analysis...")
            analysis = analyze_chart_image(image_data, selected_pair=pair.symbol, timeframe=timeframe)
            app.logger.info(f"Analysis result: {analysis}")
        except Exception as analysis_error:
            app.logger.error(f"Exception during chart analysis: {str(analysis_error)}")
            flash(f'خطأ في تحليل الصورة: {str(analysis_error)}', 'danger')
            return redirect(url_for('user_chart_analysis'))
        
        if 'error' in analysis:
            app.logger.error(f"Analysis error: {analysis['error']}: {analysis.get('details', '')}")
            flash(f'خطأ في تحليل الصورة: {analysis["error"]}', 'danger')
            return redirect(url_for('user_chart_analysis'))
        
        # Extract success probability from the analysis
        success_probability = 0
        if 'probability' in analysis:
            # Extract numeric part from string like "85%"
            prob_str = analysis['probability']
            if prob_str.endswith('%'):
                prob_str = prob_str[:-1]  # Remove '%' sign
            try:
                success_probability = int(prob_str)
            except (ValueError, TypeError):
                success_probability = 85  # Default if parsing fails
        
        # Create a new ChartAnalysis record
        new_analysis = ChartAnalysis(
            user_id=current_user.id,
            pair_id=pair.id,
            direction=analysis.get('direction', 'BUY'),
            entry_time=analysis.get('entry_time', ''),
            duration=analysis.get('duration', f"{timeframe} دقيقة"),
            success_probability=success_probability,
            timeframe=timeframe,
            image_path=image_path,
            analysis_notes=analysis.get('analysis_notes', '')
        )
        
        db.session.add(new_analysis)
        db.session.commit()
        
        # Get all OTC pairs for the form
        pairs = OTCPair.query.all()
        
        # Get user's previous analyses
        analysis_history = ChartAnalysis.query.filter_by(user_id=current_user.id).order_by(ChartAnalysis.created_at.desc()).all()
        
        return render_template(
            'chart_analysis.html',
            user=current_user,
            pairs=pairs,
            analysis_history=analysis_history,
            analysis_result=new_analysis
        )
    except Exception as e:
        app.logger.error(f"Error processing chart image: {str(e)}")
        flash(f'فشل في معالجة الصورة: {str(e)}', 'danger')
        return redirect(url_for('user_chart_analysis'))

# API route to get chart analysis details
@app.route('/user/chart-analysis/details/<int:analysis_id>', methods=['GET'])
@login_required
def user_get_chart_analysis_details(analysis_id):
    analysis = ChartAnalysis.query.filter_by(id=analysis_id, user_id=current_user.id).first()
    
    if not analysis:
        return jsonify({'success': False, 'message': 'تحليل غير موجود'}), 404
    
    return jsonify({
        'success': True,
        'analysis': {
            'id': analysis.id,
            'pair_symbol': analysis.pair.symbol,
            'direction': analysis.direction,
            'entry_time': analysis.entry_time,
            'duration': analysis.duration,
            'success_probability': analysis.success_probability,
            'timeframe': analysis.timeframe,
            'image_url': url_for('static', filename=analysis.image_path),
            'analysis_notes': analysis.analysis_notes,
            'result': analysis.result,
            'created_at': analysis.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })

# API route for generating signals
@app.route('/api/signals/generate', methods=['POST'])
@admin_required
def generate_signal_api():
    # Get request data
    data = request.json
    pair_id = data.get('pair_id')
    is_doubling = data.get('is_doubling', False)
    
    # Generate the signal
    signal = generate_signal(bot, pair_id, is_doubling)
    
    if signal:
        return jsonify({
            "status": "success", 
            "message": "Signal generated successfully",
            "signal": {
                "id": signal.id,
                "pair": signal.pair.symbol,
                "direction": signal.direction,
                "entry_time": signal.entry_time,
                "duration": signal.duration,
                "expiration_time": signal.expiration_time.strftime('%Y-%m-%d %H:%M:%S'),
                "success_probability": signal.success_probability,
                "doubling_strategy": signal.doubling_strategy
            }
        })
    else:
        return jsonify({"status": "error", "message": "Failed to generate signal"}), 500

# API route for generating enhanced signals using the new system
@app.route('/api/signals/enhanced', methods=['POST'])
@admin_required
def generate_enhanced_signal_api():
    """نقطة وصول API لتوليد إشارات معززة باستخدام النظام الجديد"""
    
    try:
        # التحقق من إمكانية استخدام النظام المعزز
        try:
            from enhanced_signal_system import generate_enhanced_signal, get_system_statistics
            ENHANCED_SYSTEMS_AVAILABLE = True
            logger.info("✅ تم استيراد أنظمة الإشارات المتقدمة للواجهة الجديدة")
        except ImportError as e:
            logger.warning(f"⚠️ لم يتم العثور على أنظمة الإشارات المتقدمة: {e}")
            return jsonify({
                'success': False,
                'error': 'النظام المعزز غير متاح حاليًا',
                'details': str(e)
            }), 500
            
        # الحصول على بيانات الطلب
        data = request.json or {}
        pair_symbol = data.get('pair_symbol')
        force_generation = data.get('force_generation', False)
        
        # توليد الإشارة المعززة
        with app.app_context():
            logger.info(f"Generating enhanced signal for pair: {pair_symbol}")
            signal_data = generate_enhanced_signal(pair_symbol, force_generation)
            
            if not signal_data:
                return jsonify({
                    'success': False,
                    'message': 'لم يتم العثور على إشارة مناسبة وفقًا للمعايير المعززة. حاول لاحقًا.'
                }), 200
                
            # إرجاع بيانات الإشارة المعززة
            return jsonify({
                'success': True,
                'signal': signal_data,
                'message': 'تم توليد إشارة معززة بنجاح'
            })
            
    except Exception as e:
        logger.error(f"Error generating enhanced signal: {e}")
        logger.exception("Detailed exception:")
        return jsonify({
            'success': False,
            'error': 'حدث خطأ أثناء توليد الإشارة المعززة',
            'details': str(e)
        }), 500

# صفحة اختبار رسائل الترحيب
@app.route('/bot/welcome_test', methods=['GET'])
def welcome_test_page():
    """صفحة اختبار إرسال رسائل الترحيب"""
    return render_template('welcome_test.html')

# مسار خاص لإرسال رسالة الترحيب
@app.route('/bot/send_welcome', methods=['GET'])
def send_welcome_message():
    """
    مسار خاص لإرسال رسالة الترحيب
    يمكن استخدامه عبر الرابط مباشرة: /bot/send_welcome?user_id=YOUR_TELEGRAM_ID&lang=ar
    """
    user_id = request.args.get('user_id')
    first_name = request.args.get('name', 'المستخدم')
    lang = request.args.get('lang', 'ar')
    
    if not user_id:
        return jsonify({"status": "error", "message": "يجب توفير معرف المستخدم"}), 400
    
    try:
        # استدعاء دالة إرسال رسالة الترحيب من جميع البوتات
        from bot.welcome_sender import send_direct_welcome, send_welcome_from_all_bots
        
        logger.info(f"محاولة إرسال رسالة ترحيب للمستخدم {user_id} باللغة {lang} من جميع البوتات")
        
        # محاولة إرسال رسالة من جميع البوتات المسجلة
        all_bots_result = send_welcome_from_all_bots(user_id, first_name, lang)
        
        # تحقق من نجاح أي من البوتات
        success = False
        for bot_key, bot_result in all_bots_result.items():
            if bot_result.get('ok', False):
                success = True
                logger.info(f"نجح البوت {bot_key} في إرسال الرسالة")
        
        if success:
            logger.info(f"تم إرسال رسالة الترحيب بنجاح للمستخدم {user_id} من واحد أو أكثر من البوتات")
            result = {"ok": True, "message": "تم إرسال الرسالة بنجاح من واحد أو أكثر من البوتات"}
        else:
            # محاولة أخيرة باستخدام الطريقة القديمة
            logger.info("محاولة إرسال رسالة ترحيب مباشرة باستخدام طريقة بديلة")
            result = send_direct_welcome(user_id, first_name, lang)
        
        if result.get('ok', False):
            logger.info(f"تم إرسال رسالة الترحيب بنجاح للمستخدم {user_id}")
            return jsonify({
                "status": "success", 
                "message": "تم إرسال رسالة الترحيب بنجاح",
                "details": result
            })
        else:
            logger.error(f"فشل إرسال رسالة الترحيب المباشرة: {result}")
            # حاول الطريقة القديمة عبر مكتبة python-telegram-bot كخطة بديلة
            logger.info("جاري تجربة إرسال الرسالة عبر python-telegram-bot كخطة بديلة...")
            
            from bot.telegram_bot import telegram_bot
            
            if not telegram_bot:
                # إعادة تهيئة البوت إذا لم يكن متوفرًا
                from bot.telegram_bot import setup_bot
                setup_bot(app)
                from bot.telegram_bot import telegram_bot
            
            # إرسال الرسالة عبر مكتبة python-telegram-bot
            import asyncio
            
            async def send_message():
                # استخدام رسالة الترحيب من العميل المباشر (من welcome_sender)
                from bot.welcome_sender import WelcomeSender
                sender = WelcomeSender()
                
                if lang.lower() in ["ar", "arabic"]:
                    message_text = sender._get_arabic_welcome_message(first_name)
                else:
                    message_text = sender._get_english_welcome_message(first_name)
                
                await telegram_bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode='Markdown'
                )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_message())
            
            return jsonify({"status": "success", "message": "تم إرسال رسالة الترحيب بنجاح (الطريقة البديلة)"})
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة الترحيب: {e}")
        logger.exception("تفاصيل الخطأ:")
        return jsonify({"status": "error", "message": f"حدث خطأ: {str(e)}"}), 500

# واجهة API الجديدة للإشارات والمراقبة لنظام التعافي التلقائي
@app.route('/ping', methods=['GET'])
def health_check():
    """نقطة نهاية لفحص صحة الخدمة"""
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

@app.route('/signal_monitoring', methods=['GET'])
def signal_monitoring():
    """الحصول على حالة الإشارات للمراقبة"""
    try:
        # الحصول على آخر الإشارات من قاعدة البيانات
        last_signal = Signal.query.order_by(Signal.created_at.desc()).first()
        
        # حساب الوقت منذ آخر إشارة
        time_since_last_signal = 0
        if last_signal:
            time_since_last_signal = (datetime.utcnow() - last_signal.created_at).total_seconds()
        
        # حساب إحصائيات الإشارات الأخيرة
        last_24h_signals = Signal.query.filter(
            Signal.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        recent_signals = Signal.query.filter(
            Signal.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).order_by(Signal.created_at.desc()).limit(10).all()
        
        recent_signal_details = []
        for signal in recent_signals:
            pair = OTCPair.query.get(signal.pair_id) if signal.pair_id else None
            pair_symbol = pair.symbol if pair else "Unknown"
            recent_signal_details.append({
                "id": signal.id,
                "pair": pair_symbol,
                "direction": signal.direction,
                "entry_time": signal.entry_time,
                "created_at": signal.created_at.isoformat()
            })
        
        return jsonify({
            "status": "ok",
            "last_signal_time": last_signal.created_at.isoformat() if last_signal else None,
            "seconds_since_last_signal": time_since_last_signal,
            "signals_last_24h": last_24h_signals,
            "recent_signals": recent_signal_details,
            "server_time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting signal status: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "server_time": datetime.utcnow().isoformat()
        }), 500

@app.route('/api/signals/force', methods=['GET'])
def force_signal_generation():
    """إجبار إنشاء إشارة جديدة لضمان استمرارية الإرسال"""
    try:
        logger.info("⚠️ طلب إجباري لإنشاء إشارة جديدة من نظام التعافي التلقائي")
        
        # استخدام نظام الإشارات المعزز لإنشاء إشارة جديدة مع إجبار الإنشاء
        from enhanced_signal_system import generate_enhanced_signal
        signal_data = generate_enhanced_signal(force_generation=True)
        
        if not signal_data or "error" in signal_data:
            logger.error(f"⚠️ فشل في إنشاء إشارة إجبارية: {signal_data.get('error', 'unknown error') if signal_data else 'No data'}")
            # محاولة إنشاء إشارة بالحد الأدنى من البيانات إذا فشلت الطريقة المعززة
            from bot.signal_generator import generate_minimal_emergency_signal
            emergency_signal = generate_minimal_emergency_signal()
            
            if emergency_signal and "error" not in emergency_signal:
                logger.info("✅ تم إنشاء إشارة طوارئ بنجاح")
                return jsonify({"status": "success", "message": "تم إنشاء إشارة طوارئ بنجاح", "data": emergency_signal})
            else:
                logger.error(f"⚠️ فشل في إنشاء إشارة طوارئ: {emergency_signal.get('error', 'unknown error') if emergency_signal else 'No data'}")
                return jsonify({"status": "error", "message": "فشل في إنشاء أي نوع من الإشارات"}), 500
        
        logger.info("✅ تم إنشاء إشارة إجبارية بنجاح")
        return jsonify({"status": "success", "message": "تم إنشاء إشارة إجبارية بنجاح", "data": signal_data})
        
    except Exception as e:
        logger.error(f"⚠️ خطأ أثناء إنشاء إشارة إجبارية: {str(e)}")
        return jsonify({"status": "error", "message": f"حدث خطأ: {str(e)}"}), 500

# Exempt API routes from CSRF protection
csrf.exempt("/api/users")
csrf.exempt("/api/users/<int:user_id>")
csrf.exempt("/api/admins")
csrf.exempt("/api/admins/<int:admin_id>")
csrf.exempt("/api/channels")
csrf.exempt("/api/channels/<int:channel_id>")
csrf.exempt("/api/otc_pairs")
csrf.exempt("/api/otc_pairs/<int:pair_id>")
csrf.exempt("/webhook")  # Critical: Make sure webhook route is exempt from CSRF protection for Telegram
csrf.exempt("/bot/send_welcome")  # Exempt welcome message route
csrf.exempt("/api/signals/generate")
csrf.exempt("/api/signals/enhanced")
csrf.exempt("/api/signals/force")  # إعفاء نقطة نهاية الإشارات الإجبارية
csrf.exempt("/api/bots")
csrf.exempt("/ping")  # إعفاء نقطة فحص صحة النظام
csrf.exempt("/signal_monitoring")  # إعفاء نقطة حالة الإشارات

# Create all tables
with app.app_context():
    db.create_all()
    
    # Create default admin if none exists
    if Admin.query.count() == 0:
        default_admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            telegram_id='',
            is_moderator=False
        )
        db.session.add(default_admin)
        
        # Add 20 default OTC pairs
        default_pairs = [
            "EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC", "USDCHF-OTC", 
            "USDJPY-OTC", "GBPUSD-OTC", "AUDCAD-OTC", "NZDUSD-OTC", 
            "AUDUSD-OTC", "USDCAD-OTC", "AUDJPY-OTC", "GBPJPY-OTC", 
            "XAUUSD-OTC", "XAGUSD-OTC", "GBPCAD-OTC", "EURCHF-OTC", 
            "NZDJPY-OTC", "CADCHF-OTC", "EURCAD-OTC", "CHFJPY-OTC"
        ]
        for pair in default_pairs:
            otc_pair = OTCPair(symbol=pair)
            db.session.add(otc_pair)
        
        # Add official channel
        official_channel = ApprovedChannel(
            channel_id='@Trading3litepro',
            channel_name='Trading3litepro'
        )
        db.session.add(official_channel)
        
        db.session.commit()

# Importar el blueprint API
try:
    from app_endpoints import api_blueprint
    # Registrar el blueprint para los endpoints API
    app.register_blueprint(api_blueprint, url_prefix='/api')
    logger.info("✅ Blueprint de API registrado correctamente")
except ImportError as e:
    logger.error(f"❌ Error al importar el blueprint de API: {e}")

# Añadir ruta directa para la política de privacidad
@app.route('/privacy-policy')
def privacy_policy():
    """
    عرض صفحة سياسة الخصوصية
    """
    # Determinar si hay un usuario autenticado
    user = None
    try:
        from flask_login import current_user
        user = current_user
    except ImportError:
        pass
    
    return render_template('privacy_policy.html', user=user)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
