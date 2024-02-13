from flask import Flask, render_template, request, jsonify, redirect, url_for
from twilio.rest import Client as TwilioClient
import africastalking
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import threading
import time
from datetime import datetime, timedelta
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'd84dca72bbeb77c098733a6e7e61d564'
db = SQLAlchemy(app)
socketio = SocketIO(app)
migrate = Migrate(app, db)

class Meter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_number = db.Column(db.String(255), unique=True, nullable=False)
    remaining_kilowatts = db.Column(db.Float, default=0.0)
    daily_consumption = db.Column(db.Float, default=0.0)
    weekly_consumption = db.Column(db.Float, default=0.0)
    monthly_consumption = db.Column(db.Float, default=0.0)
    yearly_consumption = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    class ConsumptionTracker:
        def __init__(self):
            self.start_time_daily = time.time()  # Start time for daily reset

        def check_reset(self):
            current_time = time.time()
            # Check for daily reset
            if current_time - self.start_time_daily >= 24 * 60 * 60:  # 24 hours in seconds
                self.reset_daily()
                self.start_time_daily = current_time

        def reset_daily(self):
            self.daily_consumption = 0
            print("Daily consumption reset to zero.")

# Example usage:
meter_tracker_mapping = {}  # Dictionary to map meter number to ConsumptionTracker object

# Function to create or retrieve ConsumptionTracker object for a meter
def get_consumption_tracker(meter_number):
    if meter_number not in meter_tracker_mapping:
        meter_tracker_mapping[meter_number] = Meter.ConsumptionTracker()
    return meter_tracker_mapping[meter_number]

# Twilio credentials
twilio_account_sid = 'AC2c5e4a95e86bd5353f511d31c5015c6e'
twilio_auth_token = '0937d28d4eb8b2acd7334329304fcc70'
twilio_phone_number = '+12293982236'
twilio_client = TwilioClient(twilio_account_sid, twilio_auth_token)

# Africa's Talking credentials
africastalking.initialize(username='Ginnah', api_key='278bd4e919e723b95e8da22b54119a9c43d8feb7d9f1027897941a19f2e06930')
at_sms = africastalking.SMS

def send_twilio_confirmation_sms(user_phone_number, meter_number, amount=None):
    try:
        if amount is not None:
            message_body = f"Token purchase for {meter_number} is successful. You've bought {amount or '0'} kilowatts. Thank you!"
        else:
            message_body = f"Token purchase for {meter_number} is successful. Thank you!"

        twilio_client.messages.create(
            body=message_body,
            from_=twilio_phone_number,
            to=user_phone_number
        )

        print("Twilio SMS sent successfully")
        return True
    except Exception as e:
        print(f"Error sending Twilio SMS: {e}")
        return False

def send_at_confirmation_sms(user_phone_number, meter_number, amount=None):
    try:
        if amount is not None:
            message_body = f"Token purchase for {meter_number} is successful. You've bought {amount or '0'} kilowatts. Thank you!"
        else:
            message_body = f"Token purchase for {meter_number} is successful. Thank you!"

        # Replace 'YOUR_AT_SENDER_ID' with your Africa's Talking sender ID
        response = at_sms.send(message_body, [user_phone_number], sender_id='YOUR_AT_SENDER_ID')

        print(f"Africa's Talking SMS sent successfully. Response: {response}")
        return True
    except Exception as e:
        print(f"Error sending Africa's Talking SMS: {e}")
        return False

def update_remaining_kilowatts(meter_number, amount):
    with app.app_context():
        meter = Meter.query.filter_by(meter_number=meter_number).first()
        if meter:
            meter.remaining_kilowatts += amount
            db.session.commit()

def deduct_kilowatts(meter_number):
    while True:
        try:
            time.sleep(2)
            with app.app_context():
                meter = Meter.query.filter_by(meter_number=meter_number).first()
                if meter and meter.remaining_kilowatts is not None and meter.remaining_kilowatts >= 5:
                    consumption_tracker = get_consumption_tracker(meter_number)
                    consumption_tracker.check_reset()  # Check and reset daily consumption if necessary

                    meter.remaining_kilowatts = max(0, meter.remaining_kilowatts - 5)
                    meter.daily_consumption += 5  # Assuming 5 kilowatts deducted per day
                    db.session.commit()
                    print(f"Deducted 5 kilowatts from {meter_number}. Remaining: {meter.remaining_kilowatts}")

                    # Emit a SocketIO event to inform the client about the deduction
                    socketio.emit('update', {'meter_number': meter_number, 'remaining_kilowatts': meter.remaining_kilowatts}, namespace='/socket')

                    if meter.remaining_kilowatts <= 20.0:
                        send_low_balance_notification(meter_number)
                else:
                    print(f"Insufficient balance or meter not found.")
        except Exception as e:
            print(f"Exception in deduct_kilowatts: {e}")

def send_low_balance_notification(meter_number):
    user_phone_number = '+263715512554'

    print(f"Attempting to send low balance notification for {meter_number}.")

    send_twilio_confirmation_sms(user_phone_number, meter_number)
    print(f"Twilio SMS sent for {meter_number}.")

    send_at_confirmation_sms(user_phone_number, meter_number)
    print(f"Africa's Talking SMS sent for {meter_number}.")

    print(f"Low balance notification sent for {meter_number}.")


# its ignatiousdera coding baba
@app.route('/index')
def purchase_page():
    return render_template('index.html')

@app.route('/purchase', methods=['POST'])
def purchase():
    meter_number = request.form['meter_number']
    user_phone_number = request.form['phone']
    amount = float(request.form['amount'])

    # Create the meter in the database if it doesn't exist
    with app.app_context():
        meter = Meter.query.filter_by(meter_number=meter_number).first()
        if not meter:
            meter = Meter(meter_number=meter_number)
            db.session.add(meter)
            db.session.commit()

    # Update the remaining kilowatts
    update_remaining_kilowatts(meter_number, amount)

    # Deduct 5 kilowatts for each purchase
    threading.Thread(target=deduct_kilowatts, args=(meter_number,), daemon=True).start()

    # Send confirmation SMS using both Twilio and Africa's Talking
    if send_twilio_confirmation_sms(user_phone_number, meter_number, amount):
        if send_at_confirmation_sms(user_phone_number, meter_number, amount):
            # Redirect to the loading page first, then to the index page
            return redirect(url_for('loading'))
        else:
            return render_template('index.html', error_message="Failed to send Africa's Talking SMS")
    else:
        return render_template('index.html', error_message="Failed to send Twilio SMS")

@app.route('/loading')
def loading():
    return render_template('loading.html')


@app.route('/retrieve')
def retrieve():
    return render_template('retrieve.html')



@app.route('/get-remaining-kilowatts/<meter_number>')
def get_remaining_kilowatts_endpoint(meter_number):
    with app.app_context():
        meter = Meter.query.filter_by(meter_number=meter_number).first()
        if meter:
            remaining_kilowatts = meter.remaining_kilowatts
        else:
            remaining_kilowatts = None
    return jsonify({'remaining_kilowatts': remaining_kilowatts})




@app.route('/get-daily-consumption/<meter_number>')        
def get_daily_consumption(meter_number):
    with app.app_context():
        meter = Meter.query.filter_by(meter_number=meter_number).first()
        if meter:
            daily_consumption = meter.daily_consumption
        else:
            daily_consumption = None
    return jsonify({'daily_consumption': daily_consumption})



@app.route('/')
def index():
    amount = request.args.get('amount', default=None, type=float)
    return render_template('index.html', amount=amount)


@app.route('/consumption_summary', methods=['GET', 'POST'])
def consumption_summary():
    if request.method == 'POST':
        meter_number = request.form['meter_number']

        with app.app_context():
            # Fetch the meter from the database based on the provided meter number
            meter = Meter.query.filter_by(meter_number=meter_number).first()

            if meter:
                # Calculate the date range for daily, weekly, monthly, and yearly consumption
                today = datetime.today()
                one_week_ago = today - timedelta(days=7)
                one_month_ago = today - timedelta(days=30)
                one_year_ago = today - timedelta(days=365)

                # Fetch consumption data for the specified date ranges
                daily_consumption = meter.daily_consumption
                weekly_consumption = Meter.query.filter(Meter.meter_number == meter_number, Meter.updated_at >= one_week_ago).with_entities(db.func.sum(Meter.daily_consumption)).scalar() or 0
                monthly_consumption = Meter.query.filter(Meter.meter_number == meter_number, Meter.updated_at >= one_month_ago).with_entities(db.func.sum(Meter.daily_consumption)).scalar() or 0
                yearly_consumption = Meter.query.filter(Meter.meter_number == meter_number, Meter.updated_at >= one_year_ago).with_entities(db.func.sum(Meter.daily_consumption)).scalar() or 0

                return render_template('consumption_summary.html',
                                       meter_number=meter_number,
                                       daily_consumption=daily_consumption,
                                       weekly_consumption=weekly_consumption,
                                       monthly_consumption=monthly_consumption,
                                       yearly_consumption=yearly_consumption)
            else:
                error_message = "Meter not found in the database."
                return render_template('consumption_summary.html', error_message=error_message)

    return render_template('consumption_summary.html')




if __name__ == '__main__':
    meter_numbers = ['112233445566', '223344556677', '123456789101112', '000000000000', '334455667788']
    deduction_threads = [threading.Thread(target=deduct_kilowatts, args=(meter_number,)) for meter_number in meter_numbers]

    for thread in deduction_threads:
        thread.start()

    socketio.run(app, debug=True, host='0.0.0.0')
