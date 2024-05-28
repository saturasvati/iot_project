from flask import Flask, render_template, request, Response
from classes import *
import datetime
import env

app = Flask(__name__)

db = DatabaseLink(database=env.DB_DATABASE, host=env.DB_HOST, username=env.DB_USERNAME, password=env.DB_PASSWORD)

tokens_catch = db.get_tokens()
room: list[Room] = {}

room["main"] = Room("main", db)

def update_tokens_catch(db):
	pass

@app.route("/api/<request_room>/<sensor_name>", methods=["POST"])
def api_main(request_room):
	try:
		room[request_room]
	except KeyError:
		return Response("Request room not exist",status=404)
	try:
		room[request_room].
	except KeyError:
		return Response("Request room not exist",status=404)
	token = request.headers["Auth"]
	if token == (None or ""):
		return Response("Token is necessary",status=401)
	if not room["main"].is_in_tokens_list(token):
		return Response("Token not accepted",status=403)
	

@app.route("/")
def main_page():
	pass