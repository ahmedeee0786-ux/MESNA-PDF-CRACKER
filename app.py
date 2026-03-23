import os
import time
import math
import datetime
import concurrent.futures
import pikepdf
import io
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def check_chunk(args):
    pdf_bytes, chunk = args
    # Test each password in this chunk
    for pwd in chunk:
        try:
            # Use io.BytesIO to open PDF from memory (avoiding disk I/O)
            with pikepdf.open(io.BytesIO(pdf_bytes), password=pwd):
                pass
            return pwd
        except (pikepdf.PasswordError, pikepdf.PdfError):
            continue
        except Exception:
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

        # Prepare the list of passwords to try (using generators for large sets)
        if crack_mode == 'numeric':
            passwords = (f"{i:0{pin_length}d}" for i in range(10**pin_length))
            total_passwords = 10**pin_length
        elif crack_mode == 'dob':
            start_date = datetime.date(1900, 1, 1)
            end_date = datetime.date(2027, 1, 1)
            delta = datetime.timedelta(days=1)
            
            def dob_generator():
                curr_date = start_date
                seen = set()
                while curr_date < end_date:
                    formats = ["%d%m%Y", "%m%d%Y", "%Y%m%d", "%d%m%y", "%m%d%y"]
                    for fmt in formats:
                        pwd = curr_date.strftime(fmt)
                        if pwd not in seen:
                            seen.add(pwd)
                            yield pwd
                    curr_date += delta
            
            passwords = dob_generator()
            # Approximate count for chunking
            total_passwords = (end_date - start_date).days * 5
        else:
            p_list = [p.strip() for p in passwords_text.split('\n') if p.strip()]
            passwords = iter(p_list)
            total_passwords = len(p_list)

        # Read PDF into memory once
        with open(filepath, 'rb') as f:
            pdf_bytes = f.read()

        # Dynamic chunk size based on total passwords and cores
        num_cores = max(1, (os.cpu_count() or 4) - 1)
        if total_passwords > 1000000:
            chunk_size = 10000
        elif total_passwords > 100000:
            chunk_size = 5000
        else:
            chunk_size = 2000

        # Helper to yield chunks from a generator
        def chunked_iterable(iterable, size):
            it = iter(iterable)
            while True:
                chunk = []
                try:
                    for _ in range(size):
                        chunk.append(next(it))
                    yield chunk
                except StopIteration:
                    if chunk:
                        yield chunk
                    break

        chunks = chunked_iterable(passwords, chunk_size)
        
        start_time = time.time()
        found_password = None
        attempts_count = 0

        # Execute chunks across multiple CPU cores
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
            # We use a set of futures and wait for completion/found password
            active_futures = set()
            
            # Submit initial batch
            for _ in range(num_cores * 2):
                try:
                    chunk = next(chunks)
                    active_futures.add(executor.submit(check_chunk, (pdf_bytes, chunk)))
                except StopIteration:
                    break
            
            while active_futures:
                done, active_futures = concurrent.futures.wait(
                    active_futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for future in done:
                    res = future.result()
                    if res is not None:
                        found_password = res
                        # Cancel remaining futures if supported
                        for f in active_futures:
                            f.cancel()
                        active_futures = set()
                        break
                    
                    # Submit next chunk if more available
                    try:
                        next_chunk = next(chunks)
                        attempts_count += chunk_size
                        active_futures.add(executor.submit(check_chunk, (pdf_bytes, next_chunk)))
                    except StopIteration:
                        pass

        # Final count of attempts (approximate for display)
        if not attempts_count:
             attempts_count = total_passwords
                
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

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error and return a JSON error message
    print(f"Unhandled Exception: {e}")
    return jsonify({
        'success': False,
        'error': 'An internal server error occurred.',
        'details': str(e)
    }), 500

if __name__ == '__main__':
    # Try to run on port 5000, but handle cases where it might be blocked
    try:
        print("\n" + "="*50)
        print("MESNA PDF CRACKER IS STARTING...")
        print("Link: http://127.0.0.1:5000")
        print("="*50 + "\n")
        app.run(host='0.0.0.0', debug=True, port=5000)
    except Exception as e:
        print(f"ERROR: Could not start server on port 5000. It might be in use by another app.")
        print(f"Technical details: {e}")
