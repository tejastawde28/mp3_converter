import smtplib, os, json
from email.message import EmailMessage

def notification(message):
    try:
        message = json.loads(message)
        mp3_fid = message["mp3_fid"]
        sender_address = os.environ.get("GMAIL_ADDRESS")
        app_password = os.environ.get("GMAIL_APP_PASSWORD")
        receiver_address = message["username"]

        msg = EmailMessage()
        msg.set_content(f"MP3 File ID: {mp3_fid} is now ready!")
        msg["Subject"] = "MP3 Download"
        msg["From"] = sender_address
        msg["To"] = receiver_address

        session = smtplib.SMTP("smtp.gmail.com", 587)
        session.starttls()
        session.login(sender_address, app_password)
        session.send_message(msg)
        session.quit()
        print("Mail Sent")

    except Exception as err:
        print(f"Error sending email: {err}")
        return err