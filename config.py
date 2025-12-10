"""
ملف الإعدادات - جميع المتغيرات في مكان واحد
"""

import os
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv('.env')

# ==========================
# 🔑 مفاتيح API
# ==========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
YOUR_PHONE_NUMBER = os.environ.get("YOUR_PHONE_NUMBER")
BASE_URL = os.environ.get("BASE_URL")

# ==========================
# ⚙️ إعدادات النظام
# ==========================
# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True

# Twilio Voice
VOICE_LANGUAGE = 'ar-SA'
VOICE_NAME = 'Polly.Zeina'  # صوت عربي نسائي طبيعي
SPEECH_TIMEOUT = 3
SPEECH_HINTS = 'أبشر، إقامة، جواز، رخصة، تجديد، استعلام، مخالفة، هوية'

# OpenAI
OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS = 100  # ردود قصيرة لكبار السن
OPENAI_TIMEOUT = 10

# الذاكرة
MAX_CONVERSATION_HISTORY = 6  # آخر 6 رسائل فقط

# ==========================
# 📋 رسائل النظام
# ==========================
GREETING_MESSAGE = """السلام عليكم ورحمة الله وبركاته. 
معك سَمّ، مساعدك الشخصي لخدمات أبشر. 
كيف أقدر أخدمك اليوم؟"""

FAREWELL_MESSAGE = "العفو يا غالي، الله يسعدك. في أمان الله."

NO_SPEECH_MESSAGE = "ما سمعت شي واضح. لو تتكلم بصوت أعلى شوي؟"

ERROR_MESSAGE = "عذراً، صار عندي خطأ بسيط. ممكن تعيد طلبك؟"

TIMEOUT_MESSAGE = "يبدو إنك مشغول. لو تحتاج شي اتصل في أي وقت. مع السلامة."

# ==========================
# 🚫 كلمات الإنهاء
# ==========================
EXIT_KEYWORDS = [
    "شكرا", "شكراً", "شكرًا",
    "مع السلامة", "السلامة", 
    "باي", "بس", "خلاص", 
    "كفاية", "تمام", "انتهيت",
    "توقف", "قف", "stop"
]

# ==========================
# ✅ التحقق من الإعدادات
# ==========================
def validate_config():
    """التحقق من وجود جميع الإعدادات المطلوبة"""
    
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("❌ OPENAI_API_KEY غير موجود")
    
    if not TWILIO_ACCOUNT_SID:
        errors.append("❌ TWILIO_ACCOUNT_SID غير موجود")
    
    if not TWILIO_AUTH_TOKEN:
        errors.append("❌ TWILIO_AUTH_TOKEN غير موجود")
    
    if not TWILIO_PHONE_NUMBER:
        errors.append("❌ TWILIO_PHONE_NUMBER غير موجود")
    
    if errors:
        print("\n⚠️ تحذيرات الإعدادات:")
        for error in errors:
            print(f"   {error}")
        print("\nتأكد من ملف .env يحتوي على جميع المفاتيح المطلوبة.\n")
        return False
    
    print("✅ جميع الإعدادات موجودة!")
    return True