import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from config import DATABASE_CONFIG  # Import the database configuration
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')  # Use environment variable

# Define the specific admin password
ADMIN_PASSWORD = 'crypto'  # Replace with your actual admin password

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host=DATABASE_CONFIG['host'],
        user=DATABASE_CONFIG['user'],
        password=DATABASE_CONFIG['password'],
        database=DATABASE_CONFIG['database']
    )
# ****************************************************************************************************************** returns
# Route for the root URL
@app.route('/')
def index():
    return redirect(url_for('home'))  # Redirect to home page

# Route for the home page
@app.route('/home')
def home():
    user_id = session.get('user_id')  # Retrieve user ID from session
    return render_template('index.html', user_id=user_id)
# ****************************************************************************************************************** log in
# Route for logging in
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, password, role FROM User WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user:
            stored_user_id, stored_password, role = user
            if check_password_hash(stored_password, password):
                # Store user information in session
                session['user_id'] = stored_user_id
                session['email'] = email
                session['role'] = role
                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid password!', 'error')
        else:
            flash('Email not found!', 'error')
        
        cursor.close()
        conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# ******************************************************************************************************************  wallet
# Route to view the wallet
@app.route('/view_wallet')
def view_wallet():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to view your wallet.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_role = session.get('role')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if user_role == 'admin':
            # For admin, join with User table to show user information
            cursor.execute('''
                SELECT w.*, u.name as user_name, u.email as user_email 
                FROM Wallet w 
                JOIN User u ON w.user_id = u.user_id
            ''')
        else:
            # Regular users can only see their own wallets
            cursor.execute('SELECT * FROM Wallet WHERE user_id = %s', (user_id,))
        
        wallets = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading wallets: {str(e)}", 'error')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()

    return render_template('wallets.html', wallets=wallets, user_role=user_role)




@app.route('/create_wallet', methods=['GET', 'POST'])
def create_wallet():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to create a wallet.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']  # Get the user ID from session
        initial_balance = float(request.form['initial_balance'])  # Retrieve initial balance from the form

        # Validation for positive balance and greater than 100
        if initial_balance <= 100:
            flash('Initial balance must be greater than 100.', 'error')
            return redirect(url_for('create_wallet'))  # Redirect back to the same page

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Call the stored procedure to create a wallet
            cursor.callproc('CreateWallet', [user_id, initial_balance])
            conn.commit()
            flash('Wallet created successfully with initial balance!', 'success')  # Flash success message
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('view_wallet'))  # Redirect to wallet view after successful creation

    return render_template('create_wallet.html')


# Route to delete a wallet
@app.route('/delete_wallet/<int:wallet_id>', methods=['POST'])
def delete_wallet(wallet_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to delete a wallet.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']  # Get the user ID from session

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verify that the wallet belongs to the logged-in user
        cursor.execute(
            'SELECT * FROM Wallet WHERE wallet_id = %s AND user_id = %s',
            (wallet_id, user_id)
        )
        wallet = cursor.fetchone()

        if wallet is None:
            flash('Wallet not found or you do not have permission to delete it.', 'error')
            return redirect(url_for('view_wallet'))

        # Delete the wallet
        cursor.execute(
            'DELETE FROM Wallet WHERE wallet_id = %s AND user_id = %s',
            (wallet_id, user_id)
        )
        conn.commit()
        flash('Wallet deleted successfully!', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_wallet'))
# ******************************************************************************************************************create user
# Route for creating a new user
@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        print(request.form)  # Debug: print the form data

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # Get the role from form

        # If the role is 'admin', ensure the correct admin password is provided
        if role == 'admin':
            admin_password = request.form.get('admin_password')  # Get admin password from form
            if admin_password != ADMIN_PASSWORD:  # Check against the predefined admin password
                flash('Incorrect admin password. User not created.', 'error')
                return redirect(url_for('create_user'))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if the email already exists
            cursor.execute('SELECT * FROM User WHERE email = %s', (email,))
            if cursor.fetchone() is not None:
                flash('Email already exists!', 'error')
                return redirect(url_for('create_user'))

            # Hash the password
            password_hash = generate_password_hash(password)
            cursor.execute('INSERT INTO User (name, email, password, role) VALUES (%s, %s, %s, %s)', (name, email, password_hash, role))
            conn.commit()
            flash('User created successfully!', 'success')
        except mysql.connector.Error as err:
            conn.rollback()  # Rollback on error
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('home'))

    return render_template('create_user.html')
# ****************************************************************************************************************** portfolio
# Route for creating a portfolio
@app.route('/create_portfolio', methods=['GET', 'POST'])
def create_portfolio():
    if request.method == 'POST':
        portfolio_name = request.form['portfolio_name']
        user_id = session['user_id']  # Assuming user_id is stored in session
        total_value = 0.00  # Set initial total value to 0

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO Portfolio (portfolio_name, total_value, user_id) VALUES (%s, %s, %s)',
                           (portfolio_name, total_value, user_id))
            conn.commit()
            flash('Portfolio created successfully!', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('view_portfolios'))

    return render_template('create_portfolio.html')


# Route for viewing portfolios
@app.route('/view_portfolios')
def view_portfolios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Update the query to calculate total value based on transaction types
    cursor.execute('''
        SELECT 
            p.portfolio_id, 
            p.portfolio_name,
            COALESCE(
                SUM(
                    CASE 
                        WHEN t.transaction_type = 'buy' THEN t.quantity * t.price_at_transaction
                        WHEN t.transaction_type = 'sell' THEN -(t.quantity * t.price_at_transaction)
                        ELSE 0
                    END
                ), 0
            ) as total_value
        FROM Portfolio p
        LEFT JOIN Transaction t ON p.portfolio_id = t.portfolio_id
        WHERE p.user_id = %s
        GROUP BY p.portfolio_id, p.portfolio_name
    ''', (session['user_id'],))
    
    portfolios = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('view_portfolios.html', portfolios=portfolios)

# Helper function to check if the user has permission to delete a portfolio
def user_has_permission_to_delete(portfolio_id):
    user_id = session.get('user_id')  # Get the user_id from the session
    if not user_id:  # Check if the user is logged in
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM Portfolio WHERE portfolio_id = %s', (portfolio_id,))
    owner_id = cursor.fetchone()  # Get the owner_id for the portfolio
    cursor.close()
    conn.close()
    
    if owner_id is not None:
        return owner_id[0] == user_id  # Return True if the logged-in user is the owner
    return False

# Delete portfolio
@app.route('/delete_portfolio/<int:portfolio_id>', methods=['POST'])
def delete_portfolio(portfolio_id):
    # Check if the user has permission to delete the portfolio
    if not user_has_permission_to_delete(portfolio_id):  # Check if the user is the owner
        flash('Access Denied: You do not have permission to delete this portfolio.', 'danger')
        return redirect(url_for('view_portfolios'))

    # Logic to delete the portfolio from the database
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute('DELETE FROM Portfolio WHERE portfolio_id = %s', (portfolio_id,))
        connection.commit()
        flash('Portfolio deleted successfully!', 'success')  # Show a success message
    except mysql.connector.Error as err:
        connection.rollback()
        flash(f'Error: {err}', 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('view_portfolios'))  # Redirect to view portfolios

# ****************************************************************************************************************** cryptocurrency

# Route for creating a new cryptocurrency, accessible only by admins
@app.route('/create_cryptocurrency', methods=['GET', 'POST'])
def create_cryptocurrency():
    # Check if user is logged in and has admin privileges
    user_role = session.get('role')  # Assume `role` is stored in the session when user logs in
    
    if user_role != 'admin':
        flash('Only admins can add cryptocurrencies.', 'error')
        return redirect(url_for('index'))  # Redirect to home or another accessible page for users
    
    if request.method == 'POST':
        name = request.form['name']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Call the stored procedure to create a cryptocurrency
            cursor.callproc('CreateCryptocurrency', [name])
            conn.commit()
            flash('Cryptocurrency created successfully!', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('view_cryptocurrencies'))

    return render_template('create_cryptocurrency.html')

# Route for viewing all cryptocurrencies
@app.route('/view_cryptocurrencies')
def view_cryptocurrencies():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Cryptocurrency')
    cryptocurrencies = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('view_cryptocurrencies.html', cryptocurrencies=cryptocurrencies)

# ****************************************************************************************************************** transaction
# Route for creating a transaction
@app.route('/create_transaction', methods=['GET', 'POST'])
def create_transaction():
    if request.method == 'POST':
        try:
            user_id = session['user_id']
            portfolio_id = request.form['portfolio_id']
            crypto_id = request.form['crypto_id']
            quantity = float(request.form['quantity'])
            transaction_type = request.form['transaction_type']
            price_at_transaction = float(request.form['price_at_transaction'])
            wallet_id = request.form['wallet_id']
            
            # Calculate total value for this transaction
            total_value = quantity * price_at_transaction
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Start transaction
            cursor.execute("START TRANSACTION")
            
            # Check wallet balance for 'buy' transactions
            if transaction_type.lower() == 'buy':
                cursor.execute('SELECT balance FROM Wallet WHERE wallet_id = %s AND user_id = %s', 
                             (wallet_id, user_id))
                wallet = cursor.fetchone()
                if not wallet or wallet[0] < total_value:
                    cursor.close()
                    conn.close()
                    flash('Insufficient funds in wallet', 'error')
                    # Fetch data needed for the form
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT portfolio_id, portfolio_name FROM Portfolio WHERE user_id = %s', (user_id,))
                    portfolios = cursor.fetchall()
                    cursor.execute('SELECT crypto_id, name FROM Cryptocurrency')
                    cryptocurrencies = cursor.fetchall()
                    cursor.execute('SELECT wallet_id, balance FROM Wallet WHERE user_id = %s', (user_id,))
                    wallets = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    return render_template('create_transaction.html', 
                                        portfolios=portfolios, 
                                        cryptocurrencies=cryptocurrencies,
                                        wallets=wallets)
                
                # Deduct from wallet
                cursor.execute('''
                    UPDATE Wallet 
                    SET balance = balance - %s 
                    WHERE wallet_id = %s AND user_id = %s
                ''', (total_value, wallet_id, user_id))
            
            elif transaction_type.lower() == 'sell':
                # Add to wallet
                cursor.execute('''
                    UPDATE Wallet 
                    SET balance = balance + %s 
                    WHERE wallet_id = %s AND user_id = %s
                ''', (total_value, wallet_id, user_id))
            
            # Insert the transaction
            cursor.execute('''
                INSERT INTO Transaction 
                (user_id, portfolio_id, crypto_id, quantity, transaction_type, 
                price_at_transaction, total_value, wallet_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (user_id, portfolio_id, crypto_id, quantity, transaction_type, 
                price_at_transaction, total_value, wallet_id))
            
            # Update portfolio total value
            if transaction_type.lower() == 'buy':
                cursor.execute('''
                    UPDATE Portfolio 
                    SET total_value = total_value + %s 
                    WHERE portfolio_id = %s
                ''', (total_value, portfolio_id))
            elif transaction_type.lower() == 'sell':
                cursor.execute('''
                    UPDATE Portfolio 
                    SET total_value = total_value - %s 
                    WHERE portfolio_id = %s
                ''', (total_value, portfolio_id))
            
            conn.commit()
            flash('Transaction created successfully!', 'success')
            
        except ValueError:
            flash('Please enter valid numbers for quantity and price', 'error')
            return redirect(url_for('create_transaction'))
        except Exception as err:
            conn.rollback()
            flash(f'Error: {err}', 'error')
            return redirect(url_for('create_transaction'))
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('view_transactions'))

    # GET request to show the transaction creation form
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch portfolios, cryptocurrencies, and wallets for the form
    cursor.execute('SELECT portfolio_id, portfolio_name FROM Portfolio WHERE user_id = %s', (session['user_id'],))
    portfolios = cursor.fetchall()
    
    cursor.execute('SELECT crypto_id, name FROM Cryptocurrency')
    cryptocurrencies = cursor.fetchall()
    
    cursor.execute('SELECT wallet_id, balance FROM Wallet WHERE user_id = %s', (session['user_id'],))
    wallets = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('create_transaction.html', 
                         portfolios=portfolios, 
                         cryptocurrencies=cryptocurrencies,
                         wallets=wallets)


# Route for viewing transactions
@app.route('/view_transactions')
def view_transactions():
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Updated query without amount field
    cursor.execute('''
        SELECT t.transaction_id, p.portfolio_name, c.name AS crypto_name, t.quantity, 
               t.transaction_type, t.price_at_transaction, t.total_value, 
               t.time_of_transaction
        FROM Transaction t
        JOIN Portfolio p ON t.portfolio_id = p.portfolio_id
        JOIN Cryptocurrency c ON t.crypto_id = c.crypto_id
        WHERE t.user_id = %s
    ''', (user_id,))
    transactions = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('view_transactions.html', transactions=transactions)


# ****************************************************************************************************************** market data

import time

# Global variables to manage API calls
last_api_call_time = None
api_call_interval = 60  # 1 minute

def can_call_api():
    global last_api_call_time
    if last_api_call_time is None or time.time() - last_api_call_time > api_call_interval:
        last_api_call_time = time.time()
        return True
    return False


# Function to fetch market data
def fetch_market_data():
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,litecoin,dogecoin,ripple&vs_currencies=usd'
    try:
        response = requests.get(url)
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# Route to update market data

@app.route('/update_market_data')
def update_market_data():
    market_data = fetch_market_data()
    if market_data:
        conn = get_db_connection()
        cursor = conn.cursor()
        for crypto_name, price_data in market_data.items():
            price = price_data['usd']
            cursor.execute('SELECT crypto_id FROM Cryptocurrency WHERE name = %s', (crypto_name,))
            crypto_id = cursor.fetchone()
            if crypto_id:
                cursor.execute('INSERT INTO MarketData (crypto_id, price) VALUES (%s, %s)', (crypto_id[0], price))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Market data updated successfully!', 'success')
    else:
        flash('Failed to fetch market data.', 'error')
    return redirect(url_for('index'))


# Route to view market data
@app.route('/view_market_data')
def view_market_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.name, m.price, m.timestamp
            FROM MarketData m
            JOIN Cryptocurrency c ON m.crypto_id = c.crypto_id
            ORDER BY m.timestamp DESC
        ''')
        market_data = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while fetching market data.", 500

    return render_template('view_market_data.html', market_data=market_data)



# ****************************************************************************************************************** 
# Route to view users
@app.route('/users')
def view_users():
    # Check if the user is logged in and is an admin
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, name, email, role FROM User')
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('view_users.html', users=users)
    else:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

# Route for editing users
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    # Check if the user is logged in and is an admin
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            role = request.form['role']

            cursor.execute('UPDATE User SET name = %s, email = %s, role = %s WHERE user_id = %s', (name, email, role, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash('User updated successfully!', 'success')
            return redirect(url_for('view_users'))

        # Fetch the user details for editing
        cursor.execute('SELECT name, email, role FROM User WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user)
    else:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

# Route for deleting

# Route for deleting users
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' in session and session['role'] == 'admin':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Delete from Transaction first (it has foreign keys to both wallet and portfolio)
            cursor.execute('DELETE FROM Transaction WHERE user_id = %s OR wallet_id IN (SELECT wallet_id FROM Wallet WHERE user_id = %s)', (user_id, user_id))
            
            # Delete from MarketData if there are any user-specific entries
            cursor.execute('DELETE FROM MarketData WHERE crypto_id IN (SELECT crypto_id FROM Transaction WHERE user_id = %s)', (user_id,))
            
            # Delete from Watchlist
            cursor.execute('DELETE FROM Watchlist WHERE user_id = %s', (user_id,))
            
            # Delete from Portfolio
            cursor.execute('DELETE FROM Portfolio WHERE user_id = %s', (user_id,))
            
            # Delete from Wallet
            cursor.execute('DELETE FROM Wallet WHERE user_id = %s', (user_id,))
            
            # Finally delete the user
            cursor.execute('DELETE FROM User WHERE user_id = %s', (user_id,))
            
            conn.commit()
            flash('User deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed to delete user: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Access denied!', 'error')

    return redirect(url_for('view_users'))

@app.route('/watchlist')
def watchlist():
    if 'user_id' not in session:
        flash('Please log in to view your watchlist.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get watchlist items with current market data
    cursor.execute('''
        SELECT w.preference_id, c.name as crypto_name, 
               m.price as current_price, m.timestamp as last_updated
        FROM Watchlist w
        JOIN Cryptocurrency c ON w.preferred_currency = c.name
        LEFT JOIN (
            SELECT m1.*
            FROM MarketData m1
            INNER JOIN (
                SELECT crypto_id, MAX(timestamp) as max_timestamp
                FROM MarketData
                GROUP BY crypto_id
            ) m2 ON m1.crypto_id = m2.crypto_id AND m1.timestamp = m2.max_timestamp
        ) m ON c.crypto_id = m.crypto_id
        WHERE w.user_id = %s
    ''', (session['user_id'],))
    
    watchlist_items = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('watchlist.html', watchlist_items=watchlist_items)

@app.route('/add_to_watchlist/<string:crypto_name>', methods=['POST'])
def add_to_watchlist(crypto_name):
    if 'user_id' not in session:
        flash('Please log in to add to watchlist.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if already in watchlist
        cursor.execute('SELECT * FROM Watchlist WHERE user_id = %s AND preferred_currency = %s',
                      (session['user_id'], crypto_name))
        if cursor.fetchone():
            flash('This cryptocurrency is already in your watchlist!', 'error')
        else:
            cursor.execute('INSERT INTO Watchlist (user_id, preferred_currency) VALUES (%s, %s)',
                         (session['user_id'], crypto_name))
            conn.commit()
            flash('Added to watchlist successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('view_cryptocurrencies'))

@app.route('/remove_from_watchlist/<int:preference_id>', methods=['POST'])
def remove_from_watchlist(preference_id):
    if 'user_id' not in session:
        flash('Please log in to remove from watchlist.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM Watchlist WHERE preference_id = %s AND user_id = %s',
                      (preference_id, session['user_id']))
        conn.commit()
        flash('Removed from watchlist successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('watchlist'))

# Add new route for adding amount to wallet
@app.route('/add_amount/<int:wallet_id>', methods=['POST'])
def add_amount(wallet_id):
    # Ensure user is logged in
    if 'user_id' not in session:
        flash('Please log in to add amount to your wallet.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_role = session.get('role')  # Get user's role
    
    try:
        amount = float(request.form['amount'])
        if amount <= 0:
            flash('Please enter a positive amount.', 'error')
            return redirect(url_for('view_wallet'))
            
    except ValueError:
        flash('Invalid amount format.', 'error')
        return redirect(url_for('view_wallet'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if wallet exists
        if user_role == 'admin':
            cursor.execute('SELECT * FROM Wallet WHERE wallet_id = %s', (wallet_id,))
        else:
            cursor.execute('SELECT * FROM Wallet WHERE wallet_id = %s AND user_id = %s', 
                         (wallet_id, user_id))
        
        wallet = cursor.fetchone()
        
        if not wallet:
            flash('Wallet not found or you do not have permission to modify it.', 'error')
            return redirect(url_for('view_wallet'))

        # Call the stored procedure to add amount
        cursor.callproc('AddAmountToWallet', [wallet_id, amount])
        conn.commit()
        flash(f'Successfully added ${amount:.2f} to the wallet!', 'success')
        
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Database Error: {err}', 'error')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_wallet'))

@app.route('/get_crypto_price/<crypto_name>')
def get_crypto_price(crypto_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the most recent price for the cryptocurrency
        cursor.execute('''
            SELECT m.price 
            FROM MarketData m
            JOIN Cryptocurrency c ON m.crypto_id = c.crypto_id
            WHERE c.name = %s
            ORDER BY m.timestamp DESC
            LIMIT 1
        ''', (crypto_name,))
        
        result = cursor.fetchone()
        if result:
            return jsonify({'price': result['price']})
        else:
            return jsonify({'error': 'Price not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/dashboard')
def dashboard():
    return redirect(url_for('home'))  # Redirect to home or another existing route

if __name__ == '__main__':
    app.run(debug=True)