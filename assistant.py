"""
المساعد الذكي المحسّن - سَمّ
يعرف المستخدم ويتعامل معه بشكل شخصي
"""

from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS, OPENAI_TIMEOUT
from data import get_user_by_phone, get_expiring_documents, renew_document, create_reminder
from prompts import build_system_prompt, get_whats_new_message, RENEWAL_CONFIRMATION, RENEWAL_SUCCESS, INSUFFICIENT_FUNDS, REMINDER_SET

# تهيئة OpenAI
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# 🧠 المساعد الذكي
# ==========================
class SmartAssistant:
    """مساعد ذكي مع سياق وذاكرة"""
    
    def __init__(self, phone_number):
        """
        تهيئة المساعد لمستخدم معين
        
        Args:
            phone_number: رقم جوال المستخدم
        """
        self.user = get_user_by_phone(phone_number)
        self.phone_number = phone_number
        self.expiring_docs = None
        self.current_renewal = None  # المستند قيد التجديد
        
        if self.user:
            self.expiring_docs = get_expiring_documents(self.user)
    
    def get_greeting(self):
        """الحصول على رسالة ترحيب مخصصة"""
        from prompts import get_greeting
        
        if not self.user:
            return "السلام عليكم، أنا سَمّ. ممكن رقم جوالك للتعرف عليك؟"
        
        return get_greeting(self.user)
    
    def handle_whats_new(self):
        """معالجة سؤال 'وش عندي من جديد'"""
        if not self.user:
            return "أحتاج رقم جوالك أولاً للتعرف عليك."
        
        return get_whats_new_message(self.user, self.expiring_docs)
    
    def handle_renewal_request(self, user_text):
        """
        معالجة طلب التجديد
        
        Args:
            user_text: نص المستخدم
        
        Returns:
            الرد المناسب
        """
        user_lower = user_text.lower()
        
        # إذا لم يحدد مستند بعد
        if not self.current_renewal:
            # البحث عن أول مستند يحتاج تجديد
            if self.expiring_docs:
                self.current_renewal = self.expiring_docs[0]
                
                wallet_balance = self.user.get("family_wallet", {}).get("balance", 0)
                
                return RENEWAL_CONFIRMATION.format(
                    document_type=self.current_renewal['name_ar'],
                    fee=self.current_renewal['renewal_fee'],
                    wallet_balance=wallet_balance
                )
            else:
                return "كل مستنداتك سارية، ما فيه شي يحتاج تجديد الحين."
        
        # المستخدم قرر طريقة الدفع
        use_wallet = any(word in user_lower for word in ["محفظة", "محفظتي", "العائلية", "نعم", "أيوه", "تمام"])
        
        # محاكاة التجديد
        result = renew_document(
            self.user,
            self.current_renewal['type'],
            self.current_renewal['number'],
            use_wallet=use_wallet
        )
        
        if result["success"]:
            wallet_message = ""
            if use_wallet:
                wallet_message = f"رصيدك الحالي: {result['wallet_balance']} ريال."
            
            response = RENEWAL_SUCCESS.format(
                document_type=result['document_type'],
                document_number=result['document_number'],
                new_expiry=result['new_expiry'],
                fee=result['fee'],
                reference_number=result['reference_number'],
                wallet_message=wallet_message
            )
            
            # إعادة تعيين
            self.current_renewal = None
            self.expiring_docs = get_expiring_documents(self.user)
            
            return response
        else:
            # فشل التجديد (غالباً رصيد غير كافي)
            if "غير كافي" in result["message"]:
                wallet_balance = self.user.get("family_wallet", {}).get("balance", 0)
                fee = self.current_renewal['renewal_fee']
                
                return INSUFFICIENT_FUNDS.format(
                    current_balance=wallet_balance,
                    required_amount=fee,
                    shortage=fee - wallet_balance
                )
            else:
                return result["message"]
    
    def handle_reminder_request(self):
        """معالجة طلب تذكير"""
        if not self.expiring_docs:
            return "ما عندك مستندات تحتاج تذكير الحين."
        
        doc = self.expiring_docs[0]
        result = create_reminder(self.user, doc, days_before=5)
        
        if result["success"]:
            return REMINDER_SET.format(
                days_before=5,
                document_type=doc['name_ar']
            )
        else:
            return "ما قدرت أضبط التذكير، جرب مرة ثانية."
    
    def handle_wallet_inquiry(self):
        """معالجة سؤال عن المحفظة"""
        if not self.user:
            return "أحتاج رقم جوالك أولاً."
        
        wallet_balance = self.user.get("family_wallet", {}).get("balance", 0)
        return f"رصيد محفظتك العائلية: {wallet_balance} ريال."

# ==========================
# 💬 توليد الردود
# ==========================
def generate_response(user_text: str, phone_number: str = None, conversation_history: list = None) -> str:
    """
    توليد رد ذكي من المساعد
    
    Args:
        user_text: نص المستخدم
        phone_number: رقم الجوال
        conversation_history: تاريخ المحادثة
    
    Returns:
        رد المساعد
    """
    
    # إذا OpenAI غير متوفر
    if not openai_client:
        return generate_fallback_response(user_text, phone_number)
    
    # الحصول على بيانات المستخدم
    user = get_user_by_phone(phone_number) if phone_number else None
    
    if not user:
        return "ممكن رقم جوالك للتعرف عليك وأقدر أخدمك بشكل أفضل؟"
    
    # الحصول على المستندات المنتهية
    expiring_docs = get_expiring_documents(user)
    
    # بناء البرومت
    system_prompt = build_system_prompt(user, expiring_docs)
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if conversation_history:
        messages.extend(conversation_history)
    
    messages.append({"role": "user", "content": user_text})
    
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS,
            timeout=OPENAI_TIMEOUT
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ خطأ في OpenAI: {e}")
        return "عذراً، صار عندي خطأ بسيط. ممكن تعيد؟"

# ==========================
# 🔄 ردود احتياطية
# ==========================
def generate_fallback_response(user_text: str, phone_number: str = None) -> str:
    """
    ردود بسيطة بدون AI
    
    Args:
        user_text: نص المستخدم
        phone_number: رقم الجوال
    
    Returns:
        رد بسيط
    """
    
    user_lower = user_text.lower()
    user = get_user_by_phone(phone_number) if phone_number else None
    
    # ترحيب
    if any(word in user_lower for word in ["السلام", "مرحبا", "هلا"]):
        if user:
            nickname = user.get("nickname", user.get("name", "").split()[0])
            return f"هلا والله {nickname}، كيف أقدر أخدمك؟"
        return "هلا والله، كيف أقدر أخدمك في أبشر؟"
    
    # وش الجديد
    if any(word in user_lower for word in ["جديد", "عندي"]):
        if user:
            expiring = get_expiring_documents(user)
            return get_whats_new_message(user, expiring)
        return "أحتاج رقم جوالك للتعرف عليك."
    
    # المحفظة
    if "محفظة" in user_lower or "رصيد" in user_lower:
        if user:
            balance = user.get("family_wallet", {}).get("balance", 0)
            return f"رصيد محفظتك العائلية: {balance} ريال."
        return "أحتاج رقم جوالك أولاً."
    
    # خدمات عامة
    return "تمام، كيف أقدر أساعدك في خدمات أبشر؟"

# ==========================
# 🗣️ تنسيق الأرقام للنطق
# ==========================
def format_numbers_for_speech(text: str) -> str:
    """تحويل الأرقام لصيغة منطوقة"""
    
    numbers_map = {
        '0': 'صفر', '1': 'واحد', '2': 'اثنين', '3': 'ثلاثة', '4': 'أربعة',
        '5': 'خمسة', '6': 'ستة', '7': 'سبعة', '8': 'ثمانية', '9': 'تسعة'
    }
    
    result = text
    for num, word in numbers_map.items():
        result = result.replace(num, f" {word} ")
    
    return result