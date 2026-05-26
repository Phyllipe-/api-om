import os
from datetime import timedelta
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_swagger_ui import get_swaggerui_blueprint
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

def create_app():
    app = Flask(__name__)

    # ── Credenciais via variáveis de ambiente ─────────────────────────────────
    db_url = os.environ.get('DATABASE_URL')
    jwt_secret = os.environ.get('JWT_SECRET_KEY')
    if not db_url or not jwt_secret:
        raise RuntimeError("DATABASE_URL e JWT_SECRET_KEY precisam estar definidos no .env")

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=4)

    # ── CORS restrito às origens configuradas ─────────────────────────────────
    raw_origins = os.environ.get('ALLOWED_ORIGINS', '')
    allowed_origins = [o.strip() for o in raw_origins.split(',') if o.strip()]
    if not allowed_origins:
        allowed_origins = ['http://localhost:3000']

    CORS(app, resources={r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,
        "max_age": 3600,
    }})

    # ── Upload ────────────────────────────────────────────────────────────────
    app.config['UPLOAD_FOLDER'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # ── Extensões ─────────────────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # ── Handler genérico de erros (não vaza stack trace) ─────────────────────
    is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'

    @app.route('/')
    def index():
        return jsonify({"status": "API OM online", "versao": "1.0", "docs": "/docs"}), 200

    @app.errorhandler(404)
    def handle_not_found(e):
        import logging
        logging.warning("404 Not Found: %s %s", request.method, request.path)
        return jsonify({"erro": f"Rota não encontrada: {request.method} {request.path}"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({"erro": f"Método {request.method} não permitido em {request.path}"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        import logging, traceback
        logging.error("Unhandled exception: %s\n%s", e, traceback.format_exc())
        if is_dev:
            return jsonify({"erro": str(e)}), 500
        return jsonify({"erro": "Erro interno. Tente novamente ou contacte o suporte."}), 500

    @app.errorhandler(429)
    def handle_ratelimit(e):
        return jsonify({"erro": "Muitas tentativas. Aguarde antes de tentar novamente."}), 429

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.routes.alunos import alunos_bp
    app.register_blueprint(alunos_bp, url_prefix='/api/alunos')

    from app.routes.treinos import treinos_bp
    app.register_blueprint(treinos_bp, url_prefix='/api/treinos')

    from app.routes.analises import analises_bp
    app.register_blueprint(analises_bp, url_prefix='/api/analises')

    from app.routes.atividades import atividades_bp
    app.register_blueprint(atividades_bp, url_prefix='/api/atividades')

    from app.routes.professores import professores_bp
    app.register_blueprint(professores_bp, url_prefix='/api/professores')

    from app.routes.quadros import quadros_bp
    app.register_blueprint(quadros_bp, url_prefix='/api/quadros')

    # ── Swagger (apenas em dev) ───────────────────────────────────────────────
    if is_dev:
        swaggerui_blueprint = get_swaggerui_blueprint(
            '/docs', '/static/swagger.yaml',
            config={'app_name': "API de Orientação e Mobilidade (OM)"}
        )
        app.register_blueprint(swaggerui_blueprint, url_prefix='/docs')

    return app
