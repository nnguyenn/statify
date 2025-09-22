from flask import Flask

app = Flask(__name__)

#Base Page
@app.get("/")
def home():
  return "hello world"