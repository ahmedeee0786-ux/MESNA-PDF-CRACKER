import os
import time
import math
import datetime
import concurrent.futures
import pikepdf
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def check_chunk(args):
    filepath, chunk = args
    # Test each password in this chunk
    for pwd in chunk:
        try:
            # pikepdf uses the high-speed qpdf C++ library
            with pikepdf.open(filepath, password=pwd):
                pass
            return pwd
        except pikepdf.PasswordError:
            continue
        except Exception:
            # Catch other potential read errors if the file is truly broken
            continue
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/crack', methods=['POST'])
def crack_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    pdf_file = request.files['pdf_file']
    crack_mode = request.form.get('crack_mode', 'dict')
    passwords_text = request.form.get('passwords', '')
    
    try:
        pin_length = int(request.form.get('pin_length', 6))
    except ValueError:
        pin_length = 6
    
    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if crack_mode == 'dict' and not passwords_text.strip():
        return jsonify({'error': 'No passwords provided for the dictionary attack'}), 400

    filename = secure_filename(pdf_file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    pdf_file.save(filepath)
    
    try:
        # First check if the file is actually encrypted
        try:
            with pikepdf.open(filepath):
                os.remove(filepath)
                return jsonify({'success': False, 'message': 'This PDF is not protected by a password! It is already unlocked.'})
        except pikepdf.PasswordError:
            pass # It is encrypted, proceed!

        # Prepare the list of passwords to try
        if crack_mode == 'numeric':
            passwords = [f"{i:0{pin_length}d}" for i in range(10**pin_length)]
        elif crack_mode == 'dob':
            start_date = datetime.date(1900, 1, 1)
            end_date = datetime.date(2027, 1, 1)
            delta = datetime.timedelta(days=1)
            passwords = []
            while start_date < end_date:
                # Add multiple common formats
                passwords.append(start_date.strftime("%d%m%Y"))
                passwords.append(start_date.strftime("%m%d%Y"))
                passwords.append(start_date.strftime("%Y%m%d"))
                passwords.append(start_date.strftime("%d%m%y")) # shorter formats
                passwords.append(start_date.strftime("%m%d%y"))
                start_date += delta
            # Remove duplicates just in case
            passwords = list(dict.fromkeys(passwords))
        else:
            passwords = [p.strip() for p in passwords_text.split('\n') if p.strip()]

        # Split the passwords into smaller chunks
        num_cores = max(1, (os.cpu_count() or 4) - 1) # Keep 1 core free for OS/Flask
        chunk_size = 5000 
        chunks = [passwords[i:i + chunk_size] for i in range(0, len(passwords), chunk_size)]
        
        args_list = [(filepath, c) for c in chunks]

        start_time = time.time()
        found_password = None
        attempts_count = 0

        # Execute chunks across multiple CPU cores
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
            future_to_chunk = {executor.submit(check_chunk, arg): arg for arg in args_list}
            for future in concurrent.futures.as_completed(future_to_chunk):
                attempts_count += len(future_to_chunk[future][1])
                res = future.result()
                if res is not None:
                    found_password = res
                    break
                
        elapsed = time.time() - start_time
        
        # Save Unlocked PDF if found
        unlocked_url = None
        if found_password:
            unlocked_filename = f"unlocked_{filename}"
            unlocked_path = os.path.join(app.config['UPLOAD_FOLDER'], unlocked_filename)
            try:
                with pikepdf.open(filepath, password=found_password) as pdf:
                    pdf.save(unlocked_path)
                unlocked_url = f"/download/{unlocked_filename}"
            except Exception as e:
                print(f"Failed to save unlocked PDF: {e}")

        # Cleanup original
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

        if found_password:
            return jsonify({
                'success': True,
                'password': found_password,
                'unlocked_url': unlocked_url,
                'time_taken': f"{elapsed:.2f}s",
                'attempts': attempts_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Password not found in the selected range or dictionary.',
                'time_taken': f"{elapsed:.2f}s",
                'attempts': attempts_count
            })

    except Exception as e:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Important for Windows multiprocessing
    app.run(host='0.0.0.0', debug=True, port=5000)
