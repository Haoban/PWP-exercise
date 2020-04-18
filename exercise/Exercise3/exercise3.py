from flask_restful import Resource
import math
import os
import json
from flask import Flask, request, abort, Response
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


class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.
    """

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.

        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.

        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, ns, uri):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.

        : param str ns: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][ns] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.

        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href


class StorageEntry(db.Model):
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
    in_storage = db.relationship("StorageEntry", back_populates="product")


db.create_all()


class InventoryBuilder(MasonBuilder):

    @staticmethod
    def product_schema():
        schema = {
            "type": "object",
            "required": ["handle", "weight", "price"]
        }
        props = schema["properties"] = {}
        props["handle"] = {
            "description": "Products's unique name",
            "type": "string"
        }
        props["weight"] = {
            "description": "weight of the product's model",
            "type": "number"
        }

        props["price"] = {
            "description": "price of the product's model",
            "type": "number"
        }
        return schema

    def add_control_delete_product(self, handle):
        self.add_control(
            "storage:delete",
            href=api.url_for(ProductItem, handle=handle),
            method="DELETE",
            title="Delete this resource"
        )

    def add_control_all_products(self):
        self.add_control(
            "storage:products-all",
            "/api/products/",
            method="GET",
            title="get all products"
        )

    def add_control_add_product(self):

        self.add_control(
            "storage:add-product",
            "/api/products/",
            method="POST",
            encoding="json",
            title="Add a new product",
            schema=self.product_schema()
        )

    def add_control_edit_product(self, handle):

        self.add_control(
            "edit",
            href=api.url_for(ProductItem, handle=handle),
            method="Put",
            encoding="json",
            title="Edit a product",
            schema=self.product_schema()
        )


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
