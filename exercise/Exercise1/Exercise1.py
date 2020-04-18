from flask import Flask
app = Flask("hello")

@app.route("/")
def index():
    return "help string that describes how to use the web application (string)"

@app.route("/hello/<name>")
def hello(name):
    return "Hello {}".format(name)

@app.route("/add/<float:number_1>/<float:number_2>")
def plus(number_1, number_2):
    sum = number_1 + number_2
    return "The result is: {}".format(sum)

@app.route("/sub/<float:number_1>/<float:number_2>")
def minus(number_1, number_2):
    sum = number_1 - number_2
    return "The result is: {}".format(sum)

@app.route("/mul/<float:number_1>/<float:number_2>")
def mult(number_1, number_2):
    sum = number_1 * number_2
    return "The result is: {}".format(sum)

@app.route("/div/<float:number_1>/<float:number_2>")
def div(number_1, number_2):
    if number_2 == 0.0:
        return "NaN"
    sum = number_1 / number_2
    return "The result is: {}".format(sum)
