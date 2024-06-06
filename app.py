from flask import Flask, request, jsonify, render_template, redirect, url_for, session,flash
import mysql.connector
import base64

app = Flask(__name__)
app.secret_key = '12345'

# Establish MySQL connection
try:
    con = mysql.connector.connect(host="localhost", user="root", password="root", database="mydatabase")
    print("Connection successful")
except mysql.connector.Error as e:
    print("Error:", e)


@app.route('/', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        data = request.form
        name = data['name']
        email = data['email']
        mobile = data['mobile']
        security_q1 = data['security_q1']
        security_q2 = data['security_q2']
        password = data['password']
        
        try:
            cursor = con.cursor()
            cursor.execute("INSERT INTO user_info (name, email, mobile, security_q1, security_q2, password) VALUES (%s, %s, %s, %s, %s, %s)",
                           (name, email, mobile, security_q1, security_q2, password))
            con.commit()
            cursor.close()
            
            return redirect(url_for('login_page'))
        except mysql.connector.Error as e:
            print("Error:", e)
            return jsonify({"error": str(e)}), 500
    
    # If request is a GET, access the registration 
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_info WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if user and user['password'] == password:
            session['user'] = user  # Store user data in session
            return redirect(url_for('profile'))
        else:
            message = 'Invalid email or password'
            if not user:
                message = 'Invalid email'
            elif user['password'] != password:
                message = 'Invalid password'
            return render_template('login.html', message=message, email=email, password=password)  # Pass email and password back to the template
    return render_template('login.html')


@app.route('/profile', methods=['GET'])
def profile():
    if 'user' in session:
        user = session['user']
        return render_template('profile.html', user=user)
    else:
        return redirect(url_for('login_page'))


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        security_q1 = request.form.get('security_q1')
        security_q2 = request.form.get('security_q2')
        security_q1_answer = request.form.get('security_q1_answer')
        security_q2_answer = request.form.get('security_q2_answer')
        new_password = request.form.get('new_password')
        
        
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_info WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
            
        if user:
            error_message = "" 
            
            if user['security_q1'] != security_q1_answer:
                error_message = "Security question 1 answer is incorrect. "
                
            if user['security_q2'] != security_q2_answer:
                error_message += "Security question 2 answer is incorrect. "


            if error_message.strip() == "Security question 1 answer is incorrect. Security question 2 answer is incorrect.":
                error_message = "Both security questions are incorrect."
                return render_template('reset_password.html', error_message=error_message)
            elif error_message:
                return render_template('reset_password.html', error_message=error_message)
            else:
                # Update the user's password
                cursor = con.cursor()
                cursor.execute("UPDATE user_info SET password = %s WHERE email = %s", (new_password, email))
                con.commit()
                cursor.close()

                return redirect(url_for('login_page'))
        else:
            return "User not found"

    elif request.method == 'GET':
        return render_template('reset_password.html', error_message=None)


@app.route('/users', methods=['GET'])
def get_users():
    try:
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_info")
        users = cursor.fetchall()
        cursor.close()
        return jsonify(users)
    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)})


@app.route('/concerts', methods=['GET'])
def concerts_page():
    try:
        cursor = con.cursor()
        cursor.execute("SELECT id, name, artistname, date, time, country, stadium_name, stadium_capacity, ticket_price, image_data FROM concert")
        concerts = cursor.fetchall()

        concert_data = []
        for concert in concerts:
            image_data = base64.b64encode(concert[9]).decode('utf-8') if concert[9] else None

            concert_data.append({
                "id": concert[0],  # Add the ID attribute to each concert dictionary
                "name": concert[1],
                "artistname": concert[2],
                "date": str(concert[3]),
                "time": str(concert[4]),
                "country": concert[5],
                "stadium_name": concert[6],
                "stadium_capacity": concert[7],
                "ticket_price": float(concert[8]),
                "image_data": image_data
            })

        return render_template('concerts.html', concerts=concert_data)
    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/book_concert/<int:concert_id>', methods=['GET', 'POST'])
def book_concert(concert_id):
    try:
        if 'user' not in session:
            return redirect(url_for('login_page'))  # Redirect user to login page if not logged in

        user_id = session['user']['user_id']  # Get user_id from session

        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM concert WHERE id = %s", (concert_id,))
        concert = cursor.fetchone()

        if not concert:
            return "Concert not found"

        if request.method == 'POST':
            num_tickets = int(request.form['num_tickets'])

            # Check if there are enough available tickets
            if num_tickets >= concert['available_tickets']:
                return "Not enough tickets available"
            
            # Update available tickets
            new_available_tickets = concert['available_tickets'] - num_tickets
            cursor.execute("UPDATE concert SET available_tickets = %s WHERE id = %s", (new_available_tickets, concert_id))

            # Insert booking details into bookings table
            cursor.execute("INSERT INTO bookings (user_id, concert_id, num_tickets, status) VALUES (%s, %s, %s, 'Booked')", (user_id, concert_id, num_tickets))
            con.commit()

            return redirect(url_for('booking_success', concert_id=concert_id, num_tickets=num_tickets))

        # Decode image data if it exists
        image_data = base64.b64encode(concert['image_data']).decode('utf-8') if concert['image_data'] else None

        # Pass image data to the template
        return render_template('booking.html', concert=concert, image_data=image_data)

    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/booking_success/<int:concert_id>/<int:num_tickets>', methods=['GET'])
def booking_success(concert_id, num_tickets):
    try:
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT name FROM concert WHERE id = %s", (concert_id,))
        concert = cursor.fetchone()

        if concert:
            return render_template('booking_success.html', concert=concert, num_tickets=num_tickets)
        else:
            return "Concert not found"

    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/booking_history', methods=['GET'])
def booking_history():
    try:
        # Check if user is logged in
        if 'user' not in session:
            return redirect(url_for('login_page'))

        # Get user_id from session
        user_id = session['user']['user_id']

        # Fetch booking history for the user
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT bookings.booking_id,bookings.status,concert.name, concert.date, concert.time, bookings.num_tickets FROM concert INNER JOIN bookings ON concert.id = bookings.concert_id WHERE bookings.user_id = %s", (user_id,))
        booking_history = cursor.fetchall()

        return render_template('booking_history.html', booking_history=booking_history)

    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/cancel_booking/<int:booking_id>', methods=['GET'])
def cancel_booking(booking_id):
    try:
        # Check if user is logged in
        if 'user' not in session:
            return redirect(url_for('login_page'))

        # Get user_id from session
        user_id = session['user']['user_id']

        # Check if the booking exists and belongs to the logged-in user
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE booking_id = %s AND user_id = %s", (booking_id, user_id))
        booking = cursor.fetchone()

        if not booking:
            return "Booking not found or does not belong to the logged-in user"

        # Get the number of tickets booked
        num_tickets = booking['num_tickets']
        concert_id = booking['concert_id']

        # Mark the booking as canceled
        cursor.execute("UPDATE bookings SET status = 'canceled' WHERE booking_id = %s", (booking_id,))
        con.commit()

        # Add the number of tickets back to the concert's available tickets
        cursor.execute("SELECT available_tickets FROM concert WHERE id = %s", (concert_id,))
        available_tickets = cursor.fetchone()['available_tickets']
        new_available_tickets = available_tickets + num_tickets
        cursor.execute("UPDATE concert SET available_tickets = %s WHERE id = %s", (new_available_tickets, concert_id))
        con.commit()

        return redirect(url_for('booking_history'))  # Redirect back to booking history

    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    except mysql.connector.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
