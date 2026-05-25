import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

app = create_app()

if __name__ == '__main__':
    is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(debug=is_dev, host='127.0.0.1', port=5000)
