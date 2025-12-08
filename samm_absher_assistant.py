import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv 
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
from openai import OpenAI

# تحميل متغيرات البيئة
load_dotenv('.env')

# ==========================
# 🔑 إعداد OpenAI API
# ==========================
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "❌ OPENAI_API_KEY غير موجود!\n"
        "يرجى تعيين المفتاح:\n"
        "1. Terminal: export OPENAI_API_KEY='sk-...'\n"
        "2. ملف .env: OPENAI_API_KEY=sk-..."
    )
client = OpenAI(api_key=api_key)

SAMPLE_RATE = 16000

# ==========================
# 📚 معلومات خدمات أبشر المحسّنة
# ==========================
ABSHER_SERVICES_TEXT = """
أبشر منصة إلكترونية رسمية تابعة لوزارة الداخلية السعودية تقدم أكثر من 200 خدمة للمواطنين والمقيمين:

🛂 خدمات الجوازات:
- إصدار وتجديد جواز السفر إلكترونياً
- إصدار تأشيرات الخروج والعودة (خروج نهائي، خروج وعودة)
- الاستعلام عن صلاحية الجواز
- طباعة بيانات الجواز

👥 خدمات المقيمين والعمالة:
- تجديد الإقامة للعمالة المنزلية
- نقل خدمات العمالة بين الكفلاء
- الاستعلام عن صلاحية الإقامة
- إصدار تأشيرات الخروج النهائي والعودة للمقيمين
- الإبلاغ عن هروب عامل أو تغيبه

🚗 خدمات المرور:
- تجديد رخصة القيادة
- الاستعلام عن المخالفات المرورية وسدادها
- تفويض قيادة المركبات
- إصدار رخصة قيادة دولية

🆔 خدمات الأحوال المدنية:
- إصدار وتجديد بطاقة الهوية الوطنية
- تسجيل المواليد والوفيات
- إصدار سجل الأسرة
- تحديث البيانات الشخصية

📅 خدمات أخرى:
- حجز المواعيد في فروع وزارة الداخلية
- خدمة التوصيل المنزلي للوثائق
- إصدار شهادات إلكترونية

ملاحظة: هذا مساعد تدريبي وليس بديلاً عن المنصة الرسمية.
"""

# ==========================
# 👥 بيانات تدريبية محسّنة
# ==========================
ABSHER_FAKE_USERS = [
    {
        "national_id": "1010101010",
        "name": "أحمد محمد العتيبي",
        "role": "صاحب منشأة",
        "phone": "0501234567",
        "workers": [
            {
                "iqama_number": "2456789012",
                "name": "محمد خان",
                "nationality": "باكستان",
                "profession": "عامل منزلي",
                "iqama_issue_date": "2024-05-01",
                "iqama_expiry": "2026-05-01",
                "status": "سارية",
                "border_number": "16",
                "sponsor_id": "1010101010"
            },
            {
                "iqama_number": "2456789013",
                "name": "سلمان رحمن",
                "nationality": "بنغلاديش",
                "profession": "سائق خاص",
                "iqama_issue_date": "2023-12-10",
                "iqama_expiry": "2025-12-10",
                "status": "قريبة الانتهاء",
                "border_number": "16",
                "sponsor_id": "1010101010"
            }
        ],
        "passport": {
            "number": "K123456",
            "issue_date": "2020-01-15",
            "expiry_date": "2030-01-15",
            "status": "ساري"
        }
    },
    {
        "national_id": "2020202020",
        "name": "نورة علي القحطاني",
        "role": "فرد",
        "phone": "0507654321",
        "workers": [
            {
                "iqama_number": "3456789012",
                "name": "فاطمة سعيد",
                "nationality": "الفلبين",
                "profession": "عاملة منزلية",
                "iqama_issue_date": "2023-08-20",
                "iqama_expiry": "2025-08-20",
                "status": "منتهية",
                "border_number": "16",
                "sponsor_id": "2020202020"
            }
        ],
        "passport": {
            "number": "L789012",
            "issue_date": "2021-03-20",
            "expiry_date": "2031-03-20",
            "status": "ساري"
        }
    }
]

# ==========================
# 📊 محاكاة تجديد الإقامة
# ==========================
def simulate_iqama_renewal(iqama_number: str) -> dict:
    """محاكاة عملية تجديد إقامة مع تفاصيل واقعية"""
    old_expiry = None
    worker_name = ""
    
    for user in ABSHER_FAKE_USERS:
        for worker in user["workers"]:
            if worker["iqama_number"] == iqama_number:
                old_expiry = worker["iqama_expiry"]
                worker_name = worker["name"]
                # حساب تاريخ انتهاء جديد (سنة من الآن)
                new_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                worker["iqama_expiry"] = new_expiry
                worker["status"] = "سارية"
                
                return {
                    "success": True,
                    "worker_name": worker_name,
                    "iqama_number": iqama_number,
                    "old_expiry": old_expiry,
                    "new_expiry": new_expiry,
                    "fees": "650 ريال",
                    "reference_number": f"REF{int(time.time())}",
                    "message": "تم التجديد بنجاح"
                }
    
    return {
        "success": False,
        "message": "رقم الإقامة غير موجود في قاعدة البيانات التدريبية"
    }

# ==========================
# 🧠 بناء Prompt محسّن
# ==========================
def build_absher_prompt(user_text: str, conversation_history: list = None) -> list:
    """بناء محادثة متعددة الأدوار مع سياق"""
    users_text = json.dumps(ABSHER_FAKE_USERS, ensure_ascii=False, indent=2)
    
    system_prompt = f"""أنت "شوشو" - مساعدة أبشر الصوتية الذكية، متخصصة في خدمات وزارة الداخلية السعودية.

🎯 شخصيتك:
- ودودة، محترفة، وسريعة الاستجابة
- تتحدثين بلهجة سعودية خفيفة مع فصحى مبسطة
- صبورة ومتفهمة لاحتياجات المستخدمين
- تستخدمين عبارات مثل: "تمام"، "أكيد"، "ما عندك مشكلة"، "حاضر"

📋 خدمات أبشر:
{ABSHER_SERVICES_TEXT}

💾 قاعدة البيانات التدريبية:
{users_text}

📌 تعليمات مهمة:
1. ردودك قصيرة ومباشرة (2-3 جمل كحد أقصى للاستفسارات البسيطة)
2. لا تذكري "JSON" أو مصطلحات برمجية للمستخدم
3. عند طلب تجديد إقامة لرقم موجود:
   - استخدم دالة simulate_iqama_renewal لمحاكاة التجديد
   - اذكري التفاصيل: رقم الإقامة، تاريخ الانتهاء الجديد، الرسوم، رقم المرجع
4. للاستفسارات عن بيانات موجودة، أعطِ معلومات دقيقة من البيانات
5. للأسئلة العامة عن أبشر، اشرحي بإيجاز
6. ذكّري دائماً أن هذا مساعد تدريبي وليس منصة أبشر الرسمية
7. استخدمي الإيموجي بشكل خفيف لجعل الرد أكثر ودية

🚫 ممنوع:
- الردود الطويلة والمملة
- طلب معلومات حساسة حقيقية
- ادعاء الاتصال الفعلي بأنظمة أبشر الحقيقية
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # إضافة تاريخ المحادثة
    if conversation_history:
        messages.extend(conversation_history)
    
    messages.append({"role": "user", "content": user_text})
    
    return messages

# ==========================
# 🎙️ تسجيل صوتي محسّن
# ==========================
def record_audio(filename="user.wav", duration=5, show_countdown=True):
    """تسجيل صوت مع عد تنازلي اختياري"""
    if show_countdown:
        print(f"🎙️ ابدئي الكلام خلال: ", end="", flush=True)
        for i in range(3, 0, -1):
            print(f"{i}.. ", end="", flush=True)
            time.sleep(0.7)
        print("تكلمي الحين! 🎤")
    else:
        print(f"🎙️ أتكلم الحين (لمدة {duration} ثواني)...")
    
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()
    write(filename, SAMPLE_RATE, audio)
    print("✅ تم التسجيل\n")
    return filename

# ==========================
# 📝 تحويل صوت لنص محسّن
# ==========================
def speech_to_text(audio_path: str, language="ar") -> str:
    """تحويل صوت لنص مع دعم لغات متعددة"""
    if not audio_path or not os.path.exists(audio_path):
        return ""
    
    try:
        print("📥 جاري تحويل الصوت إلى نص...")
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
                response_format="text"
            )
        print(f"📝 قلتي: {transcript}\n")
        return transcript.strip()
    except Exception as e:
        print(f"⚠️ خطأ في التحويل الصوتي: {e}")
        return ""

# ==========================
# 🤖 توليد رد محسّن
# ==========================
def generate_reply(user_text: str, conversation_history: list = None) -> str:
    """توليد رد مع سياق المحادثة"""
    print("🤖 جاري توليد الرد...")
    
    # فحص إذا كان الطلب يتعلق بتجديد إقامة
    if "تجديد" in user_text and "إقامة" in user_text:
        # البحث عن رقم إقامة في النص
        for user in ABSHER_FAKE_USERS:
            for worker in user["workers"]:
                if worker["iqama_number"] in user_text:
                    renewal_result = simulate_iqama_renewal(worker["iqama_number"])
                    if renewal_result["success"]:
                        user_text += f"\n\nملاحظة: تم محاكاة التجديد بنجاح بالتفاصيل التالية:\n{json.dumps(renewal_result, ensure_ascii=False, indent=2)}"
    
    messages = build_absher_prompt(user_text, conversation_history)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300,  # حد أقصى للإيجاز
            stream=False
        )
        
        reply = response.choices[0].message.content.strip()
        print(f"💬 الرد: {reply}\n")
        return reply
    except Exception as e:
        print(f"⚠️ خطأ في توليد الرد: {e}")
        return "عذراً، حصل خطأ تقني. ممكن تعيدين طلبك؟"

# ==========================
# 🔊 تحويل نص لصوت محسّن
# ==========================
def text_to_speech(text: str, filename="reply.mp3", voice="nova") -> str:
    """تحويل نص إلى صوت بصوت نسائي طبيعي"""
    try:
        print("🔊 جاري تحويل الرد إلى صوت...")
        
        # استخدام أصوات أكثر طبيعية
        # nova: صوت نسائي دافئ | alloy: محايد | shimmer: نسائي حماسي
        response = client.audio.speech.create(
            model="tts-1-hd",  # نموذج عالي الجودة
            voice=voice,
            input=text,
            speed=1.0
        )
        
        audio_data = response.read()
        Path(filename).write_bytes(audio_data)
        print(f"✅ تم حفظ الصوت: {filename}\n")
        return filename
    except Exception as e:
        print(f"⚠️ خطأ في تحويل النص لصوت: {e}")
        return None

# ==========================
# 🎚️ إعدادات مقاطعة محسّنة
# ==========================
BARGE_IN_THRESHOLD = 0.05      # حساسية أعلى للاستجابة الأسرع
MIN_BARGE_TIME = 0.8           # وقت أقصر قبل السماح بالمقاطعة
BARGE_IN_SILENCE = 0.5         # صمت أقصر لإنهاء المقاطعة
CHUNK_SIZE = 512               # حجم أصغر للاستجابة الأسرع

# ==========================
# 🔊 تشغيل صوت مع مقاطعة محسّنة
# ==========================
def speak_with_barge_in(text: str, voice="nova") -> str:
    """تشغيل صوت مع إمكانية المقاطعة الذكية"""
    tts_file = text_to_speech(text, voice=voice)
    if not tts_file:
        return ""
    
    print("▶️ تشغيل الرد (تقدرين تقاطعين)...")
    
    # تشغيل الصوت
    player = subprocess.Popen(
        ["afplay", tts_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    start_time = time.time()
    interrupted = False
    recorded_chunks = []
    silence_start = None
    
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE
        ) as stream:
            
            while True:
                player_alive = (player.poll() is None)
                
                # قراءة صوت المستخدم
                audio_chunk, _ = stream.read(CHUNK_SIZE)
                volume = np.abs(audio_chunk).mean()
                
                now = time.time()
                elapsed = now - start_time
                
                # إذا انتهى التشغيل ولم تحصل مقاطعة
                if not player_alive and not interrupted:
                    print("✅ انتهى التشغيل بشكل طبيعي\n")
                    return ""
                
                # انتظار الحد الأدنى قبل السماح بالمقاطعة
                if not interrupted and elapsed < MIN_BARGE_TIME:
                    continue
                
                # اكتشاف المقاطعة
                if not interrupted and volume > BARGE_IN_THRESHOLD:
                    print("\n✋ اكتشفت مقاطعة! إيقاف التشغيل...")
                    interrupted = True
                    try:
                        player.terminate()
                        player.wait(timeout=0.5)
                    except:
                        try:
                            player.kill()
                        except:
                            pass
                    
                    recorded_chunks.append(audio_chunk)
                    silence_start = None
                    continue
                
                # تسجيل صوت المستخدم بعد المقاطعة
                if interrupted:
                    if volume > BARGE_IN_THRESHOLD:
                        recorded_chunks.append(audio_chunk)
                        silence_start = None
                    else:
                        # اكتشاف الصمت لإنهاء التسجيل
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= BARGE_IN_SILENCE:
                            print("🔇 اكتشفت صمت، إنهاء التسجيل...")
                            break
    
    except KeyboardInterrupt:
        print("\n⚠️ تم إيقاف التشغيل يدوياً")
        try:
            player.terminate()
        except:
            pass
        return ""
    except Exception as e:
        print(f"⚠️ خطأ أثناء التشغيل: {e}")
        return ""
    
    # حفظ ومعالجة صوت المقاطعة
    if not interrupted or not recorded_chunks:
        return ""
    
    try:
        audio_data = np.concatenate(recorded_chunks, axis=0)
        interrupt_file = "interrupt.wav"
        write(interrupt_file, SAMPLE_RATE, (audio_data * 32767).astype("int16"))
        print(f"💾 تم حفظ المقاطعة: {interrupt_file}")
        
        # تحويل المقاطعة لنص
        new_text = speech_to_text(interrupt_file).strip()
        if new_text:
            print(f"🗣️ قاطعتي وقلتي: '{new_text}'\n")
            return new_text
        else:
            print("⚠️ لم أفهم المقاطعة، تقدرين تعيدين\n")
            return ""
    
    except Exception as e:
        print(f"⚠️ خطأ في معالجة المقاطعة: {e}")
        return ""

# ==========================
# 🔁 حلقة المحادثة المحسّنة
# ==========================
def chat_loop():
    """حلقة محادثة ذكية مع سياق"""
    print("\n" + "="*60)
    print("🎉 مرحباً بك في مساعد أبشر الصوتي الذكي")
    print("="*60)
    print("💡 نصائح:")
    print("   • تقدرين تقاطعين المساعد بالكلام")
    print("   • قولي 'توقف' أو 'شكراً' للخروج")
    print("   • جربي: 'وش خدمات أبشر؟' أو 'جددي إقامتي'")
    print("="*60 + "\n")
    
    # سياق المحادثة
    conversation_history = []
    
    # رسالة الترحيب
    greeting = "سلام عليكم! أنا شوشو، مساعدتك في أبشر. كيف أقدر أساعدك اليوم؟"
    
    print("👋 رسالة ترحيب...")
    interrupt = speak_with_barge_in(greeting, voice="nova")
    
    if interrupt:
        conversation_history.append({"role": "assistant", "content": greeting})
        user_text = interrupt
    else:
        # انتظار أول طلب
        audio_file = record_audio(duration=5, show_countdown=True)
        user_text = speech_to_text(audio_file).strip()
    
    interaction_count = 0
    max_interactions = 20  # حد أقصى لتجنب الحلقات اللانهائية
    
    while interaction_count < max_interactions:
        interaction_count += 1
        
        if not user_text:
            retry_msg = "ما سمعت شي واضح، ممكن تعيدين؟"
            print("⚠️ لم أفهم، إعادة محاولة...")
            speak_with_barge_in(retry_msg, voice="nova")
            
            audio_file = record_audio(duration=5, show_countdown=False)
            user_text = speech_to_text(audio_file).strip()
            continue
        
        print(f"👤 المستخدم: {user_text}")
        
        # فحص كلمات الإنهاء
        exit_keywords = ["توقف", "خروج", "قف", "stop", "انهاء", "إنهاء", 
                        "شكرا", "شكراً", "مع السلامة", "باي", "bye"]
        
        if any(keyword in user_text.lower() for keyword in exit_keywords):
            farewell = "العفو حبيبتي! أي وقت تحتاجين مساعدة أنا هنا. مع السلامة 🤍"
            speak_with_barge_in(farewell, voice="nova")
            print("\n👋 انتهت الجلسة بنجاح!\n")
            break
        
        # إضافة طلب المستخدم للسياق
        conversation_history.append({"role": "user", "content": user_text})
        
        # توليد الرد
        reply = generate_reply(user_text, conversation_history)
        
        # إضافة رد المساعد للسياق
        conversation_history.append({"role": "assistant", "content": reply})
        
        # الحد من طول السياق (آخر 6 رسائل فقط)
        if len(conversation_history) > 6:
            conversation_history = conversation_history[-6:]
        
        # تشغيل الرد مع إمكانية المقاطعة
        new_user_text = speak_with_barge_in(reply, voice="nova")
        
        if new_user_text:
            # متابعة مباشرة مع المقاطعة
            print("🔁 متابعة الرد على المقاطعة...")
            user_text = new_user_text
        else:
            # انتظار طلب جديد
            audio_file = record_audio(duration=5, show_countdown=False)
            user_text = speech_to_text(audio_file).strip()
    
    if interaction_count >= max_interactions:
        print("\n⏱️ وصلنا للحد الأقصى من التفاعلات. شكراً لاستخدامك المساعد!\n")

# ==========================
# 🚀 تشغيل البرنامج
# ==========================
if __name__ == "__main__":
    try:
        chat_loop()
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف البرنامج. مع السلامة!")
    except Exception as e:
        print(f"\n❌ حصل خطأ: {e}")
        print("يرجى التأكد من:")
        print("  1. تثبيت جميع المكتبات: pip install -r requirements.txt")
        print("  2. وجود OPENAI_API_KEY في ملف .env")
        print("  3. توفر ميكروفون ومكبر صوت")