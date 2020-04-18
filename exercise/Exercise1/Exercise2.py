from flask import Flask, request
import types, math
app = Flask("hello")

@app.route("/trig/<func>")
def trig(func):
    
    try:
        angle = request.args["angle"]
    except KeyError:
        return "Missing query parameter: angle", 500
    try:
        unit = request.args["unit"]
    except :
        unit = 'radian'

    if unit != 'radian' and unit !='degree':
        return "Invalid query parameter value(s)",500


    for c in angle:
        if ord(c) > 58 or ord(c) < 45 or ord(c) == 47:
            return "Invalid query parameter value(s)",500

    if unit == 'degree':
        x = float(angle)/180 * math.pi
        angle = x
    else:
        x = float(angle)
        angle = x


    if func == 'sin':
        result = math.sin(angle)
    elif func == 'cos':
        result = math.cos(angle)
    elif func == 'tan':
        result = math.tan(angle)
    else:
        return "Operation not found", 404

    result = round(result,3)
    
    return "{}".format(result),200

