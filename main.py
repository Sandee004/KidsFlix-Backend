from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_cors import CORS
from datetime import timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

jwt = JWTManager(app)
db = SQLAlchemy(app)
CORS(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(100), unique = True, nullable=False)
    email = db.Column(db.String(100), unique = True, nullable = False)

class Favourite(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)

@app.route('/')
def home():
    return "Home"


@app.route('/api/register', methods=["POST"])
def register():
    username = request.json.get('username')
    email = request.json.get("email")

    if not username or not email:
        return jsonify({"message": "Fill all fields"})
    
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email is already in use"})
    
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username is taken"})
    
    new_user = User(username=username, email=email)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201


@app.route('/api/login', methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('email'):
        return jsonify({'error': 'Missing username or email'}), 400 

    username = data.get('username')
    email = data.get('email')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Account does not exist"}), 404
    
    if user.username != username or user.email != email:
        return jsonify({"message": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200


@app.route("/api/toogle_favourites", methods=["POST"])
@jwt_required()
def toogle_favourite():
    try:
        current_user_id = get_jwt_identity()
        data  = request.get_json()
        movie_id = data['movie_id']
        title = data['title']

        existing_favourite = Favourite.query.filter_by(user_id=current_user_id, movie_id=movie_id).first()

        if existing_favourite:
            db.session.delete(existing_favourite)
            db.session.commit()
            return jsonify({"action": "removed"}), 200
        else:
            new_favourite = Favourite(user_id=current_user_id, movie_id=movie_id, title=title)
            db.session.add(new_favourite)
            db.session.commit()
            return jsonify({"action": "added"}), 200
        
    except Exception as e:
        print(f"Error in toggle_favourite: {str(e)}")
        return jsonify({"error": str(e)}), 401


@app.route("/api/favourites", methods=["GET"])
@jwt_required()
def get_favourites():
    current_user_id = get_jwt_identity()
    favourites = Favourite.query.filter_by(user_id=current_user_id).all()
    return jsonify([
        {"movie_id": fav.movie_id, "title": fav.title}
        for fav in favourites
    ]), 200


@app.route('/api/check-token', methods=["GET"])
@jwt_required()
def check_token():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user:
            return jsonify({"message": "Token is valid",
                            "user": {
                                "id": user.id,
                                "username": "user.username",
                                "email": user.email
                            }
                            }), 200
        else:
            return jsonify({"messgae": "User not found"}), 404
        
    except Exception as e:
        print(f"Error in check_token: {str(e)}")
        return jsonify({"message": "Invalid or expired token"}), 401


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
