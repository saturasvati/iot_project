from flask import Flask, render_template
from classes import *
import datetime
import env

app = Flask(__name__)

db = DatabaseLink(database=env.DB_DATABASE, host=env.DB_HOST, username=env.DB_USERNAME, password=env.DB_PASSWORD)

@app.route("/api")
def api_main():
	pass

@app.route("/")
def main_page():
	pass