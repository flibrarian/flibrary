wine pyinstaller --onefile --collect-all lxml ../flibextract.py
wine pyinstaller --onefile --collect-all lxml ../flibdump.py
wine pyinstaller --onefile --collect-all lxml ../flibhtml.py
rm -r build
rm *.spec
