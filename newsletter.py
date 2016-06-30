from flask import Flask, render_template, request
import json
import requests
import datetime
import pytz
from flask_mail import Mail, Message

app = Flask(__name__)

app.config.update(
	DEBUG = True,
	MAIL_SERVER = 'smtp.gmail.com',
	MAIL_PORT = 465,
	MAIL_USE_SSL = True,
	MAIL_USE_TLS = False,
	MAIL_USERNAME = 'zack.gray@levelsolar.com',
	MAIL_PASSWORD = 'levelsolar'
	)

mail = Mail(app)

recipients = ['newsletter@levelsolar.com']

zack = ['zspencergray@gmail.com']



def send_mail():		
	body = render_template("newsletter.html", info=info)
	msg = Message('Sales Newsletter %s' %info["date"], sender='Zack Gray', recipients=recipients)
	msg.html = body
	mail.send(msg)
	return "Done."

def send_error():
	msg = Message('Newsletter Error', sender='Zack Gray', recipients=zack)
	mail.send(msg)
	return "Done."

if __name__ == "__main__":
	data_file = open("/root/lboard/data.json", "r")
	info = json.load(data_file)
	data_file.close()
	utc_zone = pytz.timezone('UTC')
	est_zone = pytz.timezone('US/Eastern')
	now_utc_naive = datetime.datetime.utcnow()
	now_utc_aware = utc_zone.localize(now_utc_naive)
	now_est_aware = now_utc_aware.astimezone(est_zone)
	if info["check"] == now_est_aware.day:
		with app.app_context():
			send_mail()
	else:
		with app.app_context():
			send_error()
