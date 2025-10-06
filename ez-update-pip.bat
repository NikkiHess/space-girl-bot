@echo off

echo "Upgrading pip..."

:: upgrade pip
python -m pip install -U pip

echo "Done upgrading pip!"
echo "Upgrading required modules..."

:: install and update packages
pip install --upgrade -r requirements.txt

echo "Done upgrading required modules!"
echo "All done, you can now start the bot."