import pika, json

def upload(f, fs, channel, access):
    try:
        print(f"Attempting to store file in MongoDB")
        fid = fs.put(f)
        print(f"File stored with ID: {fid}")
    except Exception as err:
        print(f"MongoDB storage failed: {err}")
        return "internal server error", 500
    
    message = {
        "video_fid": str(fid),
        "mp3_fid": None,  
        "username": access["username"],
    }
    
    try:
        print(f"Publishing message to RabbitMQ: {message}")
        channel.basic_publish(
            exchange="",
            routing_key="video",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        print("Message published successfully")
    except Exception as err:
        print(f"RabbitMQ publish failed: {err}")
        fs.delete(fid)
        return "internal server error", 500
    
    return None