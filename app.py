import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

db = SQLAlchemy(model_class=Base)
db.init_app(app)
with app.app_context():
    db.create_all()


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'message': 'ok'}), 200


@app.route('/todos', methods=['POST'])
def create_task():
    task_data = request.json
    name = task_data['name']
    task = Task(name=name)
    db.session.add(task)
    db.session.commit()
    return jsonify({'message': 'Task created successfully'}), 200


if __name__ == '__main__':
    app.run()
