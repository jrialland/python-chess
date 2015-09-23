#!/bin/bash
set -e
source /lib/lsb/init-functions

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


echo 'Input Python script :' $target
echo 'Executable name : ' $exe_name


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
       apt-get install $1
    fi
    log_end_msg 0
}
verify_pkg unzip
verify_pkg git
verify_pkg scons
verify_pkg wine
verify_pkg python-pip
pip install wheel --upgrade 2>&1 > /dev/null ||true

hr
#get pyinstaller
log_daemon_msg "Fetching pyinstaller from github"
git clone https://github.com/pyinstaller/pyinstaller
log_end_msg $?

hr
#get virtual-wine
log_daemon_msg "Fetching 'virtual-wine' from github"
git clone https://github.com/htgoebel/virtual-wine
log_end_msg $?

hr
#modify it a bit (remove winecfg at end of the script)
log_daemon_msg "Patching 'virtual-wine'"
cat virtual-wine/vwine-setup | grep -v /bin/winecfg > virtual-wine/vwine-setup.2
rm virtual-wine/vwine-setup
mv virtual-wine/vwine-setup.2 virtual-wine/vwine-setup
chmod +x virtual-wine/vwine-setup
log_end_msg $?

#ACTIVATING "windows" virtualenv
./virtual-wine/vwine-setup venv_wine
source ./venv_wine/bin/activate

hr
#install python 2.7
log_daemon_msg 'Installing Python 2.7.8 for win32'
wget https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi
wine msiexec /a python-2.7.8.msi /qn "TARGETDIR=c:/Python27"
log_end_msg $?

hr
#install setuptools
log_daemon_msg 'Installing setuptools'
wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
wine c:/Python27/python.exe ez_setup.py
log_end_msg $?

hr
#download pywin232 (quite tricky !)
log_daemon_msg 'Installing pywin32'
wget http://vorboss.dl.sourceforge.net/project/pywin32/pywin32/Build%20219/pywin32-219.win32-py2.7.exe
python -m wheel convert pywin32-219.win32-py2.7.exe
wine c:/Python27/Scripts/easy_install.exe pip
wine c:/Python27/Scripts/pip.exe install $(find ./ -name "*.whl")

log_end_msg 0
log_daemon_msg 'Running pywin32 postinstall script'
unzip -p pywin32-219.win32-py2.7.exe SCRIPTS/pywin32_postinstall.py > venv_wine/drive_c/pywin32_postinstall.py || true
wine c:/Python27/python.exe c:/pywin32_postinstall.py -install
log_end_msg $?

hr
#compile !
log_daemon_msg "Compiling $target Into .exe"
wine c:/Python27/python.exe pyinstaller/pyinstaller.py -D $target
log_end_msg $?

#turn off virtual env
deactivate


if [ -d dist ]; then
    mv dist $thisdir
else
    echo 'Build Error'
    exit 255
fi

popd