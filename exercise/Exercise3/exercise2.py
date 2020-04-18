from flask_restful import Resource
import math
import os
import json
from flask import Flask, request,  abort, Response

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from datetime import datetime
from flask_restful import Api
app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)


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


class ProductItem(Resource):

    def get(self, handle):
        return Response(status=501)


class ProductCollection(Resource):

    def get(self):
        results = []
        try:
            products = Product.query.all()

            for j in products:
                dic = {}
                dic['handle'] = j.handle
                dic['weight'] = j.weight
                dic['price'] = j.price

                results.append(dic)
            return results
        except (KeyError, ValueError, IntegrityError):
            abort(400)

    def post(self):
        # This branch happens when client submits the JSON document
        if request.method == "POST":
            if request.json:
                try:

                    handle = request.json["handle"]
                    weight = request.json["weight"]
                    price = request.json["price"]
                    exist = Product.query.filter_by(handle=handle).first()

                    if (isinstance(weight, float) != True or isinstance(price, float) != True):
                        return "Incomplete request - missing fields", 400

                    if (exist == None):
                        dic = {}
                        pro = Product(
                            handle=handle,
                            weight=weight,
                            price=price
                        )
                        db.session.add(pro)
                        db.session.commit()
                        product_uri = api.url_for(ProductItem, handle=handle)
                        dic["Location"] = product_uri
                        Product_response = Response(
                            headers={"Location": product_uri}, status=201)
                        return Product_response
                    elif (exist != None):
                        return "Handle already exists", 409
                    else:
                        abort(404)
                except (KeyError, ValueError, IntegrityError):

                    abort(400)

                except (TypeError):
                    return 'Request content type must dsfdsfdsbe JSON', 415
            else:
                return "Post method required", 415
            pass


api.add_resource(ProductCollection, "/api/products/")

api.add_resource(ProductItem, "/api/products/<handle>/")
