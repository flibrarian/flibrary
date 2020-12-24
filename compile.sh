wine ~/.wine/drive_c/Python27/Scripts/pyinstaller.exe --onefile flibextract.py
wine ~/.wine/drive_c/Python27/Scripts/pyinstaller.exe --onefile flibdump.py
wine ~/.wine/drive_c/Python27/Scripts/pyinstaller.exe --onefile flibhtml.py
mv dist/*.exe .
rm -r dist build
rm *.spec
