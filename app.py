import psycopg2
from config import db_name, user, host, port, password
from flask import Flask, request, jsonify

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
    print("--- Успешное подключение к БД!+-")
    cursor = connection.cursor()

except Exception as _ex:
    print("--- Ошибка подключения к БД: ", _ex)

@app.route('/users', methods=['POST', 'DELETE'])
def users():
    if request.method == "POST":
        login = request.json.get('login')
        name = request.json.get('name')
        email = request.json.get('email')
        phone = request.json.get('phone')
        address = request.json.get('address')
        password = request.json.get('password')

        if not all([login, name, email, phone, address, password]):
            return jsonify({'error': 'Не все обязательные поля заполнены (login, name, email, phone, address, password)'}), 400

        cursor.execute("SELECT login FROM sellers WHERE login = %s", (login,))
        if cursor.fetchone():
            return jsonify({'error': 'Пользователь с таким login уже существует'}), 400

        cursor.execute("""
            INSERT INTO sellers (login, name, email, phone, address, password) 
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING sellerID;
        """, (login, name, email, phone, address, password))

        new_seller_id = cursor.fetchone()[0]
        connection.commit()

        return jsonify({
            'message': 'Пользователь успешно добавлен',
            'sellerID': new_seller_id
        }), 201
    if request.method == 'DELETE':
        login = request.json.get('login')
        password = request.json.get('password')

        if not login or not password:
            return jsonify({'error': 'Необходимо указать login и password'}), 400

        cursor.execute("SELECT sellerID FROM sellers WHERE login = %s AND password = %s", (login, password))
        user = cursor.fetchone()

        if user:
            cursor.execute("DELETE FROM sellers WHERE login = %s", (login,))
            connection.commit()
            return jsonify({'message': 'Пользователь успешно удален'}), 200
        else:
            return jsonify({'error': 'Неверный login или password'}), 404

@app.route('/car_area', methods=['GET', 'POST'])
def cars():
    if request.method == "GET":
        cursor.execute("""
        SELECT cb.name AS brand, cm.name AS model, co.name AS color, ca.car_year, ca.price, ca.car_info, 
            ca.photo, s.name AS seller_name, s.phone AS seller_phone, s.address AS seller_address
        FROM car_ads ca JOIN car_model cm ON ca.model_id = cm.id JOIN car_brand cb ON cm.brand_id = cb.id
            JOIN colors co ON ca.color_id = co.color_id JOIN sellers s ON ca.seller_id = s.sellerID
        """)
        cars_list = cursor.fetchall()
        return jsonify({
            'Список авто': cars_list,
            'метод': request.method
        })
    if request.method == "POST":
        login = request.json.get('login')
        password = request.json.get('password')
        model_id = request.json.get('model_id')
        color_id = request.json.get('color_id')
        car_year = request.json.get('car_year')
        price = request.json.get('price')
        car_info = request.json.get('car_info')
        photo = request.json.get('photo')

        cursor.execute("""
            SELECT sellerID FROM sellers
            WHERE login = %s AND password = %s
            """, (login, password))
        seller = cursor.fetchone()

        if seller is None:
            return jsonify({'error': 'Неправильный логин или пароль'}), 400

        seller_id = seller[0]
        cursor.execute("""
            INSERT INTO car_ads (seller_id, model_id, color_id, car_year, price, car_info, photo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """, (seller_id, model_id, color_id, car_year, price, car_info, photo))
        new_ad_id = cursor.fetchone()[0]
        connection.commit()

        return jsonify({
            'message': 'Объявление успешно добавлено',
            'id нового объявления': new_ad_id
        }), 201


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
    app.run(debug=True)