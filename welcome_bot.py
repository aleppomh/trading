#!/usr/bin/env python
"""
بوت ترحيب مستقل
بوت بسيط يستخدم Long Polling لإرسال رسائل ترحيب فقط
"""

import os
import sys
import time
import logging
import asyncio
import json
from typing import Dict, Any, List
from pathlib import Path

try:
    # محاولة استيراد مكتبة python-telegram-bot
    from telegram import Bot, Update
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        CallbackContext, filters, ExtBot
    )
    TELEGRAM_IMPORT_SUCCESS = True
except ImportError:
    TELEGRAM_IMPORT_SUCCESS = False
    print("Telegram library not found, using direct API instead")

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("welcome_bot")

# ------------------ وظائف مساعدة ------------------

def load_bot_tokens() -> List[str]:
    """
    تحميل قائمة توكنات البوتات من الملفات المختلفة
    """
    tokens = []
    
    # محاولة تحميل من متغيرات البيئة
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        tokens.append(env_token)
    
    # محاولة تحميل من ملف التهيئة
    config_path = Path("config/bots.json")
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                for bot_info in data:
                    if "token" in bot_info and bot_info["token"] and bot_info["token"] not in tokens:
                        tokens.append(bot_info["token"])
        except Exception as e:
            logger.warning(f"Failed to load from config file: {e}")
    
    # محاولة تحميل من قاعدة البيانات (إذا أمكن)
    try:
        # استيراد وحدة النماذج
        sys.path.append(os.getcwd())
        from models import TradingBot
        from app import app, db
        
        with app.app_context():
            bots = TradingBot.query.all()
            for bot in bots:
                if bot.bot_token and bot.bot_token not in tokens:
                    tokens.append(bot.bot_token)
    except Exception as e:
        logger.warning(f"Failed to load from database: {e}")
    
    # إزالة القيم الفارغة أو المكررة
    return list(set([t for t in tokens if t]))

def get_welcome_message(first_name: str, language_code: str = "ar") -> str:
    """
    الحصول على نص رسالة الترحيب حسب اللغة
    """
    if language_code.lower() in ["ar", "arabic"]:
        return f"""*مرحباً {first_name}* 👋
        
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
        
*شكراً لاستخدامك خدماتنا* 🌟
"""
    else:
        return f"""*Welcome {first_name}* 👋
        
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
        
*Thank you for using our services* 🌟
"""

# ------------------ واجهة مكتبة تلجرام ------------------

async def start_command(update: Update, context: CallbackContext) -> None:
    """
    معالجة أمر البدء (/start)
    """
    user = update.effective_user
    first_name = user.first_name or "المستخدم"
    language_code = user.language_code or "ar"
    
    # الحصول على رسالة الترحيب المناسبة
    welcome_text = get_welcome_message(first_name, language_code)
    
    # إرسال رسالة الترحيب
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown"
    )
    logger.info(f"Sent welcome message to {user.id} ({first_name}) using library")

async def run_welcome_bot_with_library(token: str, use_polling: bool = True) -> None:
    """
    تشغيل بوت الترحيب باستخدام المكتبة
    
    Args:
        token: توكن البوت
        use_polling: استخدام Long Polling بدلاً من Webhook
    """
    # إنشاء تطبيق البوت
    application = Application.builder().token(token).build()
    
    # إضافة معالج أمر /start
    application.add_handler(CommandHandler("start", start_command))
    
    if use_polling:
        # تشغيل البوت باستخدام Long Polling
        await application.initialize()
        await application.start_polling(
            allowed_updates=["message"],
            drop_pending_updates=True
        )
        logger.info(f"Bot started with token {token[:8]}... in polling mode")
        
        # إبقاء البوت قيد التشغيل
        try:
            await application.updater.start_polling()
            await asyncio.sleep(60)  # استمرار لمدة دقيقة واحدة ثم الإنهاء لتجنب استهلاك الموارد
        finally:
            await application.stop()
    else:
        # سيتم التعامل مع الويب هوك منفصلاً
        pass

# ------------------ واجهة REST API المباشرة ------------------

def send_welcome_via_api(token: str, user_id: int, first_name: str, language_code: str = "ar") -> Dict[str, Any]:
    """
    إرسال رسالة ترحيب مباشرة عبر واجهة برمجة تطبيقات تلجرام
    
    Args:
        token: توكن البوت
        user_id: معرف المستخدم
        first_name: اسم المستخدم
        language_code: رمز اللغة
        
    Returns:
        dict: نتيجة الإرسال
    """
    import requests
    
    # الحصول على رسالة الترحيب
    message_text = get_welcome_message(first_name, language_code)
    
    # إعداد طلب API
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        # إرسال الطلب
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok", False):
            logger.info(f"Successfully sent welcome message to {user_id} via direct API")
        else:
            logger.error(f"Failed to send welcome message: {data.get('description', 'Unknown error')}")
            
        return data
    except Exception as e:
        error_message = f"Error during API request: {str(e)}"
        logger.error(error_message)
        return {"ok": False, "error": error_message}

def send_welcome_from_all_bots(user_id: int, first_name: str = "المستخدم", language_code: str = "ar") -> Dict[str, Any]:
    """
    إرسال رسالة ترحيب من جميع البوتات المسجلة
    
    Args:
        user_id: معرف المستخدم
        first_name: اسم المستخدم
        language_code: رمز اللغة
        
    Returns:
        dict: نتيجة الإرسال
    """
    # تحميل كافة التوكنات
    tokens = load_bot_tokens()
    
    if not tokens:
        return {"ok": False, "error": "No bot tokens found"}
    
    # محاولة إرسال من جميع البوتات
    results = {}
    success = False
    
    for i, token in enumerate(tokens):
        # إضافة تأخير بين الرسائل
        if i > 0:
            time.sleep(1)
            
        # محاولة الإرسال
        result = send_welcome_via_api(token, user_id, first_name, language_code)
        results[f"bot_{i}"] = result
        
        if result.get("ok", False):
            success = True
    
    return {
        "ok": success,
        "results": results,
        "message": "Successfully sent welcome message from at least one bot" if success else "Failed to send welcome message from any bot"
    }

# ------------------ نقطة الدخول الرئيسية ------------------

async def main() -> None:
    """
    النقطة الرئيسية لتشغيل البوت
    """
    # تحميل التوكنات
    tokens = load_bot_tokens()
    
    if not tokens:
        logger.error("No bot tokens found")
        return
    
    logger.info(f"Found {len(tokens)} bot tokens")
    
    if TELEGRAM_IMPORT_SUCCESS:
        # استخدام المكتبة إذا كانت متاحة (أفضل)
        for token in tokens:
            try:
                await run_welcome_bot_with_library(token)
            except Exception as e:
                logger.error(f"Error running bot with token {token[:8]}...: {e}")
    else:
        # استخدام واجهة API المباشرة إذا لم تكن المكتبة متاحة (احتياطي)
        logger.info("Running in direct API mode")
        
        # اختبار الإرسال إلى معرف محدد (للاختبار فقط)
        test_user_id = os.environ.get("TEST_USER_ID")
        if test_user_id:
            result = send_welcome_from_all_bots(test_user_id, "Test User", "ar")
            logger.info(f"Test send result: {result}")
        
        logger.info("Welcome bot functionality is available through direct API calls")

if __name__ == "__main__":
    """
    تشغيل البوت كـ standalone script
    """
    # الحصول على معرف المستخدم من وسيطات سطر الأوامر (إذا تم تحديده)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        user_id = int(sys.argv[1])
        name = sys.argv[2] if len(sys.argv) > 2 else "المستخدم"
        lang = sys.argv[3] if len(sys.argv) > 3 else "ar"
        
        # إرسال رسالة ترحيب
        result = send_welcome_from_all_bots(user_id, name, lang)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # تشغيل البوت
        if TELEGRAM_IMPORT_SUCCESS:
            asyncio.run(main())
        else:
            print("Please install python-telegram-bot package or provide a user_id as argument")
            print("Usage: python welcome_bot.py USER_ID [FIRST_NAME] [LANGUAGE_CODE]")