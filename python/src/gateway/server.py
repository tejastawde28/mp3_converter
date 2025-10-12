import os, gridfs, pika, json, time
from flask import Flask, request, send_file
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId

server = Flask(__name__)

mongo_video = PyMongo(server, uri="mongodb://host.minikube.internal:27017/videos")
mongo_mp3 = PyMongo(server, uri="mongodb://host.minikube.internal:27017/mp3s")

fs_videos = gridfs.GridFS(mongo_video.db)
fs_mp3s = gridfs.GridFS(mongo_mp3.db)

connection = None
channel = None

def get_rabbitmq_channel():
    global connection, channel
    if not connection or connection.is_closed:
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
                channel = connection.channel()
                channel.queue_declare(queue='video', durable=True)
                print("Connected to RabbitMQ")
                return channel
            except Exception as e:
                print(f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print("Max retries reached. RabbitMQ connection failed.")
                    return None
    return channel

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)

    if not err:
        return token
    
    else:
        return err

@server.route("/signup", methods=["POST"])
def signup():
    message, err = access.signup(request)
    
    if not err:
        return message
    else:
        return err
    
@server.route("/upload", methods=["POST"])
def upload():
    access, err = validate.token(request)
    
    # Check validation error first
    if err:
        print(f"Validation error: {err}")
        return err
    
    # Check if access is None or empty
    if not access:
        print("Access is None or empty")
        return "not authorized", 401
    
    # Try to parse JSON with error handling
    try:
        access = json.loads(access)
        print(f"Parsed access: {access}")  # Debug print
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Raw access string: {access}")
        return "invalid token format", 500
    
    # Check admin status
    if not access.get("admin", False):
        print(f"User {access.get('username')} is not admin")
        return "not authorized", 401
    
    # File validation
    if len(request.files) != 1:
        return "exactly 1 file required", 400
    
    # Upload file
    for _, f in request.files.items():
        max_upload_retries = 3
        upload_retry_delay = 1
        
        for upload_attempt in range(max_upload_retries):
            channel = get_rabbitmq_channel()
            if channel:
                err = util.upload(f, fs_videos, channel, access)
                if not err:
                    print("Upload successful")
                    break
                else:
                    print(f"Upload utility error (attempt {upload_attempt + 1}): {err}")
                    if upload_attempt < max_upload_retries - 1:
                        print(f"Retrying upload in {upload_retry_delay} seconds...")
                        time.sleep(upload_retry_delay)
                        upload_retry_delay *= 2
                    else:
                        print("Max upload retries reached")
                        return "upload failed, please try again", 400
            else:
                print(f"RabbitMQ not ready (attempt {upload_attempt + 1})")
                if upload_attempt < max_upload_retries - 1:
                    print(f"Retrying upload in {upload_retry_delay} seconds...")
                    time.sleep(upload_retry_delay)
                    upload_retry_delay *= 2
                else:
                    print("Max upload retries reached - RabbitMQ unavailable")
                    return "upload failed, please try again", 400
    
    return "success!", 200
    
@server.route("/download", methods=["GET"])
def download():
    try:
        access, err = validate.token(request)
        if err:
            return err 
        
        access = json.loads(access)
        if access["admin"]:
            fid_string = request.args.get("fid")

            if not fid_string:
                return "fid is required", 400
            
            
            out = fs_mp3s.get(ObjectId(fid_string))
            return send_file(out, download_name=f'{fid_string}.mp3')
        
    except Exception as err:
        print(f"Exception in download route: {err}")
        return "internal server error", 500

    return "not authorized", 401

# After creating connections, verify them
def verify_connections():
    # Verify MongoDB
    try:
        test_id = fs_videos.put(b"startup_test")
        fs_videos.delete(test_id)
        print("MongoDB connection verified")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")

if __name__ == "__main__":
    verify_connections()
    server.run(port=8080, host="0.0.0.0")