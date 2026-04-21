import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configurações do Banco e JWT
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://om_user:vision@localhost:5432/om_database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'chave-secreta-super-segura-om-2026'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=4)

    # Liga as extensões à app
    db.init_app(app)
    jwt.init_app(app)

    # ==========================================
    # CONFIGURAÇÕES DE UPLOADS
    # ==========================================
    # Define o caminho absoluto para a pasta 'uploads'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    # Limita o tamanho máximo do ficheiro a 16 Megabytes (Segurança contra sobrecarga)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


    # ==========================================
    # REGISTO DE ROTAS
    # ==========================================
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

    # ==========================================
    # CONFIGURAÇÃO DO SWAGGER UI
    # ==========================================
    SWAGGER_URL = '/docs'  # URL onde a documentação ficará acessível
    API_URL = '/static/swagger.yaml'  # Caminho para o ficheiro YAML

    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "API de Orientação e Mobilidade (OM)"
        }
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    return app