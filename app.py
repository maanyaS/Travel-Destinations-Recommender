import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
load_dotenv()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

password = quote_plus(os.getenv('DB_PASSWORD'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{password}@127.0.0.1/travel_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class TravelData(db.Model):
    __tablename__ = 'travel_data'
    id             = db.Column(db.String(50), primary_key=True)
    city           = db.Column(db.String(100))
    country        = db.Column(db.String(100))
    region         = db.Column(db.String(100))
    short_description = db.Column(db.Text)
    latitude       = db.Column(db.String(50))
    longitude      = db.Column(db.String(50))
    avg_temp_monthly  = db.Column(db.Text)
    ideal_durations   = db.Column(db.Text)
    budget_level   = db.Column(db.String(50))
    culture        = db.Column(db.String(10))
    adventure      = db.Column(db.String(10))
    nature         = db.Column(db.String(10))
    beaches        = db.Column(db.String(10))
    nightlife      = db.Column(db.String(10))
    cuisine        = db.Column(db.String(10))
    wellness       = db.Column(db.String(10))
    urban          = db.Column(db.String(10))
    seclusion      = db.Column(db.String(10))


@app.route('/')
def home():
    return "Travel API is running!"


# GET all destinations
@app.route('/destinations', methods=['GET'])
def get_destinations():
    destinations = TravelData.query.all()
    output = []
    for d in destinations:
        output.append({
            'id': d.id,
            'city': d.city,
            'country': d.country,
            'region': d.region,
            'budget_level': d.budget_level,
            'culture': d.culture,
            'adventure': d.adventure,
            'nature': d.nature,
            'beaches': d.beaches,
            'nightlife': d.nightlife,
            'cuisine': d.cuisine,
            'wellness': d.wellness,
            'urban': d.urban,
            'seclusion': d.seclusion,
        })
    return jsonify(output)


# GET a single destination by id
@app.route('/destinations/<id>', methods=['GET'])
def get_destination(id):
    dest = TravelData.query.get_or_404(id)
    return jsonify({
        'id': dest.id,
        'city': dest.city,
        'country': dest.country,
        'region': dest.region,
        'budget_level': dest.budget_level,
        'culture': dest.culture,
        'adventure': dest.adventure,
        'nature': dest.nature,
        'beaches': dest.beaches,
        'nightlife': dest.nightlife,
        'cuisine': dest.cuisine,
        'wellness': dest.wellness,
        'urban': dest.urban,
        'seclusion': dest.seclusion,
    })


# POST — add a new destination
@app.route('/destinations', methods=['POST'])
def add_destination():
    data = request.get_json()
    if not data or 'id' not in data or 'city' not in data or 'country' not in data:
        return jsonify({'error': 'id, city, and country are required'}), 400

    if TravelData.query.get(data['id']):
        return jsonify({'error': 'A destination with that id already exists'}), 409

    new_dest = TravelData(
        id=data['id'],
        city=data['city'],
        country=data['country'],
        region=data.get('region'),
        budget_level=data.get('budget_level'),
        culture=data.get('culture', '0'),
        adventure=data.get('adventure', '0'),
        nature=data.get('nature', '0'),
        beaches=data.get('beaches', '0'),
        nightlife=data.get('nightlife', '0'),
        cuisine=data.get('cuisine', '0'),
        wellness=data.get('wellness', '0'),
        urban=data.get('urban', '0'),
        seclusion=data.get('seclusion', '0'),
    )
    db.session.add(new_dest)
    db.session.commit()
    return jsonify({'message': f"Destination '{data['city']}' added successfully!"}), 201


# PUT — update an existing destination
@app.route('/destinations/<id>', methods=['PUT'])
def update_destination(id):
    dest = TravelData.query.get_or_404(id)
    data = request.get_json()

    updatable_fields = [
        'city', 'country', 'region', 'budget_level',
        'culture', 'adventure', 'nature', 'beaches',
        'nightlife', 'cuisine', 'wellness', 'urban', 'seclusion',
    ]
    for field in updatable_fields:
        if field in data:
            setattr(dest, field, data[field])

    db.session.commit()
    return jsonify({'message': f"Destination '{dest.city}' updated successfully!"})


# DELETE — remove a destination
@app.route('/destinations/<id>', methods=['DELETE'])
def delete_destination(id):
    dest = TravelData.query.get_or_404(id)
    city_name = dest.city
    db.session.delete(dest)
    db.session.commit()
    return jsonify({'message': f"Destination '{city_name}' deleted successfully!"})


if __name__ == '__main__':
    app.run(debug=True)
