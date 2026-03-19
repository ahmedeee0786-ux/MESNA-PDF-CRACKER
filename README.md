# Mesna PDF Cracker 🔓

A premium, blazing-fast web application to completely crack protected PDF files locally on your own machine. Features an elegant glassmorphism UI, real-time animations, and a highly-optimized Python backend using multiprocessing.

![UI Screenshot](https://img.shields.io/badge/UI-Glassmorphism-purple?style=flat-square)
![Backend](https://img.shields.io/badge/Backend-Python_Flask-blue?style=flat-square)
![Engine](https://img.shields.io/badge/Acceleration-Pikepdf_C++-green?style=flat-square)

## Features ✨
- **10x-50x Speed Boost**: Uses the `pikepdf` C++ engine combined with Python's `ProcessPoolExecutor` to utilize 100% of your available CPU cores simultaneously.
- **6-Digit PIN Brute Force**: Automatically generates and tests all 1,000,000 possible 6-digit combinations (000000 - 999999).
- **Custom Dictionary Mode**: Input a custom list of passwords to try specific names, dates, or common phrases.
- **Live Hacker UI**: Dynamic frontend interface complete with live stopwatches and animated combination scrolling.
- **Mobile Remote**: Host the backend on your laptop, but control the cracking process directly from your smartphone's browser on the same Wi-Fi.

## How to Install and Run 🛠️

1. **Clone this repository** to your machine (or download the ZIP file).
2. **Install the dependencies:** Open your terminal in the project folder and run:
   ```bash
   pip install -r requirements.txt
   ```
3. **Start the local server:**
   ```bash
   python app.py
   ```
4. **Open in Browser:**
   Go to `http://127.0.0.1:5000` in your web browser. 
   *(To use on a mobile phone anywhere in the world, use your live public link: `https://clever-bars-check.loca.lt`!)*

## Disclaimer ⚠️
This tool was created for educational logic demonstrations and recovering your own lost passwords. Please do not use this tool on PDF documents you do not legally own or have explicit permission to access.
