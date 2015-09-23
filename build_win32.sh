#!/bin/bash
set -e

#current script path
thisscript=`readlink -m $0`

#current dir path
thisdir=`dirname $thisscript`

#script to compile
if [ -z "$1" ]; then
    echo "Missing argument. (Usage : $0 <script to compile>)"
    exit 1
fi

target=`readlink -m $1`
if [ ! -f $target ]; then
    echo "No such script : $script"
    exit 2
fi

exe_name=$(echo `basename $target` | sed s/\\.py$/.exe/)
prj_name=$(echo $exe_name | sed s/\\.exe$//)

echo 'Input Python script :' $target
echo 'Executable name : ' $exe_name
echo 'Project name : ' $prj_name

export DEBIAN_FRONTEND=noninteractive

#jump into a fresh 'build_win32 directory'
rm -rf _win32 2>/dev/null
mkdir _win32
pushd _win32

function hr {
	echo '----------'
}

hr
#verify some dependencies
function verify_pkg {
	log_daemon_msg "verifying installation for package $1"
	dpkg -l $1 > /dev/null
    if [ $? != 0 ]; then
        echo $1 'is missing' >&2
        exit 255
    fi
    log_end_msg 0
}

pip install wheel --upgrade 2>&1 > /dev/null ||true

hr
#get pyinstaller
echo "Fetching pyinstaller from github"
git clone https://github.com/pyinstaller/pyinstaller


hr
#get virtual-wine
echo "Fetching 'virtual-wine' from github"
git clone https://github.com/htgoebel/virtual-wine

hr
#modify it a bit (remove winecfg at end of the script)
echo "Patching 'virtual-wine'"
cat virtual-wine/vwine-setup | grep -v /bin/winecfg > virtual-wine/vwine-setup.2
rm virtual-wine/vwine-setup
mv virtual-wine/vwine-setup.2 virtual-wine/vwine-setup
chmod +x virtual-wine/vwine-setup

#ACTIVATING "windows" virtualenv
./virtual-wine/vwine-setup venv_wine
source ./venv_wine/bin/activate

#start xvfb
Xvfb :10 -ac -screen 0 1024x768x24 &
xvfb_pid=$?
export DISPLAY=:10.0

hr
#install python 2.7
echo 'Installing Python 2.7.8 for win32'
wget https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi
wine msiexec /a python-2.7.8.msi /qn "TARGETDIR=c:/Python27"

hr
#install setuptools
echo 'Installing setuptools'
wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
wine c:/Python27/python.exe ez_setup.py

hr
#download pywin232 (non-interactive installation)
echo 'Installing pywin32'
wget http://vorboss.dl.sourceforge.net/project/pywin32/pywin32/Build%20219/pywin32-219.win32-py2.7.exe
python -m wheel convert pywin32-219.win32-py2.7.exe
wine c:/Python27/Scripts/easy_install.exe pip
wine c:/Python27/Scripts/pip.exe install $(find ./ -name "*.whl")

echo 'Running pywin32 postinstall script'
unzip -p pywin32-219.win32-py2.7.exe SCRIPTS/pywin32_postinstall.py > venv_wine/drive_c/pywin32_postinstall.py || true
wine c:/Python27/python.exe c:/pywin32_postinstall.py -install


hr
#compile !
echo "Compiling $target Into .exe"
wine c:/Python27/python.exe pyinstaller/pyinstaller.py --onefile $target
cp dist/$exe_name dist/$prj_name-noupx.exe

wget http://upx.sourceforge.net/download/upx391w.zip
unzip upx391w.zip
wine upx391w/upx.exe dist/$exe_name

#turn off virtual env
deactivate

kill -9 $xvfb_pid > /dev/null 2>&1

if [ -d dist ]; then
    mv dist $thisdir
    echo 'Generated executable in ' $thisdir/dist
else
    echo 'Build Error'
    exit 255
fi

popd
