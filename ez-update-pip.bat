@echo off

echo Upgrading pip...

:: upgrade pip
:: TODO: make this catch if there is an error (with the command name) and do a different python
py -m pip install -U pip

echo Done upgrading pip!
echo Upgrading required modules...

:: install and update packages
py -m pip install --upgrade -r requirements.txt

echo Done upgrading required modules!
echo All done, you can now start the bot.

pause