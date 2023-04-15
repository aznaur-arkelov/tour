import os
import flask
import flask_login

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy


app = flask.Flask(__name__)

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
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


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect('/')

if __name__ == '__main__':
    app.run()
