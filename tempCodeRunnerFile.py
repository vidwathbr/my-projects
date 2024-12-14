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