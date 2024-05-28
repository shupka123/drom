import requests
from config import db_name, user, host, port, password
from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

try:
    connection = psycopg2.connect(
        host=host,
        database=db_name,
        port=port,
        user=user,
        password=password
    )
    print("--- Успешное подключение к БД!!!!")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT cb.name AS brand, cm.name AS model, co.name AS color, ca.car_year, ca.price, ca.car_info, 
            ca.photo, s.name AS seller_name, s.phone AS seller_phone, s.address AS seller_address
        FROM car_ads ca JOIN car_model cm ON ca.model_id = cm.id JOIN car_brand cb ON cm.brand_id = cb.id
            JOIN colors co ON ca.color_id = co.color_id JOIN sellers s ON ca.seller_id = s.sellerID
        """)
    print(cursor.fetchall())
    print("Vse okay!!!!!")

except Exception as _ex:
    print("--- Ошибка подключения к БД: ", _ex)
@app.route('/users', methods=['POST', 'DELETE'])
def users():
    if request.method == 'POST':
        response = requests.post('http://172.21.0.4:5000/users')
        return jsonify(response.json()), response.status_code
    elif request.method == 'DELETE':
        response = requests.delete('http://172.21.0.4:5000/users')
        return jsonify(response.json()), response.status_code

@app.route('/car_area', methods=['GET', 'POST'])
def cars():
    if request.method == 'GET':
        response = requests.get('http://172.21.0.5:5000/car_area')
        return jsonify(response.json()), response.status_code
    elif request.method == 'POST':
        response = requests.post('http://172.21.0.5:5000/car_area')
        return jsonify(response.json()), response.status_code

@app.route('/car_area/<int:car_id>', methods=['GET', 'PUT', 'DELETE'])
def car(car_id):
    if request.method == "GET":
        cursor.execute("""
        SELECT cb.name AS brand, cm.name AS model, co.name AS color, ca.car_year, ca.price, ca.car_info, 
            ca.photo, s.name AS seller_name, s.phone AS seller_phone, s.address AS seller_address
        FROM car_ads ca JOIN car_model cm ON ca.model_id = cm.id JOIN car_brand cb ON cm.brand_id = cb.id
            JOIN colors co ON ca.color_id = co.color_id JOIN sellers s ON ca.seller_id = s.sellerID
        WHERE ca.id = %s
        """, (car_id,))
        car = cursor.fetchone()
        if car:
            return jsonify({
                'id': car_id,
                'данные об авто': {
                    'бренд': car[0],
                    'модель': car[1],
                    'цвет': car[2],
                    'год выпуска': car[3],
                    'цена': car[4],
                    'информация об авто': car[5],
                    'фото': car[6],
                    'имя продавца': car[7],
                    'телефон продавца': car[8],
                    'адрес продавца': car[9]
                },
                'метод': request.method
            })
        else:
            return jsonify({'сообщение': 'Автомобиль с id {} не найден'.format(car_id)}), 404
    elif request.method == "PUT":
        data = request.json
        login = data.get('login')
        password = data.get('password')
        model_id = data.get('model_id')
        color_id = data.get('color_id')
        car_year = data.get('car_year')
        price = data.get('price')
        car_info = data.get('car_info', '')
        photo = data.get('photo', '')

        cursor.execute("""
            SELECT sellerID FROM sellers
            WHERE login = %s AND password = %s
            """, (login, password))
        seller = cursor.fetchone()
        if not seller:
            return jsonify({'error': 'Неправильный логин или пароль'}), 400
        seller_id = seller[0]
        cursor.execute("""
            SELECT * FROM car_ads WHERE id = %s AND seller_id = %s
            """, (car_id, seller_id))
        ad = cursor.fetchone()
        if not ad:
            return jsonify(
                {'error': 'Объявление с id {} не принадлежит пользователю или не существует'.format(car_id)}), 404

        cursor.execute("""
            UPDATE car_ads
            SET model_id = %s, color_id = %s, car_year = %s, price = %s, car_info = %s, photo = %s
            WHERE id = %s AND seller_id = %s
            """, (model_id, color_id, car_year, price, car_info, photo, car_id, seller_id))
        connection.commit()

        return jsonify({'message': 'Объявление с id {} успешно обновлено'.format(car_id), 'метод': request.method})
    elif request.method == "DELETE":
        data = request.json
        login = data.get('login')
        password = data.get('password')

        cursor.execute("""
            SELECT sellerID FROM sellers
            WHERE login = %s AND password = %s
            """, (login, password))
        seller = cursor.fetchone()

        if not seller:
            return jsonify({'error': 'Неправильный логин или пароль'}), 400
        seller_id = seller[0]

        cursor.execute("""
            SELECT * FROM car_ads WHERE id = %s AND seller_id = %s
            """, (car_id, seller_id))
        ad = cursor.fetchone()

        if not ad:
            return jsonify(
                {'error': 'Объявление с id {} не принадлежит пользователю или не существует'.format(car_id)}), 404
        cursor.execute("""
            DELETE FROM car_ads WHERE id = %s AND seller_id = %s
            """, (car_id, seller_id))
        connection.commit()

        return jsonify({'message': 'Объявление с id {} успешно удалено'.format(car_id),
                        'метод': request.method})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
