"""
MiroFish Backend - FastAPI WSGI Gateway
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from flask import Flask, request
from flask_cors import CORS
import logging

from .config import Config
from .utils.logger import setup_logger, get_logger
from .utils.locale import set_locale, get_locale_from_header

def create_flask_app(config_class=Config):
    """Flask应用工厂函数 - Now a sub-app"""
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)
    
    if hasattr(flask_app, 'json') and hasattr(flask_app.json, 'ensure_ascii'):
        flask_app.json.ensure_ascii = False
    
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})
    
    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp
    flask_app.register_blueprint(graph_bp, url_prefix='/api/graph')
    flask_app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    flask_app.register_blueprint(report_bp, url_prefix='/api/report')
    
    @flask_app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Flask 请求: {request.method} {request.path}")
        # Setup locale for Flask global request context via contextvars
        accept_lang = request.headers.get("Accept-Language", "")
        set_locale(get_locale_from_header(accept_lang))
        
    return flask_app

def create_app(config_class=Config):
    """FastAPI应用工厂函数 - The main entry point"""
    app = FastAPI(title="MiroFish Backend API")
    
    # 设置日志
    logger = setup_logger('mirofish')
    
    # 启用CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册模拟进程清理函数
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    
    # Health check native to FastAPI
    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend (FastAPI)'}
        
    # Mount the existing Flask app via WSGI
    flask_app = create_flask_app(config_class)
    app.mount("/", WSGIMiddleware(flask_app))
    
    return app

# 为 uvicorn 提供默认的 app 实例
app = create_app()
