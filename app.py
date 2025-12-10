"""
التطبيق الرئيسي - مساعد أبشر الصوتي "سَمّ"
متوافق مع Windows, Mac, Linux
"""

import sys
import platform
from datetime import datetime
from flask import Flask, request, Response, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

# استيراد الموديولات المحلية
from config import *
from assistant import generate_response, format_numbers_for_speech, SmartAssistant
from data import get_user_by_phone, get_expiring_documents
from prompts import get_greeting

# ==========================
# 🎨 تهيئة Flask
# ==========================
app = Flask(__name__)

# ==========================
# 💾 ذاكرة المحادثات
# ==========================
conversations = {}

def get_conversation(call_sid):
    """الحصول على تاريخ المحادثة"""
    if call_sid not in conversations:
        conversations[call_sid] = []
    return conversations[call_sid]

def update_conversation(call_sid, user_message, assistant_message):
    """تحديث تاريخ المحادثة"""
    history = get_conversation(call_sid)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    
    # الحد من طول التاريخ
    if len(history) > MAX_CONVERSATION_HISTORY:
        conversations[call_sid] = history[-MAX_CONVERSATION_HISTORY:]

def clear_conversation(call_sid):
    """حذف محادثة"""
    if call_sid in conversations:
        del conversations[call_sid]

# ==========================
# 📞 Webhook - استقبال المكالمة
# ==========================
@app.route("/voice", methods=['GET', 'POST'])
def voice_webhook():
    """
    نقطة البداية - استقبال المكالمة
    يعمل مع GET و POST
    """
    
    try:
        call_sid = request.values.get('CallSid', 'unknown')
        caller_number = request.values.get('From', 'unknown')
        
        # طباعة معلومات المكالمة
        print("=" * 70)
        print(f"📞 مكالمة جديدة")
        print(f"   Call SID: {call_sid}")
        print(f"   من: {caller_number}")
        print(f"   الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # تهيئة المحادثة
        get_conversation(call_sid)
        
        # التعرف على المستخدم
        user = get_user_by_phone(caller_number)
        
        # بناء الرد
        response = VoiceResponse()
        
        # جمع الكلام
        gather = Gather(
            input='speech',
            language=VOICE_LANGUAGE,
            timeout=SPEECH_TIMEOUT,
            speech_timeout='auto',
            action='/handle-speech',
            method='POST',
            hints=SPEECH_HINTS
        )
        
        # رسالة ترحيب مخصصة
        if user:
            greeting = get_greeting(user)
        else:
            greeting = GREETING_MESSAGE
        
        gather.say(greeting, language=VOICE_LANGUAGE, voice=VOICE_NAME)
        response.append(gather)
        
        # إذا لم يتكلم المستخدم
        response.say(TIMEOUT_MESSAGE, language=VOICE_LANGUAGE, voice=VOICE_NAME)
        response.hangup()
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        print(f"❌ خطأ في /voice: {e}")
        return create_error_response()

# ==========================
# 🗣️ Webhook - معالجة الكلام
# ==========================
@app.route("/handle-speech", methods=['POST'])
def handle_speech():
    """
    معالجة كلام المستخدم وتوليد الرد
    """
    
    try:
        call_sid = request.values.get('CallSid', 'unknown')
        user_speech = request.values.get('SpeechResult', '').strip()
        
        print(f"\n🗣️ المستخدم قال: '{user_speech}'")
        
        # إذا لم يُفهم الكلام
        if not user_speech:
            print("⚠️ لم يتم فهم الكلام")
            return create_repeat_response()
        
        # فحص كلمات الإنهاء
        if is_exit_command(user_speech):
            print("👋 إنهاء المكالمة")
            clear_conversation(call_sid)
            return create_farewell_response()
        
        # معالجة الطلبات الخاصة (تجديد، استعلام، إلخ)
        special_response = handle_special_requests(user_speech)
        
        # توليد الرد من AI
        history = get_conversation(call_sid)
        
        if special_response:
            ai_reply = special_response
        else:
            ai_reply = generate_response(user_speech, history)
        
        # تنسيق الأرقام للنطق
        ai_reply = format_numbers_for_speech(ai_reply)
        
        print(f"🤖 الرد: {ai_reply}")
        
        # حفظ في التاريخ
        update_conversation(call_sid, user_speech, ai_reply)
        
        # بناء الرد
        response = VoiceResponse()
        
        gather = Gather(
            input='speech',
            language=VOICE_LANGUAGE,
            timeout=SPEECH_TIMEOUT,
            speech_timeout='auto',
            action='/handle-speech',
            method='POST',
            hints=SPEECH_HINTS
        )
        
        gather.say(ai_reply, language=VOICE_LANGUAGE, voice=VOICE_NAME)
        response.append(gather)
        
        # إذا لم يرد المستخدم
        response.say(TIMEOUT_MESSAGE, language=VOICE_LANGUAGE, voice=VOICE_NAME)
        response.hangup()
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        print(f"❌ خطأ في /handle-speech: {e}")
        return create_error_response()

# ==========================
# 🔧 دوال مساعدة
# ==========================
def is_exit_command(text):
    """التحقق من كلمات الإنهاء"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in EXIT_KEYWORDS)

def create_error_response():
    """إنشاء رد خطأ"""
    response = VoiceResponse()
    response.say(ERROR_MESSAGE, language=VOICE_LANGUAGE, voice=VOICE_NAME)
    response.hangup()
    return Response(str(response), mimetype='text/xml')

def create_repeat_response():
    """إنشاء رد لطلب الإعادة"""
    response = VoiceResponse()
    response.say(NO_SPEECH_MESSAGE, language=VOICE_LANGUAGE, voice=VOICE_NAME)
    response.redirect('/voice', method='POST')
    return Response(str(response), mimetype='text/xml')

def create_farewell_response():
    """إنشاء رد الوداع"""
    response = VoiceResponse()
    response.say(FAREWELL_MESSAGE, language=VOICE_LANGUAGE, voice=VOICE_NAME)
    response.hangup()
    return Response(str(response), mimetype='text/xml')

# ==========================
# 🧪 صفحات الاختبار
# ==========================
@app.route("/test", methods=['GET'])
def test_page():
    """صفحة اختبار TwiML"""
    response = VoiceResponse()
    response.say("اختبار. السيرفر يعمل بنجاح!", language=VOICE_LANGUAGE, voice=VOICE_NAME)
    return Response(str(response), mimetype='text/xml')

@app.route("/status", methods=['GET'])
def status_page():
    """صفحة حالة النظام"""
    return jsonify({
        "status": "active",
        "platform": platform.system(),
        "python_version": sys.version,
        "active_conversations": len(conversations),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/")
def home_page():
    """الصفحة الرئيسية"""
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <title>🤖 مساعد أبشر الصوتي - سَمّ</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 50px 20px;
                margin: 0;
            }
            .container {
                background: white;
                color: #333;
                padding: 50px;
                border-radius: 25px;
                max-width: 800px;
                margin: 0 auto;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { color: #667eea; font-size: 48px; margin-bottom: 10px; }
            .subtitle { color: #666; font-size: 20px; margin-bottom: 40px; }
            .status {
                background: #d4edda;
                border: 2px solid #28a745;
                padding: 25px;
                border-radius: 15px;
                margin: 30px 0;
            }
            .info {
                background: #f8f9fa;
                padding: 30px;
                border-radius: 15px;
                margin: 30px 0;
                text-align: right;
                line-height: 2;
            }
            .btn {
                background: #007bff;
                color: white;
                padding: 15px 40px;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin: 10px;
                transition: all 0.3s;
            }
            .btn:hover { background: #0056b3; transform: translateY(-2px); }
            .phone { 
                font-size: 36px; 
                font-weight: bold; 
                color: #667eea;
                margin: 20px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 سَمّ</h1>
            <p class="subtitle">مساعدك الصوتي الذكي لخدمات أبشر</p>
            
            <div class="status">
                <h2>✅ النظام يعمل بنجاح!</h2>
                <p>جاهز لاستقبال المكالمات على مدار الساعة</p>
            </div>
            
            <div class="phone">
                📞 اتصل على رقم Twilio الخاص بك
            </div>
            
            <a href="/test" target="_blank" class="btn">🧪 اختبار TwiML</a>
            <a href="/status" target="_blank" class="btn">📊 حالة النظام</a>
            
            <div class="info">
                <h3>🎯 كيف تستخدم سَمّ:</h3>
                <ol style="text-align: right;">
                    <li>اتصل على رقم Twilio من جوالك</li>
                    <li>استمع لرسالة الترحيب من سَمّ</li>
                    <li>تكلم بوضوح باللغة العربية</li>
                    <li>سَمّ يفهم ويرد عليك فوراً</li>
                    <li>قل "شكراً" أو "مع السلامة" للإنهاء</li>
                </ol>
            </div>
            
            <div class="info">
                <h3>💬 أمثلة على الأسئلة:</h3>
                <ul style="text-align: right;">
                    <li>"وش خدمات أبشر؟"</li>
                    <li>"ابغى استعلم عن إقامة"</li>
                    <li>"كيف اجدد رخصة القيادة؟"</li>
                    <li>"عندي مخالفات؟"</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """

# ==========================
# 🚀 تشغيل التطبيق
# ==========================
def print_startup_info():
    """طباعة معلومات بدء التشغيل"""
    
    print("\n" + "=" * 80)
    print("🤖 مساعد أبشر الصوتي - سَمّ")
    print("=" * 80)
    print(f"💻 النظام: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"🌐 السيرفر: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"🧪 اختبار: http://localhost:{FLASK_PORT}/test")
    print(f"📊 الحالة: http://localhost:{FLASK_PORT}/status")
    print("=" * 80)
    print("\n💡 خطوات التشغيل:")
    print("   1. شغّل ngrok في terminal آخر:")
    if platform.system() == "Windows":
        print("      ngrok.exe http 5000")
    else:
        print("      ngrok http 5000")
    print("   2. انسخ ngrok URL وحدّثه في Twilio")
    print("   3. اتصل على رقم Twilio من جوالك")
    print("   4. استمتع بالمحادثة مع سَمّ!")
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    # التحقق من الإعدادات
    if not validate_config():
        print("\n⚠️ يرجى تكملة الإعدادات في ملف .env قبل التشغيل.\n")
        sys.exit(1)
    
    # طباعة معلومات البدء
    print_startup_info()
    
    # تشغيل السيرفر
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG
        )
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف السيرفر. مع السلامة!")
    except Exception as e:
        print(f"\n❌ خطأ في تشغيل السيرفر: {e}")
        sys.exit(1)