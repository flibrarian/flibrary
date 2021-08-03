sudo dpkg --add-architecture i386
sudo apt-get update
wget https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/Debian_10/amd64/libfaudio0_20.01-0~buster_amd64.deb
wget https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/Debian_10/i386/libfaudio0_20.01-0~buster_i386.deb
sudo dpkg -i libfaudio0_20.01-0~buster_amd64.deb libfaudio0_20.01-0~buster_i386.deb
rm libfaudio0_20.01-0~buster_amd64.deb libfaudio0_20.01-0~buster_i386.deb
sudo apt --fix-broken install -y


sudo apt install -y software-properties-common
sudo apt-add-repository https://dl.winehq.org/wine-builds/debian/
wget -nc https://dl.winehq.org/wine-builds/winehq.key
sudo apt-key add winehq.key
rm winehq.key
sudo apt-get update
sudo apt-get install -y --install-recommends winehq-stable
sudo apt-get install -y winetricks
WINEARCH=win32 WINEPREFIX=~/.wine winecfg
winetricks -q win10
winetricks vcrun2015
winetricks -q win10
winecfg