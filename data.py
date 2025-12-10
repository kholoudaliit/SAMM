"""
بيانات أبشر المحسّنة - مع معلومات شخصية وعائلية
"""

from datetime import datetime, timedelta
import random

# ==========================
# 👥 مستخدمي أبشر المحسّن
# ==========================
MOCK_USERS = {
    # رقم الجوال كمفتاح للتعرف السريع
    "+966501234567": {
        "phone": "+966501234567",
        "national_id": "1010101010",
        "name": "أحمد محمد العتيبي",
        "nickname": "أبو عبدالله",  # الكنية
        "children": [
            {"name": "عبدالله", "age": 15},
            {"name": "فاطمة", "age": 12},
            {"name": "خالد", "age": 8}
        ],
        "family_wallet": {
            "balance": 1200.00,
            "currency": "ريال"
        },
        "documents": {
            "national_id": {
                "number": "1010101010",
                "issue_date": "2015-03-20",
                "expiry_date": (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"),  # تنتهي بعد 20 يوم
                "status": "قريبة الانتهاء",
                "renewal_fee": 300
            },
            "passport": {
                "number": "K123456",
                "issue_date": "2020-01-15",
                "expiry_date": "2030-01-15",
                "status": "ساري",
                "renewal_fee": 300
            },
            "drivers_license": {
                "number": "12345678",
                "issue_date": "2018-06-10",
                "expiry_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
                "status": "ساري",
                "renewal_fee": 400
            }
        },
        "workers": [
            {
                "iqama_number": "2456789012",
                "name": "محمد خان",
                "nationality": "باكستان",
                "profession": "عامل منزلي",
                "iqama_issue_date": "2024-05-01",
                "iqama_expiry": "2026-05-01",
                "status": "سارية",
                "renewal_fee": 650
            },
            {
                "iqama_number": "2456789013",
                "name": "سلمان رحمن",
                "nationality": "بنغلاديش",
                "profession": "سائق خاص",
                "iqama_issue_date": "2023-12-10",
                "iqama_expiry": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),  # تنتهي بعد 5 أيام
                "status": "تحتاج تجديد عاجل",
                "renewal_fee": 650
            }
        ],
        "traffic_violations": [
            {
                "number": "TR12345",
                "date": "2024-11-15",
                "description": "تجاوز السرعة",
                "amount": 300,
                "status": "غير مسددة"
            }
        ],
        "notifications": []  # سيتم ملؤها ديناميكياً
    },
    
    "+966507654321": {
        "phone": "+966507654321",
        "national_id": "2020202020",
        "name": "نورة علي القحطاني",
        "nickname": "أم سارة",
        "children": [
            {"name": "سارة", "age": 10},
            {"name": "لين", "age": 7}
        ],
        "family_wallet": {
            "balance": 850.00,
            "currency": "ريال"
        },
        "documents": {
            "national_id": {
                "number": "2020202020",
                "issue_date": "2016-05-10",
                "expiry_date": "2026-05-10",
                "status": "ساري",
                "renewal_fee": 300
            },
            "passport": {
                "number": "L789012",
                "issue_date": "2021-03-20",
                "expiry_date": "2031-03-20",
                "status": "ساري",
                "renewal_fee": 300
            }
        },
        "workers": [
            {
                "iqama_number": "3456789012",
                "name": "فاطمة سعيد",
                "nationality": "الفلبين",
                "profession": "عاملة منزلية",
                "iqama_issue_date": "2023-08-20",
                "iqama_expiry": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),  # منتهية
                "status": "منتهية",
                "renewal_fee": 650
            }
        ],
        "traffic_violations": [],
        "notifications": []
    }
}

# ==========================
# 🔍 دوال البحث والتعرف
# ==========================
def get_user_by_phone(phone_number):
    """
    الحصول على بيانات المستخدم برقم الجوال
    
    Args:
        phone_number: رقم الجوال
    
    Returns:
        بيانات المستخدم أو None
    """
    # تنظيف رقم الجوال
    clean_phone = phone_number.strip()
    if not clean_phone.startswith('+'):
        clean_phone = f"+966{clean_phone.lstrip('0')}"
    
    return MOCK_USERS.get(clean_phone)

def calculate_days_until(date_str):
    """
    حساب عدد الأيام المتبقية حتى تاريخ معين
    
    Args:
        date_str: التاريخ بصيغة YYYY-MM-DD
    
    Returns:
        عدد الأيام (سالب إذا انتهى)
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now()
        delta = target_date - today
        return delta.days
    except:
        return 999

def get_expiring_documents(user):
    """
    الحصول على المستندات القريبة من الانتهاء
    
    Args:
        user: بيانات المستخدم
    
    Returns:
        قائمة المستندات المنتهية أو القريبة من الانتهاء
    """
    expiring = []
    
    # فحص المستندات الشخصية
    for doc_type, doc_data in user.get("documents", {}).items():
        days_left = calculate_days_until(doc_data["expiry_date"])
        
        if days_left < 0:
            expiring.append({
                "type": doc_type,
                "name_ar": get_document_name_ar(doc_type),
                "number": doc_data["number"],
                "expiry_date": doc_data["expiry_date"],
                "days_left": days_left,
                "status": "منتهي",
                "renewal_fee": doc_data.get("renewal_fee", 0)
            })
        elif days_left <= 30:
            expiring.append({
                "type": doc_type,
                "name_ar": get_document_name_ar(doc_type),
                "number": doc_data["number"],
                "expiry_date": doc_data["expiry_date"],
                "days_left": days_left,
                "status": "قريب الانتهاء",
                "renewal_fee": doc_data.get("renewal_fee", 0)
            })
    
    # فحص إقامات العمالة
    for worker in user.get("workers", []):
        days_left = calculate_days_until(worker["iqama_expiry"])
        
        if days_left < 0:
            expiring.append({
                "type": "iqama",
                "name_ar": f"إقامة {worker['name']}",
                "number": worker["iqama_number"],
                "expiry_date": worker["iqama_expiry"],
                "days_left": days_left,
                "status": "منتهية",
                "renewal_fee": worker.get("renewal_fee", 650)
            })
        elif days_left <= 30:
            expiring.append({
                "type": "iqama",
                "name_ar": f"إقامة {worker['name']}",
                "number": worker["iqama_number"],
                "expiry_date": worker["iqama_expiry"],
                "days_left": days_left,
                "status": "قريبة الانتهاء",
                "renewal_fee": worker.get("renewal_fee", 650)
            })
    
    # ترتيب حسب الأولوية (المنتهي أولاً، ثم الأقرب)
    expiring.sort(key=lambda x: (0 if x["days_left"] < 0 else 1, x["days_left"]))
    
    return expiring

def get_document_name_ar(doc_type):
    """تحويل نوع المستند للعربي"""
    names = {
        "national_id": "الهوية الوطنية",
        "passport": "جواز السفر",
        "drivers_license": "رخصة القيادة",
        "iqama": "الإقامة"
    }
    return names.get(doc_type, doc_type)

# ==========================
# 💼 عمليات التجديد
# ==========================
def renew_document(user, doc_type, doc_number, use_wallet=False):
    """
    تجديد مستند (محاكاة)
    
    Args:
        user: بيانات المستخدم
        doc_type: نوع المستند
        doc_number: رقم المستند
        use_wallet: استخدام المحفظة العائلية
    
    Returns:
        نتيجة التجديد
    """
    
    # تجديد هوية/جواز/رخصة
    if doc_type in ["national_id", "passport", "drivers_license"]:
        doc = user["documents"].get(doc_type)
        
        if not doc or doc["number"] != doc_number:
            return {
                "success": False,
                "message": "المستند غير موجود"
            }
        
        fee = doc.get("renewal_fee", 300)
        
        # فحص المحفظة إذا طلب الدفع منها
        if use_wallet:
            wallet_balance = user["family_wallet"]["balance"]
            if wallet_balance < fee:
                return {
                    "success": False,
                    "message": f"رصيد المحفظة غير كافي. الرصيد الحالي: {wallet_balance} ريال"
                }
            
            # خصم من المحفظة
            user["family_wallet"]["balance"] -= fee
        
        # تحديث تاريخ الانتهاء
        old_expiry = doc["expiry_date"]
        new_expiry = (datetime.now() + timedelta(days=365*10)).strftime("%Y-%m-%d")
        doc["expiry_date"] = new_expiry
        doc["status"] = "ساري"
        
        return {
            "success": True,
            "document_type": get_document_name_ar(doc_type),
            "document_number": doc_number,
            "old_expiry": old_expiry,
            "new_expiry": new_expiry,
            "fee": fee,
            "payment_method": "المحفظة العائلية" if use_wallet else "مدى",
            "wallet_balance": user["family_wallet"]["balance"] if use_wallet else None,
            "reference_number": f"REF{int(datetime.now().timestamp())}",
            "message": "تم التجديد بنجاح"
        }
    
    # تجديد إقامة
    elif doc_type == "iqama":
        for worker in user.get("workers", []):
            if worker["iqama_number"] == doc_number:
                fee = worker.get("renewal_fee", 650)
                
                if use_wallet:
                    wallet_balance = user["family_wallet"]["balance"]
                    if wallet_balance < fee:
                        return {
                            "success": False,
                            "message": f"رصيد المحفظة غير كافي. الرصيد: {wallet_balance} ريال"
                        }
                    user["family_wallet"]["balance"] -= fee
                
                old_expiry = worker["iqama_expiry"]
                new_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                worker["iqama_expiry"] = new_expiry
                worker["status"] = "سارية"
                
                return {
                    "success": True,
                    "document_type": f"إقامة {worker['name']}",
                    "document_number": doc_number,
                    "old_expiry": old_expiry,
                    "new_expiry": new_expiry,
                    "fee": fee,
                    "payment_method": "المحفظة العائلية" if use_wallet else "مدى",
                    "wallet_balance": user["family_wallet"]["balance"] if use_wallet else None,
                    "reference_number": f"REF{int(datetime.now().timestamp())}",
                    "message": "تم التجديد بنجاح"
                }
        
        return {
            "success": False,
            "message": "رقم الإقامة غير موجود"
        }
    
    return {
        "success": False,
        "message": "نوع المستند غير معروف"
    }

# ==========================
# 🔔 نظام التذكير
# ==========================
def create_reminder(user, doc_info, days_before=5):
    """
    إنشاء تذكير قبل انتهاء المستند
    
    Args:
        user: بيانات المستخدم
        doc_info: معلومات المستند
        days_before: عدد أيام التذكير المسبق
    
    Returns:
        تأكيد التذكير
    """
    
    reminder_date = (datetime.strptime(doc_info["expiry_date"], "%Y-%m-%d") - timedelta(days=days_before)).strftime("%Y-%m-%d")
    
    reminder = {
        "reminder_id": f"REM{int(datetime.now().timestamp())}",
        "document_type": doc_info["name_ar"],
        "document_number": doc_info["number"],
        "expiry_date": doc_info["expiry_date"],
        "reminder_date": reminder_date,
        "message": f"تذكير: {doc_info['name_ar']} رقم {doc_info['number']} سينتهي في {doc_info['expiry_date']}",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    user.setdefault("reminders", []).append(reminder)
    
    return {
        "success": True,
        "reminder_id": reminder["reminder_id"],
        "reminder_date": reminder_date,
        "message": f"تم ضبط تذكير قبل {days_before} أيام من الانتهاء"
    }

# ==========================
# 📋 خدمات أبشر
# ==========================
ABSHER_SERVICES = {
    "الجوازات": [
        "إصدار جواز سفر جديد",
        "تجديد جواز السفر",
        "طباعة بيانات الجواز"
    ],
    "المقيمين": [
        "تجديد الإقامة",
        "نقل خدمات العمالة",
        "إصدار تأشيرة خروج وعودة"
    ],
    "المرور": [
        "تجديد رخصة القيادة",
        "الاستعلام عن المخالفات",
        "سداد المخالفات"
    ],
    "الأحوال المدنية": [
        "تجديد بطاقة الهوية",
        "إصدار سجل الأسرة",
        "تحديث البيانات"
    ]
}

SERVICES_DESCRIPTION = """أبشر منصة إلكترونية تابعة لوزارة الداخلية السعودية.
تقدم خدمات الجوازات، المقيمين، المرور، والأحوال المدنية بشكل إلكتروني متكامل."""