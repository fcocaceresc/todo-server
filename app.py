import os
from datetime import datetime, timezone, timedelta
from functools import wraps

import bcrypt
import jwt
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, ForeignKey, select, and_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    user: Mapped["User"] = relationship(back_populates="tasks")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id
        }


load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

SECRET_KEY = os.getenv('SECRET_KEY')
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRE_HOURS = 24

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

db = SQLAlchemy(model_class=Base)
db.init_app(app)
with app.app_context():
    db.create_all()


def validate_user_data(data):
    if 'username' not in data:
        return jsonify({'error': 'Username is required'}), 400
    if 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400
    if not data['username'] or not data['username'].strip():
        return jsonify({'error': 'Username must not be empty'}), 400
    if not data['password'] or not data['password'].strip():
        return jsonify({'error': 'Password must not be empty'}), 400
    return None


def validate_task_name(data):
    if 'name' not in data:
        return jsonify({'error': 'Task name is required'}), 400
    if not data['name'] or not data['name'].strip():
        return jsonify({'error': 'Task name must not be empty'}), 400
    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]

        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            current_user = db.session.get(User, data['user_id'])
            if not current_user:
                raise ValueError("User not found")
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'message': 'ok'}), 200


@app.route('/register', methods=['POST'])
def register():
    new_user_data = request.json

    validation_error = validate_user_data(new_user_data)
    if validation_error:
        return validation_error

    existing_user = db.session.execute(
        db.select(User).where(User.username == new_user_data['username'])).scalar_one_or_none()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409

    password_bytes = new_user_data['password'].encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)

    new_user = User(
        username=new_user_data['username'],
        password=hashed_password.decode('utf-8')
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    login_data = request.json

    if (not login_data) or ('username' not in login_data) or ('password' not in login_data):
        return jsonify({'error': 'Username and password required'}), 400

    user = db.session.execute(
        db.select(User).where(User.username == login_data['username'])
    ).scalar_one_or_none()

    password_bytes = login_data['password'].encode('utf-8')
    hashed_password_bytes = user.password.encode('utf-8')

    if not user or not bcrypt.checkpw(password_bytes, hashed_password_bytes):
        return jsonify({'error': 'Invalid username or password'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.now(tz=timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    },
        SECRET_KEY,
        algorithm=JWT_ALGORITHM)
    return jsonify({'token': token}), 200


@app.route('/todos', methods=['GET'])
@token_required
def get_tasks(current_user):
    task_objects = db.session.execute(db.select(Task).where(Task.user_id == current_user.id)).scalars().all()
    tasks = [task.to_dict() for task in task_objects]
    return jsonify({
        'message': 'Tasks retrieved successfully',
        'tasks': tasks
    }), 200


@app.route('/todos', methods=['POST'])
@token_required
def create_task(current_user):
    new_task_data = request.json

    name_error = validate_task_name(new_task_data)
    if name_error:
        return name_error

    task = Task(name=new_task_data['name'], user_id=current_user.id)
    db.session.add(task)
    db.session.commit()
    return jsonify({
        'message': 'Task created successfully',
        'created_task': task.to_dict()
    }), 201


@app.route('/todos/<task_id>', methods=['PUT'])
@token_required
def update_task(current_user, task_id):
    if not task_id.isdigit():
        return jsonify({'error': 'Invalid task id'})

    updated_task_data = request.json

    name_error = validate_task_name(updated_task_data)
    if name_error:
        return name_error

    task = db.session.execute(
        select(Task).where(and_(Task.id == task_id, Task.user_id == current_user.id))).scalar_one_or_none()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    old_task = task.to_dict()
    task.name = updated_task_data['name']
    db.session.commit()

    return jsonify({
        'message': 'Task updated successfully',
        'old_task': old_task,
        'updated_task': task.to_dict()
    }), 200


@app.route('/todos/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    task = db.session.execute(
        select(Task).where(and_(Task.id == task_id, Task.user_id == current_user.id))).scalar_one_or_none()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({
        'message': 'Task deleted successfully',
        'deleted_task': task.to_dict()
    }), 200


if __name__ == '__main__':
    app.run()
