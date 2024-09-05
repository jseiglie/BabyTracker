"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for, send_from_directory
from flask_migrate import Migrate
from flask_swagger import swagger
from api.utils import APIException, generate_sitemap
from api.models import db, TokenBlockedList
from api.routes import api
from api.admin import setup_admin
from api.commands import setup_commands
from flask_jwt_extended import JWTManager
#importaciones para firebase
import firebase_admin
from firebase_admin import credentials


# from models import Person

ENV = "development" if os.getenv("FLASK_DEBUG") == "1" else "production"
static_file_dir = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '../public/')
app = Flask(__name__)
app.url_map.strict_slashes = False

jwt = JWTManager(app)

####verifica si un token ha sido revocado o es invalido
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:

    #1ra condicion: el token es valido
    is_password = jwt_payload["type"]=="password" and request.path != "/api/changepassword"

    #2da condicion: el token es está en la lista de bloqueado
    jti = jwt_payload["jti"]
    token = TokenBlockedList.query.filter_by(jti=jti).first()
    is_blocked = token is not None

    print (is_password)
    print (is_blocked)

    if jwt_payload["type"] == "password":
        return is_blocked and not is_password
    else:
        return is_blocked

#FIREBASE
credentials_fb={
     "type": os.getenv("TYPE"),
     "project_id": os.getenv("PROJECT_ID"),
     "private_key_id": os.getenv("PRIVATE_KEY_ID"),
     "private_key": f"-----BEGIN PRIVATE KEY-----\n{os.getenv('PRIVATE_KEY')}\n-----END PRIVATE KEY-----\n",
     "client_email": os.getenv("CLIENT_EMAIL"),
     "client_id": os.getenv("CLIENT_ID"),
     "auth_uri": os.getenv("AUTH_URI"),
     "token_uri": os.getenv("TOKEN_URI"),
     "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
     "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL")
}
cred=credentials.Certificate(credentials_fb)
firebase_admin.initialize_app(cred,{
    'storageBucket': 'babytracker-53621.appspot.com'
})

# database condiguration
db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db, compare_type=True)
db.init_app(app)

# add the admin
setup_admin(app)

# add the admin
setup_commands(app)

# Add all endpoints form the API with a "api" prefix
app.register_blueprint(api, url_prefix='/api')

# Handle/serialize errors like a JSON object


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints


@app.route('/')
def sitemap():
    if ENV == "development":
        return generate_sitemap(app)
    return send_from_directory(static_file_dir, 'index.html')

# any other endpoint will try to serve it like a static file


@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0  # avoid cache memory
    return response


# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=PORT, debug=True)
