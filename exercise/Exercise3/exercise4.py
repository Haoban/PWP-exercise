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
from jsonschema import validate, ValidationError
app = Flask(__name__)


@app.route("/tt")
def index():
    return "This is a calculator which has a operators"


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

LINK_RELATIONS_URL = "/producthub/link-relations/"
PRODUCT_PROFILE = "/profiles/product/"
ERROR_PROFILE = "/profiles/error/"
MASON = "application/vnd.mason+json"

# Profiles


@app.route("/profiles/<resource>/")
def send_profile_html(resource):
    return "Random string"
    # return send_from_directory(app.static_folder, "{}.html".format(resource))


@app.route("/storage/link-relations/")
def send_link_relations_html():
    return "some string"
    # return send_from_directory(app.static_folder, "links-relations.html")


def create_error_response(status_code, title, message=None):
    resource_url = request.path
    body = MasonBuilder(resource_url=resource_url)
    body.add_error(title, message)
    body.add_control("profile", href=ERROR_PROFILE)
    return Response(json.dumps(body), status_code, mimetype=MASON)


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
            "/api/",
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
        db_product = Product.query.filter_by(handle=handle).first()
        if db_product is None:
            return create_error_response(404, "Not found",
                                         "No product was found with the handle {}".format(
                                             handle)
                                         )

        body = InventoryBuilder(
            handle=db_product.handle,
            weight=db_product.weight,
            price=db_product.price

        )
        body.add_namespace("prohub", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(ProductItem, handle=handle))
        body.add_control("profile", PRODUCT_PROFILE)
        body.add_control_delete_product(handle)
        body.add_control_edit_product(handle)
        body.add_control("collection", api.url_for(ProductCollection))

        return Response(json.dumps(body), 200, mimetype=MASON)

    def put(self, handle):
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                                         "Requests must be JSON"
                                         )
        try:
            validate(request.json, InventoryBuilder.product_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        product = Product(
            handle=request.json["handle"],
            weight=request.json["weight"],
            price=request.json["price"]

        )
        if (handle != request.json["handle"]):
            db_product = Product.query.filter_by(handle=product.handle).first()
            if (db_product != None):

                return create_error_response(409, "Already exists",
                                             "product with name '{}' already exists.".format(
                                                 request.json["handle"])
                                             )

        db_product = Product.query.filter_by(handle=product.handle).first()
        if db_product is None:
            return create_error_response(404, "Not found",
                                         "No product was found with the handle {}".format(
                                             product.handle)
                                         )

        try:
            db_product.handle = request.json["handle"]
            db_product.weight = request.json["weight"]
            db_product.price = request.json["price"]

            db.session.commit()
        except KeyError:
            return create_error_response(400, "Missing fields", "missing fields")
        except IntegrityError:
            return create_error_response(409, "Already exists",
                                         "product with name '{}' already exists.".format(
                                             request.json["handle"])
                                         )

        return Response("", 204)

    def delete(self, handle):
        db_product = Product.query.filter_by(handle=handle).first()

        if db_product is None:
            return create_error_response(404, "Not found",
                                         "No product was found with the handle {}".format(db_product["handle"]))

        db.session.delete(db_product)
        db.session.commit()

        return Response("", 204)


class ProductCollectionMain(Resource):

    def get(self):
        results = []
        try:
            products = Product.query.all()
            body = InventoryBuilder(items=[])

            for j in products:
                item = MasonBuilder(
                    handle=j.handle, weight=j.weight, price=j.price)
                item.add_control("self", api.url_for(
                    ProductItem, handle=j.handle))
                item.add_control("profile", "/profiles/product/")
                body["items"].append(item)

            body.add_namespace("storage", "/storage/link-relations/")
            body.add_control_all_products()
            body.add_control_add_product()
            return Response(json.dumps(body), 200, mimetype=MASON)
        except (KeyError, ValueError, IntegrityError):
            abort(400)


class ProductCollection(Resource):

    def get(self):
        results = []
        try:
            products = Product.query.all()
            body = InventoryBuilder(items=[])

            for j in products:
                item = MasonBuilder(
                    handle=j.handle, weight=j.weight, price=j.price)
                item.add_control("self", api.url_for(
                    ProductItem, handle=j.handle))
                item.add_control("profile", "/profiles/product/")
                body["items"].append(item)
            print(body)
            body.add_namespace("prohub", LINK_RELATIONS_URL)
            body.add_control_all_products()
            body.add_control_add_product()
            return Response(json.dumps(body), 200, mimetype=MASON)
        except (KeyError, ValueError, IntegrityError):
            abort(400)

    def post(self):
        if not request.json:
            return create_error_response(415, "Unsupported media type",
                                         "Requests must be JSON"
                                         )

        try:
            validate(request.json, InventoryBuilder.product_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        product = Product(
            handle=request.json["handle"],
            weight=request.json["weight"],
            price=request.json["price"]

        )

        try:

            db.session.add(product)
            db.session.commit()

        except IntegrityError:
            return create_error_response(409, "Already exists",
                                         "Product with handle '{}' already exists.".format(
                                             request.json["handle"])
                                         )

        body = InventoryBuilder()

        body.add_control("self", api.url_for(
            ProductItem, handle=product.handle))
        body.add_namespace("prohub", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(
            ProductItem, handle=product.handle))
        body.add_control("profile", PRODUCT_PROFILE)
        body.add_control_delete_product(product.handle)
        body.add_control_edit_product(product.handle)
        body.add_control_all_products()
        return Response(status=201, headers={
            "Location": api.url_for(ProductItem, handle=request.json["handle"])
        })


api.add_resource(ProductCollectionMain, "/api/")

api.add_resource(ProductCollection, "/api/products/")

api.add_resource(ProductItem, "/api/products/<handle>/")
