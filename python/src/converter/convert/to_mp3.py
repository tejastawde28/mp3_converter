import pika, json, tempfile, os
from bson.objectid import ObjectId
from moviepy import VideoFileClip

def start(message, fs_videos, fs_mp3s, channel):
    message = json.loads(message)
    """ 
    before converting the file, we need to create an empty temporary file and write 
    the video content into the temp file.
    """

    tf = tempfile.NamedTemporaryFile()
    # this will create a temp file in a temp directory in which we will write our video content
    # our video content
    out = fs_videos.get(ObjectId(message["video_fid"]))
    # add video content into the empty file -> bytes returned from the read() method will be written in this file
    tf.write(out.read())
    # now we convert to mp3 from this temp file
    audio = VideoFileClip(tf.name).audio
    tf.close()
    # after closing the temp file autoamtically gets deleted

    # we need to write the audio to the file
    tf_path = tempfile.gettempdir() + f"{message['video_fid']}.mp3"
    # we're first taking the path to our temp dir and appending our desired mp3 file name to the path
    # we want to name the mp3 file as video fid to avoid collisions between different files

    audio.write_audiofile(tf_path)
    # after writing we want to save the file to mongo db
    f = open(tf_path, "rb")
    data = f.read()
    fid = fs_mp3s.put(data) # saving the mp3 file to gridfs
    f.close()
    os.remove(tf_path) # write created a temp file and not tempfile module so manually we need to remove the file

    message["mp3_fid"] = str(fid)
    # put this message in a different queue for mp3
    try:
        channel.basic_publish(
            exchange = "",
            routing_key = os.environ.get("MP3_QUEUE"),
            body = json.dumps(message),
            properties = pika.BasicProperties(
                delivery_mode = pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
    except Exception as err:
        fs_mp3s.delete(fid)
        # we need to delete the file from mongo db if we were unable to add the message in the queue since
        # if the message wasn't added, the mp3 would never be processed.
        return "failed to publish message"