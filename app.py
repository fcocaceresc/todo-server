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

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }


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


@app.route('/todos', methods=['GET'])
def get_tasks():
    task_objects = db.session.execute(db.select(Task)).scalars()
    tasks = [task.to_dict() for task in task_objects]
    return jsonify({
        'message': 'Tasks retrieved successfully',
        'tasks': tasks
    }), 200


@app.route('/todos', methods=['POST'])
def create_task():
    new_task_data = request.json
    task = Task(name=new_task_data['name'])
    db.session.add(task)
    db.session.commit()
    return jsonify({
        'message': 'Task created successfully',
        'created_task': task.to_dict()
    }), 201


@app.route('/todos/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = db.get_or_404(Task, task_id)
    old_task = task.to_dict()
    updated_task_data = request.json
    task.name = updated_task_data['name']
    db.session.commit()
    return jsonify({
        'message': 'Task updated successfully',
        'old_task': old_task,
        'updated_task': task.to_dict()
    }), 200


@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({
        'message': 'Task deleted successfully',
        'deleted_task': task.to_dict()
    }), 200


if __name__ == '__main__':
    app.run()
