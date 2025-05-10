"""
واجهة برمجة التطبيقات (API) لنظام المراقبة والتعافي
توفر نقاط نهاية للتحقق من الحالة وإجبار إنشاء الإشارات
وصفحات إضافية مثل سياسة الخصوصية والشروط
"""

import os
import logging
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import current_user
from models import Signal, OTCPair
from app import db

logger = logging.getLogger(__name__)

# إنشاء Blueprint للواجهة
api_blueprint = Blueprint('api_endpoints', __name__)

@api_blueprint.route('/ping', methods=['GET'])
def ping():
    """
    نقطة نهاية بسيطة للتحقق من حالة الخدمة
    تستخدم من قبل خدمات مراقبة النشاط مثل UptimeRobot
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })

@api_blueprint.route('/health_check', methods=['GET'])
def health_check():
    """
    فحص صحة الخدمة بشكل أكثر تفصيلاً
    """
    try:
        # التحقق من اتصال قاعدة البيانات
        db_status = True
        db_error = None
        try:
            # تنفيذ استعلام بسيط للتحقق من الاتصال
            db.session.execute("SELECT 1").scalar()
        except Exception as e:
            db_status = False
            db_error = str(e)
        
        # الحصول على معلومات عن آخر إشارة
        last_signal = Signal.query.order_by(Signal.created_at.desc()).first()
        
        # حساب الوقت منذ آخر إشارة
        last_signal_time = None
        seconds_since_last_signal = None
        if last_signal and last_signal.created_at:
            last_signal_time = last_signal.created_at.isoformat()
            seconds_since_last_signal = (datetime.utcnow() - last_signal.created_at).total_seconds()
        
        return jsonify({
            'status': 'ok',
            'version': os.environ.get('APP_VERSION', '1.0.0'),
            'timestamp': datetime.utcnow().isoformat(),
            'database': {
                'status': 'ok' if db_status else 'error',
                'error': db_error
            },
            'last_signal': {
                'time': last_signal_time,
                'seconds_since': seconds_since_last_signal,
                'id': last_signal.id if last_signal else None
            }
        })
        
    except Exception as e:
        logger.error(f"خطأ في فحص صحة الخدمة: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_blueprint.route('/signal_status', methods=['GET'])
def signal_monitoring():
    """
    الحصول على حالة الإشارات للمراقبة
    """
    try:
        # الحصول على آخر 10 إشارات
        recent_signals = Signal.query.order_by(Signal.created_at.desc()).limit(10).all()
        
        # الحصول على حالة آخر إشارة
        last_signal = None
        if recent_signals:
            last_signal = recent_signals[0]
        
        # حساب إحصاءات الإشارات
        signal_counts = {
            'today': Signal.query.filter(
                Signal.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count(),
            'total': Signal.query.count(),
            'last_24h': Signal.query.filter(
                Signal.created_at >= datetime.utcnow() - timedelta(days=1)
            ).count()
        }
        
        # إعداد الإحصاءات مع تواريخ آخر الإشارات ومعلومات الفاصل الزمني
        result = {
            'status': 'ok',
            'signal_counts': signal_counts,
            'recent_signals': [],
            'last_signal_time': last_signal.created_at.isoformat() if last_signal else None,
            'seconds_since_last_signal': (datetime.utcnow() - last_signal.created_at).total_seconds() if last_signal else None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # إضافة تفاصيل الإشارات الأخيرة
        for signal in recent_signals:
            signal_data = {
                'id': signal.id,
                'pair_id': signal.pair_id,
                'direction': signal.direction,
                'entry_time': signal.entry_time,
                'duration': signal.duration,
                'created_at': signal.created_at.isoformat(),
                'sent_at': signal.created_at.isoformat(),  # توافق مع الاسم القديم
                'seconds_ago': (datetime.utcnow() - signal.created_at).total_seconds()
            }
            result['recent_signals'].append(signal_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على حالة الإشارات: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
        
@api_blueprint.route('/privacy-policy')
def privacy_policy():
    """
    عرض صفحة سياسة الخصوصية
    """
    # Importar current_user si es necesario
    try:
        from flask_login import current_user
        user = current_user
    except ImportError:
        user = None
    return render_template('privacy_policy.html', user=user)

@api_blueprint.route('/api/signals/force', methods=['GET'])
def force_signal_generation():
    """
    إجبار إنشاء إشارة جديدة للطوارئ
    """
    try:
        try:
            # محاولة استيراد مولد إشارات الطوارئ
            from bot.emergency_signal_generator import generate_emergency_signal_for_auto_recovery
            
            # تنفيذ إنشاء الإشارة
            result = generate_emergency_signal_for_auto_recovery()
            
            if result:
                logger.info("✅ تم إنشاء إشارة طوارئ بنجاح عبر واجهة API")
                return jsonify({
                    'status': 'success',
                    'message': 'تم إنشاء إشارة طوارئ بنجاح'
                })
            else:
                logger.error("❌ فشل في إنشاء إشارة الطوارئ عبر واجهة API")
                return jsonify({
                    'status': 'error',
                    'message': 'فشل في إنشاء إشارة الطوارئ'
                }), 500
        except ImportError as e:
            logger.error(f"❌ لم يتم العثور على مولد إشارات الطوارئ: {e}")
            
            # محاولة استيراد البدائل إذا كان مولد الطوارئ غير متاح
            try:
                # محاولة استخدام دالة إنشاء الإشارات العادية
                from app import generate_new_signal
                
                # إنشاء إشارة جديدة إجبارية
                signal = generate_new_signal()
                
                if signal:
                    logger.info("✅ تم إنشاء إشارة عادية بنجاح عبر واجهة API")
                    return jsonify({
                        'status': 'success',
                        'message': 'تم إنشاء إشارة عادية بنجاح'
                    })
                else:
                    logger.error("❌ فشل في إنشاء إشارة العادية عبر واجهة API")
                    return jsonify({
                        'status': 'error',
                        'message': 'فشل في إنشاء إشارة العادية'
                    }), 500
            except ImportError:
                return jsonify({
                    'status': 'error',
                    'message': 'لم يتم العثور على أي نظام لإنشاء الإشارات'
                }), 500
    except Exception as e:
        logger.error(f"خطأ في عملية إجبار إنشاء الإشارة: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500