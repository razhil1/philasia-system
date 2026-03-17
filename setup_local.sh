#!/bin/bash
echo "============================================"
echo " PhilAsia Inventory - Local Setup (Mac/Linux)"
echo "============================================"

echo ""
echo "[1/3] Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "[2/3] Initializing database..."
python3 init_db.py

echo ""
echo "[3/3] Setup complete!"
echo ""
echo "Default credentials:"
echo "  Admin:   admin / admin123"
echo "  Others:  <username> / password123"
echo ""
echo "To start the app, run:  python3 run.py"
echo "Then open:  http://localhost:5000"
