#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stream Proxy - Backend con Selenium
Extrae URLs de video desde iframes bloqueados usando Chrome real
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuración
CHROMEDRIVER_PATH = r'C:\chromedriver\chromedriver.exe'  # Ajusta tu ruta
TIMEOUT = 20  # segundos para esperar elementos

def get_chrome_driver():
    """Crear driver de Chrome con opciones optimizadas"""
    try:
        chrome_service = Service(CHROMEDRIVER_PATH)
        options = webdriver.ChromeOptions()
        
        # Opciones de rendimiento y seguridad
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--window-size=1920,1080")
        
        # Descomentar para modo headless (sin interfaz visual)
        # options.add_argument("--headless")
        # options.add_argument("--hide-scrollbars")
        
        driver = webdriver.Chrome(service=chrome_service, options=options)
        logger.info("Driver de Chrome creado exitosamente")
        return driver
    except Exception as e:
        logger.error(f"Error al crear driver de Chrome: {e}")
        raise

def extract_video_from_iframe(driver, iframe_url):
    """Extrae URL de video desde un iframe"""
    try:
        logger.info(f"Navigando a: {iframe_url}")
        driver.get(iframe_url)
        driver.set_page_load_timeout(TIMEOUT)
        
        # Esperar a que cargue el iframe
        logger.info("Esperando iframe...")
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        # Buscar elemento video en el iframe
        try:
            logger.info("Buscando iframe anidado...")
            iframe = driver.find_element(By.TAG_NAME, "iframe")
            driver.switch_to.frame(iframe)
            
            logger.info("Esperando elemento video...")
            video_element = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            video_url = video_element.get_attribute('src')
            
            if video_url:
                logger.info(f"Video encontrado: {video_url[:100]}...")
                return video_url
                
        except Exception as e:
            logger.warning(f"No se encontró iframe anidado, intentando video directo: {e}")
            driver.switch_to.default_content()
            
            # Intentar encontrar video directamente
            video_element = driver.find_element(By.TAG_NAME, "video")
            video_url = video_element.get_attribute('src')
            
            if video_url:
                logger.info(f"Video directo encontrado: {video_url[:100]}...")
                return video_url
        
        # Si no hay video tag, intentar extraer desde script o data attributes
        logger.warning("No se encontró video tag, intentando alternativas...")
        
        # Buscar en scripts
        scripts = driver.find_elements(By.TAG_NAME, "script")
        for script in scripts:
            content = script.get_attribute('innerHTML')
            if 'http' in content and '.m3u8' in content:
                logger.info("Encontrado M3U8 en script")
                return content
        
        return None
        
    except Exception as e:
        logger.error(f"Error extrayendo video: {e}")
        raise

@app.route('/health', methods=['GET'])
def health():
    """Health check del servidor"""
    response = jsonify({
        'status': 'ok',
        'service': 'Stream Proxy',
        'version': '1.0'
    })
    return response, 200

@app.route('/api/extract-stream', methods=['POST', 'OPTIONS'])
def extract_stream():
    """
    Extrae URL de video desde un iframe bloqueado
    
    POST /api/extract-stream
    {
        "url": "https://daddyhd.com/stream/stream-532.php"
    }
    
    Respuesta:
    {
        "success": true,
        "video_url": "https://...",
        "message": "Stream extraído exitosamente"
    }
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.get_json()
        iframe_url = data.get('url')
        
        if not iframe_url:
            logger.warning("URL no proporcionada")
            return jsonify({'error': 'URL requerida', 'success': False}), 400

        driver = None
        try:
            driver = get_chrome_driver()
            
            logger.info(f"Extrayendo stream desde: {iframe_url}")
            video_url = extract_video_from_iframe(driver, iframe_url)
            
            if video_url:
                logger.info("Stream extraído correctamente")
                return jsonify({
                    'success': True,
                    'video_url': video_url,
                    'message': 'Stream extraído exitosamente'
                }), 200
            else:
                logger.warning("No se encontró URL de video")
                return jsonify({
                    'success': False,
                    'error': 'No se encontró URL de video en el iframe'
                }), 404
                
        finally:
            if driver:
                driver.quit()
                logger.info("Driver cerrado")
        
    except Exception as e:
        logger.error(f"Error en extract_stream: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy-iframe', methods=['POST', 'OPTIONS'])
def proxy_iframe():
    """
    Devuelve URL proxificada del iframe
    
    POST /api/proxy-iframe
    {
        "url": "https://ejemplo.com/iframe"
    }
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.get_json()
        iframe_url = data.get('url')
        
        if not iframe_url:
            return jsonify({'error': 'URL requerida', 'success': False}), 400

        # Devolver URL para embeber
        return jsonify({
            'success': True,
            'iframe_url': iframe_url,
            'message': 'URL lista para embeber'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en proxy_iframe: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtener configuración del servidor"""
    return jsonify({
        'chromedriver_path': CHROMEDRIVER_PATH,
        'timeout': TIMEOUT,
        'endpoints': [
            '/health',
            '/api/extract-stream (POST)',
            '/api/proxy-iframe (POST)',
            '/api/config (GET)'
        ]
    }), 200

if __name__ == '__main__':
    logger.info("Iniciando Stream Proxy Server...")
    logger.info(f"ChromeDriver: {CHROMEDRIVER_PATH}")
    logger.info(f"Timeout: {TIMEOUT}s")
    logger.info("Servidor disponible en http://localhost:5000")
    
    # Ejecutar servidor
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )