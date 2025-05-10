import io
import os
import sys
import logging
from PIL import Image
from chart_analyzer import analyze_chart_image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_chart_image(image_path, pair, timeframe=1):
    """
    Test chart analysis on specific image
    
    Args:
        image_path: Path to image file
        pair: Trading pair name
        timeframe: Timeframe in minutes
    """
    try:
        # Read the image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        # Verify image has data
        image_size = len(image_data)
        logger.info(f"Image size: {image_size} bytes")
        
        if image_size == 0:
            logger.error("Image file is empty!")
            return
            
        # Analyze the chart
        result = analyze_chart_image(image_data, pair, timeframe)
        
        # Print results
        logger.info("=== ANALYSIS RESULT ===")
        logger.info(f"Direction: {result.get('direction', 'Unknown')}")
        logger.info(f"Probability: {result.get('probability', 'Unknown')}")
        logger.info(f"Analysis Notes: {result.get('analysis_notes', 'None')}")
        logger.info("=====================")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing chart image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with the first chart (which should be a BUY signal in the old system but correctly SELL now)
    image_path = "attached_assets/Screenshot_2025-05-07-02-07-33-867_com.android.chrome.jpg"
    result = test_chart_image(image_path, "AUD/NZD OTC", 1)