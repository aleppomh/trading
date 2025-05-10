from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from flask_login import UserMixin

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    telegram_id = Column(String(64), unique=True)
    is_moderator = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

# نظام القفل المركزي لضمان عدم تداخل عمليات إنشاء الإشارات
class SystemLock(db.Model):
    __tablename__ = 'system_locks'
    
    id = Column(Integer, primary_key=True)
    lock_name = Column(String(64), unique=True, nullable=False)
    locked_by = Column(String(128))  # معرف العملية التي قامت بالقفل
    locked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    def __repr__(self):
        return f"<SystemLock {self.lock_name} by {self.locked_by}>"


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(64), unique=True, nullable=False)
    username = Column(String(64))
    email = Column(String(120))
    password_hash = Column(String(256))
    first_name = Column(String(64))
    last_name = Column(String(64))
    language_code = Column(String(10), default='ar')
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    pocket_option_id = Column(String(100))
    referral_code = Column(String(50))
    last_login = Column(DateTime)
    expiration_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship will be added after the ChartAnalysis class is defined
    chart_analyses = []
    
    def __repr__(self):
        return f'<User {self.username or self.telegram_id}>'
    
    @property
    def is_expired(self):
        if not self.expiration_date:
            return True
        return datetime.utcnow() > self.expiration_date
    
    @property
    def days_left(self):
        if not self.expiration_date or self.is_expired:
            return 0
        delta = self.expiration_date - datetime.utcnow()
        return max(0, delta.days)
        
    @property
    def is_authenticated(self):
        return True
        
    @property
    def is_anonymous(self):
        return False
        
    def get_id(self):
        return str(self.id)

class OTCPair(db.Model):
    __tablename__ = 'otc_pairs'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False)
    display_name = Column(String(20))  # اسم العرض (بدون -OTC)
    is_active = Column(Boolean, default=True)  # لتحديد الأزواج النشطة فقط
    base_price = Column(Float, default=1.0)  # السعر الأساسي
    volatility = Column(Float, default=0.5)  # التذبذب
    payout_rate = Column(Integer, default=80)  # نسبة الربح (%)
    signals = relationship('Signal', back_populates='pair')
    
    def __repr__(self):
        return f'<OTCPair {self.symbol}>'
        
class MarketPair(db.Model):
    """نموذج أزواج البورصة العادية (غير OTC)"""
    __tablename__ = 'market_pairs'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False)  # مثل EURUSD, GBPJPY
    display_name = Column(String(20))  # اسم العرض
    is_active = Column(Boolean, default=True)  # لتحديد الأزواج النشطة فقط
    base_price = Column(Float, default=1.0)  # السعر الأساسي
    volatility = Column(Float, default=0.5)  # التذبذب
    payout_rate = Column(Integer, default=85)  # نسبة الربح (%)
    category = Column(String(20))  # فئة الزوج (forex, commodity, index, crypto)
    
    def __repr__(self):
        return f'<MarketPair {self.symbol}>'

class Signal(db.Model):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    pair_id = Column(Integer, ForeignKey('otc_pairs.id'))
    pair = relationship('OTCPair', back_populates='signals')
    direction = Column(String(10), nullable=False)  # BUY or SELL
    entry_time = Column(String(10), nullable=False)  # Format: HH:MM
    expiration_time = Column(DateTime, nullable=False)
    duration = Column(Integer, default=1)  # Duration in minutes
    success_probability = Column(Integer, default=85)  # Percentage
    result = Column(String(10))  # WIN, LOSS, or None if not expired yet
    doubling_strategy = Column(Boolean, default=False)
    signal_message_id = Column(String(50))
    result_message_id = Column(String(50))
    chart_path = Column(String(255))  # Path to the chart image generated for this signal
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Signal {self.pair.symbol} {self.direction} at {self.entry_time}>'
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expiration_time
    
    @property
    def is_successful(self):
        if not self.result:
            return None
        return self.result == 'WIN'

class ApprovedChannel(db.Model):
    __tablename__ = 'approved_channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(100), unique=True, nullable=False)
    channel_name = Column(String(100))
    bot_id = Column(Integer, ForeignKey('bot_configurations.id'))
    expiration_date = Column(DateTime)  # تاريخ انتهاء الصلاحية للقناة
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApprovedChannel {self.channel_name}>'
        
    @property
    def is_expired(self):
        if not self.expiration_date:
            return False  # عدم وجود تاريخ انتهاء يعني أن القناة لا تنتهي
        return datetime.utcnow() > self.expiration_date
    
    @property
    def days_left(self):
        if not self.expiration_date:
            return None  # عدم وجود تاريخ انتهاء يعني غير محدد
        if self.is_expired:
            return 0
        delta = self.expiration_date - datetime.utcnow()
        return max(0, delta.days)
        
class ChartAnalysis(db.Model):
    __tablename__ = 'chart_analyses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='chart_analyses')
    pair_id = Column(Integer, ForeignKey('otc_pairs.id'), nullable=False)
    pair = relationship('OTCPair')
    
    direction = Column(String(10))  # BUY or SELL
    entry_time = Column(String(10))  # Format: HH:MM
    take_profit = Column(String(20))
    stop_loss = Column(String(20))
    duration = Column(String(20))  # Format: "X دقيقة" or "X min"
    success_probability = Column(Integer)  # Percentage
    timeframe = Column(Integer, default=1)  # In minutes
    
    image_path = Column(String(255))  # Path to stored image
    analysis_notes = Column(Text)
    
    result = Column(String(10))  # WIN, LOSS, or None if not known
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChartAnalysis {self.pair.symbol} {self.direction}>'
        
class BotConfiguration(db.Model):
    __tablename__ = 'bot_configurations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    api_token = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    channels = Column(Text)  # JSON string of channel IDs (legacy support)
    expiration_date = Column(DateTime)  # تاريخ انتهاء صلاحية البوت
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # العلاقة مع القنوات المعتمدة
    approved_channels = relationship('ApprovedChannel', backref='bot')
    
    @property
    def is_expired(self):
        if not self.expiration_date:
            return False  # عدم وجود تاريخ انتهاء يعني أن البوت لا ينتهي
        return datetime.utcnow() > self.expiration_date
    
    @property
    def days_left(self):
        if not self.expiration_date:
            return None  # عدم وجود تاريخ انتهاء يعني غير محدد
        if self.is_expired:
            return 0
        delta = self.expiration_date - datetime.utcnow()
        return max(0, delta.days)
    
    def __repr__(self):
        return f'<BotConfiguration {self.name}>'

# إضافة نموذج إشارات البورصة العادية
class MarketSignal(db.Model):
    """نموذج إشارات أزواج البورصة العادية (غير OTC)"""
    __tablename__ = 'market_signals'
    
    id = Column(Integer, primary_key=True)
    pair_id = Column(Integer, ForeignKey('market_pairs.id'))
    pair = relationship('MarketPair', backref='signals')
    direction = Column(String(10), nullable=False)  # BUY or SELL
    entry_time = Column(String(10), nullable=False)  # Format: HH:MM
    expiration_time = Column(DateTime, nullable=False)
    duration = Column(Integer, default=1)  # Duration in minutes
    success_probability = Column(Integer, default=85)  # Percentage
    result = Column(String(10))  # WIN, LOSS, or None if not expired yet
    signal_message_id = Column(String(50))
    result_message_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MarketSignal {self.pair.symbol} {self.direction} at {self.entry_time}>'
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expiration_time
    
    @property
    def is_successful(self):
        if not self.result:
            return None
        return self.result == 'WIN'

# Set up the relationship after both classes are defined
User.chart_analyses = relationship('ChartAnalysis', back_populates='user', cascade='all, delete-orphan')

class AdSettings(db.Model):
    """نموذج إعدادات الإعلانات"""
    __tablename__ = 'ad_settings'
    
    id = Column(Integer, primary_key=True)
    adsense_client_id = Column(String(100))  # معرف عميل AdSense
    adsense_slot_id_header = Column(String(100))  # معرف وحدة إعلانية في الرأس
    adsense_slot_id_sidebar = Column(String(100))  # معرف وحدة إعلانية في الشريط الجانبي
    adsense_slot_id_footer = Column(String(100))  # معرف وحدة إعلانية في التذييل
    adsense_slot_id_content = Column(String(100))  # معرف وحدة إعلانية داخل المحتوى
    
    ads_enabled = Column(Boolean, default=False)  # تفعيل/تعطيل الإعلانات بشكل عام
    show_in_homepage = Column(Boolean, default=True)  # عرض في الصفحة الرئيسية
    show_in_dashboard = Column(Boolean, default=False)  # عرض في لوحة التحكم
    show_in_results = Column(Boolean, default=True)  # عرض في صفحة النتائج
    
    max_ads_per_page = Column(Integer, default=3)  # أقصى عدد للإعلانات في الصفحة الواحدة
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdSettings {self.id}>'
