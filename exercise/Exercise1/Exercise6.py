import math
import os
import json
from flask import Flask, request,  abort

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from datetime import datetime
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class StorageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qty = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey(
        "product.id"))
    location = db.Column(db.String(64), nullable=False)
    product = db.relationship("Product", back_populates="in_storage")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(64), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    in_storage = db.relationship("StorageItem", back_populates="product")


db.create_all()


@app.route("/products/add/", methods=["POST"])
def add_product():
    # This branch happens when client submits the JSON document

    if not request.content_type == 'application/json':
        return 'Request content type must be JSON', 415

    try:

        handle = request.json["handle"]
        weight = request.json["weight"]
        price = request.json["price"]
        exist = Product.query.filter_by(handle=handle).first()

        if (isinstance(weight, float) != True or isinstance(price, float) != True):
            return "Incomplete request - missing fields", 400

        if (exist == None):
            pro = Product(
                handle=handle,
                weight=weight,
                price=price
            )
            db.session.add(pro)
            db.session.commit()
            return "successful", 201
        elif (exist != None):
            return "Handle already exists", 409
        else:
            abort(404)
    except (KeyError, ValueError, IntegrityError):

        abort(400)

    except (TypeError):
        return 'Request content type must be JSON', 415


@app.route("/storage/<product>/add/", methods=["POST"])
def add_to_storage(product):
    # This branch happens when client submits the JSON document
    if not request.content_type == 'application/json':
        return 'Request content type must be JSON', 415
    if request.method != 'POST':
        return "POST method required", 405

    try:
        location = request.json["location"]
        qty = request.json["qty"]
        exist = Product.query.filter_by(handle=product).first()
        storage = StorageItem.query.join(Product).filter(
            Product.handle == product).all()
        print(storage)

        if (isinstance(location, str) == False or isinstance(qty, int) == False):
            return "Incomplete request - missing fields", 400

        if (exist == None):
            return "Product not found ", 404
        elif (exist != None):
            print(StorageItem.query.all())
            stor = StorageItem(product=exist, qty=qty, location=location)
            db.session.add(stor)
            db.session.commit()

            return "successful", 201

        else:
            abort(404)
    except (KeyError, ValueError, IntegrityError):
        abort(400)


@app.route("/storage/")
def get_inventory():
    if request.method != 'GET':
        return "GET method required", 405
    results = []
    try:
        products = Product.query.all()

        for j in products:
            dic = {}
            dic['inventory'] = []
            dic['handle'] = j.handle
            dic['weight'] = j.weight
            dic['price'] = j.price

            items = StorageItem.query.join(Product).filter(
                Product.handle == j.handle).all()
            for i in items:
                loca = []
                loca.append(i.location)
                loca.append(i.qty)
                dic['inventory'].append(loca)
            results.append(dic)
        return json.dumps(results)
    except (KeyError, ValueError, IntegrityError):
        abort(400)
