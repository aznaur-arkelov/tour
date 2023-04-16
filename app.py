import http
import os
import uuid

import flask
import flask_login
import datetime

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

db = SQLAlchemy(app)


class User(db.Model, flask_login.UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)


class Tour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(256), nullable=True)


orders_tours = db.Table('tour_order',
                        db.Column('tour_id', db.Integer, db.ForeignKey('tour.id')),
                        db.Column('order_id', db.Integer, db.ForeignKey('order.id'))
                        )


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    num_of_people = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    tours = db.relationship('Tour', secondary=orders_tours, backref=db.backref('orders', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()
    if flask.request.method == 'POST':
        username = flask.request.form['username']
        password = flask.request.form['password']
        # надо бы проверять что такого пользователя еще нет
        # и хранить хеш от пароля вместо самого пароля
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return flask.redirect('/login')

    return flask.render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()
    if flask.request.method == 'POST':
        username = flask.request.form['username']
        password = flask.request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            flask_login.login_user(user)
            return flask.redirect('/')
        else:
            return flask.render_template('login.html', error=True)

    return flask.render_template('login.html', error=False)


@app.route('/', methods=['GET'])
def index():
    if not flask_login.current_user.is_authenticated:
        return flask.redirect('/login')

    location = flask.request.args.get('location')
    duration = flask.request.args.get('duration')

    if location:
        filtered_tours = Tour.query.filter_by(location=location)
    elif duration:
        filtered_tours = Tour.query.filter_by(duration=duration)
    else:
        filtered_tours = Tour.query.all()

    locations = set()

    for tour in Tour.query.all():
        locations.add(tour.location)

    return flask.render_template('index.html', tours=filtered_tours, locations=locations)


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}


@app.route('/new_tour', methods=['GET', 'POST'])
def new_tour():
    if not flask_login.current_user.admin:
        return flask.redirect('/login')

    request = flask.request
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        location = request.form['location']
        duration = int(request.form['duration'])
        price = int(request.form['price'])

        # handle file upload
        file = request.files.get('image', '')
        filename = uuid.uuid4().hex[:6] + ".jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        tour = Tour(name=name, description=description, location=location, duration=duration, price=price,
                    image=filename)

        db.session.add(tour)
        db.session.commit()

        flask.flash('Тур создан', 'success')
        return flask.redirect('/')

    return flask.render_template('new_tour.html')


@app.route('/add_to_cart/<tour_id>', methods=['POST'])
def add_to_cart(tour_id):
    if not flask_login.current_user.is_authenticated:
        return '', http.HTTPStatus.BAD_REQUEST

    tour = Tour.query.filter_by(id=tour_id)

    if 'cart' not in flask.session:
        flask.session['cart'] = []

    flask.session['cart'].append(tour_id)
    flask.flash('Добавлено в корзину', 'success')
    return flask.redirect('/cart')


@app.route('/cart')
def cart():
    tours = []
    total_price = 0
    if 'cart' in flask.session:
        for tour_id in flask.session['cart']:
            tour = Tour.query.filter_by(id=tour_id).first()
            if tour:
                tours.append(tour)
                total_price += tour.price
    return flask.render_template('cart.html', tours=tours, total_price=total_price)


@app.route('/remove_from_cart/<tour_id>', methods=['POST'])
def remove_from_cart(tour_id):
    if not flask_login.current_user.is_authenticated:
        return '', http.HTTPStatus.BAD_REQUEST

    flask.session['cart'].remove(tour_id)
    flask.flash('Удалено из корзины', 'success')
    return flask.redirect('/cart')


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect('/')


@app.route('/uploads/<name>')
def download_file(name):
    return flask.send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route('/delete_tour/<tour_id>', methods=['POST'])
def delete_tour(tour_id):
    if not flask_login.current_user.is_authenticated:
        return '', http.HTTPStatus.BAD_REQUEST

    if not flask_login.current_user.admin:
        return '', http.HTTPStatus.BAD_REQUEST

    Tour.query.filter_by(id=tour_id).delete()
    db.session.commit()

    return flask.redirect('/')


@app.route('/cart', methods=['POST'])
def order_tour():
    if not flask_login.current_user.is_authenticated:
        return '', http.HTTPStatus.BAD_REQUEST

    request = flask.request
    name = request.form['name']
    email = request.form.get('email')
    num_people = request.form.get('quantity')
    trip_date = datetime.datetime.strptime(request.form.get('date'), '%Y-%m-%d')
    comment = request.form.get('comment')
    tours = []

    if 'cart' in flask.session:
        for tour_id in flask.session['cart']:
            tour = Tour.query.filter_by(id=tour_id).first()
            if tour:
                tours.append(tour)

    flask.session['cart'] = []

    if len(tours) == 0:
        flask.redirect('/cart')

    order = Order(name=name, email=email, num_of_people=num_people, date=trip_date, comment=comment, tours=tours,
                  user_id=flask_login.current_user.id)

    db.session.add(order)
    db.session.commit()

    return flask.redirect('/orders?ordered=True')


@app.route('/orders')
def orders():
    if not flask_login.current_user.is_authenticated:
        return '', http.HTTPStatus.BAD_REQUEST

    if flask_login.current_user.admin:
        orders_list = Order.query.all()
    else:
        orders_list = Order.query.filter_by(user_id=flask_login.current_user.id)

    return flask.render_template('orders.html', orders=orders_list, ordered=bool(flask.request.args.get('ordered')))


if __name__ == '__main__':
    app.run()
