import jwt, datetime, os
from flask import Flask, request
from flask_mysqldb import MySQL
import hashlib


server = Flask(__name__)
mysql = MySQL(server)

# config
server.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
server.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
server.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
server.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")
server.config["MYSQL_PORT"] = int(os.environ.get("MYSQL_PORT"))

@server.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return "email and password are required", 400
        
        email = data['email']
        password = data['password']
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return "invalid email format", 400
        
        # Password strength validation (at least 6 characters)
        if len(password) < 6:
            return "password must be at least 6 characters long", 400
        
        # Check if user already exists
        cur = mysql.connection.cursor()
        res = cur.execute("SELECT email FROM user WHERE email=%s", (email,))
        
        if res > 0:
            cur.close()
            return "user already exists", 409
        
        # Hash password (for security - though basic, better than plain text)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Insert new user
        cur.execute("INSERT INTO user (email, password) VALUES (%s, %s)", (email, hashed_password))
        mysql.connection.commit()
        cur.close()
        
        return "user created successfully", 201
        
    except Exception as e:
        return "internal server error", 500

@server.route("/login", methods=["POST"])
def login():
    auth = request.authorization
    if not auth:
        return "missing credentials",401
    # check db for credentials
    cur = mysql.connection.cursor()
    res = cur.execute(
        "SELECT email, password FROM user WHERE email=%s", (auth.username,)
    )
    if res > 0:
        user_row = cur.fetchone()
        email = user_row[0]
        password = user_row[1]
        
        # Hash the provided password to compare with stored hash
        provided_password_hash = hashlib.sha256(auth.password.encode()).hexdigest()
        
        if auth.username != email or provided_password_hash != password:
            return "invalid credentials", 401
        else:
            return createJWT(auth.username, os.environ.get("JWT_SECRET"), True)
    else:
        return "invalid credentials", 401
    
@server.route("/validate", methods=["POST"])
def validate():
    encoded_jwt = request.headers["Authorization"]
    
    if not encoded_jwt:
        return "missing credentials", 401
    
    encoded_jwt = encoded_jwt.split(" ")[1]

    try:
        decoded = jwt.decode(
            encoded_jwt, os.environ.get("JWT_SECRET"), algorithms=["HS256"]
        )
    except:
        return "not authorized", 403
    
    return decoded, 200

def createJWT(username, secret, authz):
    return jwt.encode(
        {
            "username": username,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(tz=datetime.timezone.utc),
            "admin": authz,
        },
        secret,
        algorithm="HS256",
    )

if __name__ == "__main__":
    server.run(port=5000, host="0.0.0.0")