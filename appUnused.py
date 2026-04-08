import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Replace 'your_password' with your actual MySQL root password
# Format: mysql+mysqlconnector://user:password@host/database_name
password = os.getenv('DB_PASSWORD')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{password}@localhost/travel_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the Model (this matches your 'travel_data' table)
class TravelData(db.Model):
    __tablename__ = 'travel_data'
    id = db.Column(db.String(50), primary_key=True)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    budget_level = db.Column(db.String(50))
    # Add other columns from your SQL file as needed

@app.route('/')
def home():
    return "Travel API is running!"

if __name__ == '__main__':
    app.run(debug=True)
    
@app.route('/destinations', methods=['GET'])
def get_destinations():
    destinations = TravelData.query.all()
    output = []
    for d in destinations:
        output.append({'id': d.id, 'city': d.city, 'country': d.country})
    return jsonify(output)

@app.route('/destinations', methods=['POST'])
def add_destination():
    data = request.get_json()
    new_dest = TravelData(id=data['id'], city=data['city'], country=data['country'])
    db.session.add(new_dest)
    db.session.commit()
    return jsonify({'message': 'Destination added!'}), 201

@app.route('/destinations/<id>', methods=['PUT'])
def update_destination(id):
    dest = TravelData.query.get_or_404(id)
    data = request.get_json()
    dest.city = data.get('city', dest.city)
    db.session.commit()
    return jsonify({'message': 'Updated successfully'})

@app.route('/destinations/<id>', methods=['DELETE'])
def delete_destination(id):
    dest = TravelData.query.get_or_404(id)
    db.session.delete(dest)
    db.session.commit()
    return jsonify({'message': 'Deleted successfully'})