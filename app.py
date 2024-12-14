from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired
import yfinance as yf
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

app = Flask(__name__)
'''Secret key is needed to keep the client-side sessions secure. You can generate some random key as below:
import os
os.urandom(24)
'\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'
Just take that key and copy/paste it into your config file
SECRET_KEY = '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'
'''
app.config['SECRET_KEY'] = 'test secret key for sanS'

# Database connection string
'''DATABASE_URL = "mssql+pyodbc://OURPC/Projects?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute("SELECT 1 AS test")
        print("Connection successful:", result.fetchall())
except Exception as e:
    print("Connection failed:", e)'''


# Aroon Indicator Calculation
def calculate_aroon(data, window=25):
    # Ensure there are enough data points
    if len(data) < window:
        raise ValueError(f"Not enough data to calculate Aroon. Need at least {window} data points.")

    # Predefine arrays to store results
    aroon_up = []
    aroon_down = []

    for i in range(len(data) - window + 1):
        # Select the rolling window data
        window_data = data.iloc[i:i + window]

        # Find the position (relative to the start of the window) of the max and min
        high_position = window_data['High'].values.argmax()  # Relative position within the window
        low_position = window_data['Low'].values.argmin()   # Relative position within the window

        # Calculate Aroon values
        aroon_up_value = 100 * (window - high_position) / window
        aroon_down_value = 100 * (window - low_position) / window

        aroon_up.append(aroon_up_value)
        aroon_down.append(aroon_down_value)

    # Fill the first 'window - 1' values with NaN for consistency
    aroon_up = [None] * (window - 1) + aroon_up
    aroon_down = [None] * (window - 1) + aroon_down

    # Convert to pandas Series
    return pd.Series(aroon_up, index=data.index), pd.Series(aroon_down, index=data.index)



# Form Class
class StockForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Submit')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = StockForm()
    if form.validate_on_submit():
        symbol = form.symbol.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        return redirect(url_for('plot_aroon', symbol=symbol, start_date=start_date, end_date=end_date))
    return render_template('index.html', form=form)
    '''if request.method == 'POST':
        symbol = request.form['symbol']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        try:
            # Fetch data using yfinance
            data = yf.download(symbol, start=start_date, end=end_date)

            # Check if data is empty
            if data.empty:
                raise ValueError(f"No data found for symbol '{symbol}'.")

            # Process data and render the plot
            return render_template('plot.html', symbol=symbol, start_date=start_date, end_date=end_date)

        except Exception as e:
            # Pass error message to index.html
            error_message = str(e)
            return render_template('index.html', error_message=error_message)

    return render_template('index.html')'''

@app.route('/plot/<symbol>/<start_date>/<end_date>')
def plot_aroon(symbol, start_date, end_date):
    # Fetch stock data
    data = yf.download(symbol, start=start_date, end=end_date)
    
    # Check if data is empty
    if data.empty:
       raise ValueError(f"No data found for symbol '{symbol}'.")
    '''if data.empty or 'High' not in data.columns or 'Low' not in data.columns:
        flash("No data found for the given stock symbol or date range.")
        return redirect(url_for('index'))'''
    
    aroon_up, aroon_down = calculate_aroon(data, window=10)

    # Plot Aroon Indicator
    plt.figure(figsize=(10, 6))
    plt.plot(data.index, aroon_up, label='Aroon Up', color='green')
    plt.plot(data.index, aroon_down, label='Aroon Down', color='red')
    plt.title(f'Aroon Indicator for {symbol}')
    plt.xlabel('Date')
    plt.ylabel('Aroon Value')
    plt.legend()
    plt.grid()

    # Save plot as a temporary image
    plot_file = f'static/aroon_{symbol}.png'
    plt.savefig(plot_file)
    plt.close()

    # Save data to SQL Server
    aroon_data = pd.DataFrame({'Date': data.index, 'Aroon Up': aroon_up, 'Aroon Down': aroon_down})
    #aroon_data.to_sql('aroon_data', engine, if_exists='append', index=False)
    
    return render_template('plot.html', symbol=symbol, plot_file=plot_file)

if __name__ == '__main__':
    app.run(debug=True)
