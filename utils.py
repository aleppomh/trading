"""
ملف يحتوي على دوال مشتركة للاستخدام في مختلف أجزاء التطبيق
هذه الدوال لا تعتمد على أي وحدة أخرى في المشروع
"""

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