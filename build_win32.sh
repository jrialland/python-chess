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

mkdir -p _win32
pushd _win32

pip install wheel --upgrade 2>&1 > /dev/null ||true

#get pyinstaller
if [ ! -d pyinstaller ]; then
  echo "Fetching pyinstaller from github"
  git clone https://github.com/pyinstaller/pyinstaller
fi

#get virtual-wine
if [ ! -d virtual-wine ]; then
  echo "Fetching 'virtual-wine' from github"
  git clone https://github.com/htgoebel/virtual-wine
fi

#modify it a bit (remove winecfg at end of the script)
cat virtual-wine/vwine-setup | grep -v /bin/winecfg > virtual-wine/vwine-setup.2
rm virtual-wine/vwine-setup
mv virtual-wine/vwine-setup.2 virtual-wine/vwine-setup
chmod +x virtual-wine/vwine-setup

#ACTIVATING "windows" virtualenv
if [ ! -d venv_wine ]; then 
  ./virtual-wine/vwine-setup venv_wine
fi
source ./venv_wine/bin/activate

#install python 2.7
if [ ! -f python-2.7.8.msi ]; then
  echo 'Installing Python 2.7.8 for win32'
  wget https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi
fi

if [ ! -d venv_wine/drive_c/Python27 ]; then
  wine msiexec /a python-2.7.8.msi /qn "TARGETDIR=c:/Python27"
fi

if [ ! -f ez_setup.py ]; then
  wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
fi

#install pip
if [ ! -f venv_wine/drive_c/Python27/Scripts/pip.exe ]; then
  echo 'Installing pip'
  wine c:/Python27/python.exe ez_setup.py
  wine c:/Python27/Scripts/easy_install.exe pip
fi

#install pywin32
if [ ! -f pywin32-219.win32-py2.7.exe ]; then
  wget http://vorboss.dl.sourceforge.net/project/pywin32/pywin32/Build%20219/pywin32-219.win32-py2.7.exe
fi

if [ ! -f pywin32-219-cp27-none-win32.whl ]; then
  python -m wheel convert pywin32-219.win32-py2.7.exe
fi

if [ ! -f venv_wine/drive_c/Python27/Scripts/pywin32_testall.pyc ]; then
  wine c:/Python27/Scripts/pip.exe install $(find ./ -name "*.whl")
  unzip -p pywin32-219.win32-py2.7.exe SCRIPTS/pywin32_postinstall.py > venv_wine/drive_c/pywin32_postinstall.py || true
  wine c:/Python27/python.exe c:/pywin32_postinstall.py -install
fi

wine c:/Python27/Scripts/pip.exe install pefile dis3


#compile !
echo "Compiling $target Into .exe"
wine c:/Python27/python.exe pyinstaller/pyinstaller.py --onefile $target

echo "Copying to $prj_name-noupx.exe"
cp dist/$exe_name dist/$prj_name-noupx.exe

if [ ! -f upx391w.zip ];then
  wget http://upx.sourceforge.net/download/upx391w.zip
fi

if [ ! -f upx391w/upx.exe ]; then
  echo 'Installing upx'
  unzip upx391w.zip
fi

echo 'Running UPX'
wine upx391w/upx.exe dist/$exe_name

#turn off virtual env
deactivate

if [ -d dist ]; then
    rm -rf $thisdir/dist/*
    mv -f dist $thisdir
    echo 'Generated executable available in ' $thisdir/dist
else
    echo 'Build Error'
    exit 255
fi

popd>/dev/null
