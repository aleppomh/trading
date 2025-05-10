import logging
import random
from advanced_signal_filter import filter_trading_signal, evaluate_signal_quality

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_otc_filter():
    """Prueba simple para el filtro de señales OTC"""
    print("\n===== Prueba del filtro de señales OTC =====\n")
    
    # Crear señal OTC con validación de soporte/resistencia
    otc_signal = {
        "pair": "EUR/JPY-OTC",
        "direction": "BUY",
        "entry_time": "12:00",
        "duration": "1 دقيقة",
        "probability": "78%",
        "sr_validated": True,  # Indicamos que la señal ha sido validada con soporte/resistencia
        "sr_info": {
            "level_type": "support",
            "price": 1.2345,
            "strength": 80
        }
    }
    
    # Crear señal regular con validación de soporte/resistencia
    regular_signal = {
        "pair": "EUR/JPY",
        "direction": "BUY",
        "entry_time": "12:00",
        "duration": "1 دقيقة",
        "probability": "78%",
        "sr_validated": True,
        "sr_info": {
            "level_type": "support",
            "price": 1.2345,
            "strength": 75
        }
    }
    
    # Probar el filtro con ambas señales
    print("Evaluando señal OTC...")
    is_valid_otc, quality_otc, reason_otc = filter_trading_signal(otc_signal)
    print(f"Señal OTC: {is_valid_otc}, calidad: {quality_otc:.2f}, razón: {reason_otc}")
    
    print("\nEvaluando señal regular...")
    is_valid_reg, quality_reg, reason_reg = filter_trading_signal(regular_signal)
    print(f"Señal regular: {is_valid_reg}, calidad: {quality_reg:.2f}, razón: {reason_reg}")
    
    # Evaluación de diferentes niveles de probabilidad para OTC
    print("\n===== Prueba de umbral de calidad para OTC =====")
    for prob in [65, 70, 75, 80, 85]:
        test_signal = {
            "pair": "USD/NOK-OTC",
            "direction": "SELL",
            "entry_time": "14:30",
            "duration": "2 دقيقة",
            "probability": f"{prob}%",
            "sr_validated": True,  # Validada en soporte/resistencia
            "sr_info": {
                "level_type": "resistance",
                "price": 0.9876,
                "strength": 70
            }
        }
        is_valid, quality, reason = filter_trading_signal(test_signal)
        print(f"Prob {prob}%: {'✅ ACEPTADA' if is_valid else '❌ RECHAZADA'}, calidad: {quality:.2f}")
    
    # Prueba comparativa entre pares OTC y regulares
    print("\n===== Comparativa entre pares OTC y regulares =====")
    
    # Crear pares de prueba con mismas características pero diferenciando OTC vs regular
    pairs_to_test = [
        {"name": "EUR/USD-OTC", "is_otc": True},
        {"name": "EUR/USD", "is_otc": False},
        {"name": "GBP/JPY-OTC", "is_otc": True},
        {"name": "GBP/JPY", "is_otc": False}
    ]
    
    for pair_info in pairs_to_test:
        test_signal = {
            "pair": pair_info["name"],
            "direction": "BUY",
            "entry_time": "10:30",
            "duration": "1 دقيقة",
            "probability": "75%",
            "sr_validated": True,
            "sr_info": {
                "level_type": "support",
                "price": 1.2345,
                "strength": 70
            }
        }
        is_valid, quality, reason = filter_trading_signal(test_signal)
        pair_type = "OTC" if pair_info["is_otc"] else "Regular"
        print(f"Par {pair_type} ({pair_info['name']}): {'✅ ACEPTADA' if is_valid else '❌ RECHAZADA'}, calidad: {quality:.2f}")
        
    print("\n===== Prueba completada =====\n")

if __name__ == "__main__":
    test_otc_filter()