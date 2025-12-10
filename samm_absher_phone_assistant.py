"""
مساعد أبشر الصوتي عبر الاتصال الهاتفي
نسخة محسّنة مع إصلاح Application Error
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
from openai import OpenAI

# تحميل المتغيرات
load_dotenv('.env')

# ==========================
# 🔑 الإعدادات
# ==========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
YOUR_PHONE_NUMBER = os.environ.get("YOUR_PHONE_NUMBER")

# تحقق من المفاتيح الأساسية فقط
if not OPENAI_API_KEY:
    print("⚠️ تحذير: OPENAI_API_KEY غير موجود")
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    print("⚠️ تحذير: Twilio credentials غير موجودة")

# تهيئة OpenAI فقط إذا كان المفتاح موجود
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# تهيئة Twilio فقط إذا كانت المفاتيح موجودة
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)

# تخزين المحادثات
conversations = {}

# ==========================
# 📚 بيانات أبشر
# ==========================
ABSHER_SERVICES_TEXT = """
أبشر منصة إلكترونية رسمية تابعة لوزارة الداخلية السعودية:
- خدمات الجوازات والمقيمين
- خدمات المرور ورخص القيادة
- خدمات الأحوال المدنية والهوية
- تجديد الإقامات والاستعلام عنها
"""

ABSHER_FAKE_USERS = [
    {
        "national_id": "1010101010",
        "name": "أحمد محمد العتيبي",
        "workers": [
            {
                "iqama_number": "2456789012",
                "name": "محمد خان",
                "profession": "عامل منزلي",
                "iqama_expiry": "2026-05-01",
                "status": "سارية"
            },
            {
                "iqama_number": "2456789013",
                "name": "سلمان رحمن",
                "profession": "سائق خاص",
                "iqama_expiry": "2025-12-10",
                "status": "قريبة الانتهاء"
            }
        ]
    }
]

# ==========================
# 🧠 توليد الردود
# ==========================
def build_prompt(user_text: str, history: list = None) -> list:
    """بناء الـ prompt"""
    users_text = json.dumps(ABSHER_FAKE_USERS, ensure_ascii=False, indent=2)
    
    system_prompt = f"""أنت "سَمّ" - مساعد أبشر الصوتي.

🎯 شخصيتك:
- ودودة ومحترفة جداً
- ردود قصيرة (10-20 كلمة كحد أقصى)
- لهجة سعودية خفيفة: "تمام"، "أكيد"، "حاضر"
- لا تستخدمي إيموجي (ستُقرأ بالصوت)

📋 خدمات أبشر:
{ABSHER_SERVICES_TEXT}

💾 بيانات تدريبية:
{users_text}

📌 قواعد الرد:
1. رد واحد قصير فقط (جملة أو جملتين)
2. مباشرة للموضوع
3. اذكري أن هذا نظام تدريبي عند الحاجة
4. عند الاستعلام: أعطي المعلومة فوراً
5. عند التجديد: اذكري النجاح والتاريخ الجديد

مثال رد صحيح: "تمام، الإقامة تنتهي خامس مايو ألفين وستة وعشرين، حابة تجددينها؟"
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": user_text})
    
    return messages

def generate_ai_response(user_text: str, call_sid: str) -> str:
    """توليد رد من OpenAI"""
    
    # إذا OpenAI غير متوفر، استخدم رد افتراضي
    if not openai_client:
        return "عذراً، الخدمة غير متوفرة حالياً. يرجى المحاولة لاحقاً."
    
    history = conversations.get(call_sid, [])
    messages = build_prompt(user_text, history)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=80,
            timeout=10  # إضافة timeout
        )
        
        reply = response.choices[0].message.content.strip()
        
        # حفظ التاريخ
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        
        if len(history) > 6:
            history = history[-6:]
        
        conversations[call_sid] = history
        
        return reply
        
    except Exception as e:
        print(f"❌ خطأ في OpenAI: {e}")
        return "عذراً، حصل خطأ تقني. ممكن تعيدين؟"

# ==========================
# 📞 Webhooks - مع معالجة أخطاء محسّنة
# ==========================
@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """استقبال المكالمة - يعمل مع GET و POST"""
    
    try:
        response = VoiceResponse()
        call_sid = request.values.get('CallSid', 'unknown')
        
        print(f"📞 مكالمة جديدة: {call_sid}")
        print(f"📊 Request Method: {request.method}")
        print(f"📊 Request Data: {dict(request.values)}")
        
        # تهيئة المحادثة
        conversations[call_sid] = []
        
        # رسالة الترحيب
        greeting = "السلام عليكم ورحمة الله وبركاته، معك سَمّ، مساعدك الشخصي لخدمات أبشر.    .سَمّ طال عمرك؟"
        
        # جمع الكلام
        gather = Gather(
            input='speech',
            language='ar-SA',
            timeout=3,
            speech_timeout='auto',
            action='/process-speech',
            method='POST',
            hints='أبشر، إقامة، جواز، رخصة'  # مساعدة للتعرف على الصوت
        )
        
        gather.say(greeting, language='ar-SA', voice='Polly.Zeina')
        response.append(gather)
        
        # إذا لم يتكلم
        response.say("ما سمعت شي. شكراً لاتصالك.", language='ar-SA', voice='Polly.Zeina')
        response.hangup()
        
        print(f"✅ TwiML Response: {str(response)}")
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        print(f"❌ خطأ في /voice: {e}")
        # إرجاع response بسيط في حالة الخطأ
        error_response = VoiceResponse()
        error_response.say("عذراً، حصل خطأ تقني.", language='ar-SA', voice='Polly.Zeina')
        error_response.hangup()
        return Response(str(error_response), mimetype='text/xml')

@app.route("/process-speech", methods=['POST'])
def process_speech():
    """معالجة كلام المستخدم"""
    
    try:
        response = VoiceResponse()
        call_sid = request.values.get('CallSid', 'unknown')
        user_speech = request.values.get('SpeechResult', '').strip()
        
        print(f"🗣️ المستخدم قال: '{user_speech}'")
        
        # إذا لم يُفهم الكلام
        if not user_speech:
            print("⚠️ لم يتم فهم الكلام")
            response.say("ما فهمت عليك، ممكن تعيدين بصوت أوضح؟", language='ar-SA', voice='Polly.Zeina')
            response.redirect('/voice', method='POST')
            return Response(str(response), mimetype='text/xml')
        
        # فحص كلمات الإنهاء
        exit_keywords = ["توقف", "خروج", "شكرا", "شكراً", "مع السلامة", "باي", "انتهيت", "كفاية"]
        
        if any(keyword in user_speech.lower() for keyword in exit_keywords):
            print("👋 إنهاء المكالمة")
            farewell = "العفو حبيبتي، مع السلامة."
            response.say(farewell, language='ar-SA', voice='Polly.Zeina')
            response.hangup()
            
            # حذف المحادثة
            if call_sid in conversations:
                del conversations[call_sid]
            
            return Response(str(response), mimetype='text/xml')
        
        # توليد الرد من AI
        ai_reply = generate_ai_response(user_speech, call_sid)
        print(f"🤖 الرد: {ai_reply}")
        
        # جمع كلام جديد
        gather = Gather(
            input='speech',
            language='ar-SA',
            timeout=3,
            speech_timeout='auto',
            action='/process-speech',
            method='POST',
            hints='أبشر، إقامة، جواز، رخصة، تجديد'
        )
        
        gather.say(ai_reply, language='ar-SA', voice='Polly.Zeina')
        response.append(gather)
        
        # إذا لم يرد
        response.say("مع السلامة.", language='ar-SA', voice='Polly.Zeina')
        response.hangup()
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        print(f"❌ خطأ في /process-speech: {e}")
        error_response = VoiceResponse()
        error_response.say("عذراً، حصل خطأ. شكراً لاتصالك.", language='ar-SA', voice='Polly.Zeina')
        error_response.hangup()
        return Response(str(error_response), mimetype='text/xml')

# ==========================
# 🧪 صفحة اختبار TwiML
# ==========================
@app.route("/test-twiml", methods=['GET'])
def test_twiml():
    """صفحة لاختبار TwiML بدون مكالمة"""
    
    response = VoiceResponse()
    response.say("هذا اختبار للتأكد من عمل TwiML بشكل صحيح.", language='ar-SA', voice='Polly.Zeina')
    
    return Response(str(response), mimetype='text/xml')

# ==========================
# 🎬 صفحة التحكم
# ==========================
@app.route("/", methods=['GET'])
def home():
    """صفحة التحكم الرئيسية"""
    
    html = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🤖 مساعد أبشر - لوحة التحكم</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 25px;
                padding: 50px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                text-align: center;
                font-size: 42px;
                margin-bottom: 15px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                font-size: 18px;
                margin-bottom: 40px;
            }
            .phone-display {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 30px;
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 2px;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            }
            .call-btn {
                width: 100%;
                background: #28a745;
                color: white;
                border: none;
                padding: 25px;
                font-size: 28px;
                border-radius: 15px;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 8px 20px rgba(40, 167, 69, 0.4);
                font-weight: bold;
                margin-bottom: 15px;
            }
            .call-btn:hover {
                background: #218838;
                transform: translateY(-3px);
                box-shadow: 0 12px 30px rgba(40, 167, 69, 0.6);
            }
            .call-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            .test-btn {
                width: 100%;
                background: #007bff;
                color: white;
                border: none;
                padding: 20px;
                font-size: 20px;
                border-radius: 15px;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 8px 20px rgba(0, 123, 255, 0.4);
                font-weight: bold;
            }
            .test-btn:hover {
                background: #0056b3;
                transform: translateY(-2px);
            }
            .status {
                text-align: center;
                margin-top: 20px;
                font-size: 20px;
                color: #667eea;
                font-weight: bold;
                min-height: 30px;
            }
            .info-card {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 15px;
                margin-top: 30px;
                border-right: 5px solid #667eea;
            }
            .info-card h3 {
                color: #333;
                margin-bottom: 15px;
                font-size: 22px;
            }
            .info-card ul {
                list-style: none;
                padding: 0;
            }
            .info-card li {
                padding: 10px 0;
                color: #555;
                font-size: 16px;
                border-bottom: 1px solid #e0e0e0;
            }
            .info-card li:last-child {
                border-bottom: none;
            }
            .info-card li::before {
                content: "✅ ";
                color: #28a745;
                font-weight: bold;
                margin-left: 10px;
            }
            .warning {
                background: #fff3cd;
                border: 2px solid #ffc107;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                color: #856404;
            }
            .success {
                background: #d4edda;
                border: 2px solid #28a745;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                color: #155724;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .calling {
                animation: pulse 1.5s infinite;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 مساعد أبشر الصوتي</h1>
            <p class="subtitle">نظام الاتصال التلقائي - مثالي للعروض التقديمية</p>
            
            <div class="phone-display">
                📞 """ + (YOUR_PHONE_NUMBER or "ضع رقمك في .env") + """
            </div>
            
            <button class="call-btn" id="callBtn" onclick="makeCall()">
                📞 ابدأ المكالمة الآن
            </button>
            
            <button class="test-btn" onclick="testTwiml()">
                🧪 اختبار TwiML
            </button>
            
            <div class="status" id="status"></div>
            
            <div class="success">
                <strong>✅ السيرفر يعمل بنجاح!</strong><br>
                اختبر TwiML أولاً، ثم جرب المكالمة.
            </div>
            
            <div class="info-card">
                <h3>📋 كيف يعمل النظام:</h3>
                <ul>
                    <li>اضغط زر "اختبار TwiML" للتأكد من عمل السيرفر</li>
                    <li>اضغط "ابدأ المكالمة" للاتصال على رقمك</li>
                    <li>رد على المكالمة واستمع للترحيب</li>
                    <li>تكلم بوضوح باللغة العربية</li>
                    <li>المساعد الذكي سيرد عليك فوراً</li>
                    <li>قل "شكراً" أو "مع السلامة" للإنهاء</li>
                </ul>
            </div>
            
            <div class="info-card">
                <h3>🎯 جرب هذه الأمثلة:</h3>
                <ul>
                    <li>"وش خدمات أبشر؟"</li>
                    <li>"ابغى استعلم عن إقامة رقم ٢٤٥٦٧٨٩٠١٢"</li>
                    <li>"كيف اجدد رخصة القيادة؟"</li>
                    <li>"متى تنتهي الإقامة؟"</li>
                </ul>
            </div>
            
            <div class="warning">
                <strong>⚠️ ملاحظات مهمة:</strong><br>
                • تأكد من تشغيل ngrok وتحديث الـ URL في Twilio<br>
                • تأكد من تحقق رقمك في Twilio (Verified Caller IDs)<br>
                • هذا نظام تدريبي للعروض التقديمية فقط
            </div>
        </div>

        <script>
            function testTwiml() {
                const status = document.getElementById('status');
                status.textContent = '🧪 جاري اختبار TwiML...';
                status.style.color = '#007bff';
                
                window.open('/test-twiml', '_blank');
                
                setTimeout(() => {
                    status.textContent = '✅ إذا ظهر لك XML، معناها السيرفر يعمل!';
                    status.style.color = '#28a745';
                }, 1000);
            }
            
            async function makeCall() {
                const btn = document.getElementById('callBtn');
                const status = document.getElementById('status');
                
                btn.disabled = true;
                btn.classList.add('calling');
                status.textContent = '📡 جاري إجراء المكالمة...';
                status.style.color = '#667eea';
                
                try {
                    const response = await fetch('/trigger-call', {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        status.textContent = '✅ تم! جاري الاتصال على رقمك...';
                        status.style.color = '#28a745';
                        
                        setTimeout(() => {
                            status.textContent = '📞 رد على المكالمة واستمتع بالتجربة!';
                        }, 2000);
                        
                        setTimeout(() => {
                            btn.disabled = false;
                            btn.classList.remove('calling');
                        }, 5000);
                    } else {
                        status.textContent = '❌ خطأ: ' + data.error;
                        status.style.color = '#dc3545';
                        btn.disabled = false;
                        btn.classList.remove('calling');
                    }
                } catch (error) {
                    status.textContent = '❌ خطأ في الاتصال: ' + error.message;
                    status.style.color = '#dc3545';
                    btn.disabled = false;
                    btn.classList.remove('calling');
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html

@app.route("/trigger-call", methods=['POST'])
def trigger_call():
    """إجراء مكالمة تلقائية"""
    
    try:
        if not twilio_client:
            return {
                'success': False,
                'error': 'Twilio client غير متوفر - تحقق من المفاتيح'
            }
        
        if not YOUR_PHONE_NUMBER:
            return {
                'success': False,
                'error': 'YOUR_PHONE_NUMBER غير مُعرّف في .env'
            }
        
        if not TWILIO_PHONE_NUMBER:
            return {
                'success': False,
                'error': 'TWILIO_PHONE_NUMBER غير مُعرّف في .env'
            }
        
        # الحصول على الـ URL الصحيح (ngrok أو production)
        base_url = os.environ.get('BASE_URL', request.url_root)
        
        # إذا كان localhost، نبلّغ المستخدم
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            return {
                'success': False,
                'error': 'يجب تعيين BASE_URL في .env (ngrok URL) - Twilio لا يمكنه الوصول لـ localhost'
            }
        
        # إجراء المكالمة
        call = twilio_client.calls.create(
            to=YOUR_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=base_url.rstrip('/') + '/voice',
            method='POST',
            status_callback=base_url.rstrip('/') + '/call-status',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        
        print(f"✅ تم إجراء المكالمة: {call.sid}")
        
        return {
            'success': True,
            'call_sid': call.sid,
            'to': YOUR_PHONE_NUMBER,
            'from': TWILIO_PHONE_NUMBER
        }
        
    except Exception as e:
        print(f"❌ خطأ في trigger_call: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route("/call-status", methods=['POST'])
def call_status():
    """تتبع حالة المكالمة"""
    
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    
    print(f"📊 Call Status: {call_sid} - {call_status}")
    
    return Response('OK', mimetype='text/plain')

# ==========================
# 📊 صفحة الحالة
# ==========================
@app.route("/status", methods=['GET'])
def status():
    """معلومات حالة النظام"""
    
    return {
        'status': 'active',
        'active_conversations': len(conversations),
        'twilio_number': TWILIO_PHONE_NUMBER or 'not configured',
        'your_number': YOUR_PHONE_NUMBER or 'not configured',
        'openai_configured': openai_client is not None,
        'twilio_configured': twilio_client is not None,
        'timestamp': datetime.now().isoformat()
    }

# ==========================
# 🚀 تشغيل السيرفر
# ==========================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎉 مساعد أبشر - نظام الاتصال التلقائي")
    print("="*70)
    print(f"📞 Twilio Number: {TWILIO_PHONE_NUMBER or '❌ غير مُعرّف'}")
    print(f"📱 Your Number: {YOUR_PHONE_NUMBER or '❌ غير مُعرّف'}")
    print(f"🤖 OpenAI: {'✅ متصل' if openai_client else '❌ غير متصل'}")
    print(f"📞 Twilio: {'✅ متصل' if twilio_client else '❌ غير متصل'}")
    print(f"🌐 لوحة التحكم: http://localhost:5000")
    print(f"🧪 اختبار TwiML: http://localhost:5000/test-twiml")
    print(f"📊 الحالة: http://localhost:5000/status")
    print("="*70)
    print("\n💡 الخطوات:")
    print("   1. شغّل ngrok في terminal آخر: ngrok http 5000")
    print("   2. انسخ الـ URL وحدّثه في Twilio")
    print("   3. افتح المتصفح: http://localhost:5000")
    print("   4. اضغط 'اختبار TwiML' للتأكد")
    print("   5. اضغط 'ابدأ المكالمة' للتجربة")
    print("\n" + "="*70 + "\n")
    
    # تشغيل السيرفر
    app.run(debug=True, host='0.0.0.0', port=5000)