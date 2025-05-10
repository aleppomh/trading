"""
ملف الترحيل لتحديث هيكل قاعدة البيانات
"""
from app import app, db
from sqlalchemy import Column, DateTime

def add_bot_expiration_date_column():
    """إضافة عمود تاريخ انتهاء الصلاحية للبوت"""
    with app.app_context():
        try:
            # التحقق مما إذا كان العمود موجوداً بالفعل
            db.session.execute("SELECT expiration_date FROM bot_configurations LIMIT 1")
            print("عمود expiration_date موجود بالفعل")
        except Exception:
            # إضافة العمود إذا لم يكن موجوداً
            print("جاري إضافة عمود expiration_date إلى جدول bot_configurations...")
            db.session.execute("ALTER TABLE bot_configurations ADD COLUMN expiration_date TIMESTAMP")
            db.session.commit()
            print("تم إضافة عمود expiration_date بنجاح")

if __name__ == "__main__":
    add_bot_expiration_date_column()