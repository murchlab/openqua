import os
import zipfile
import subprocess

file_dir = os.path.dirname(os.path.abspath(__file__))
python = os.path.join(file_dir, r'python\python.exe')


def check():
    return os.path.isfile(python)


def download_python():
    import requests
    url = 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip'
    python_zip = os.path.join(file_dir, r'python.zip')
    with open(python_zip, 'wb') as f:
        content = requests.get(url, stream=True).content
        f.write(content)
    
    python_dir = os.path.join(file_dir, r'python')
    with zipfile.ZipFile(python_zip, 'r') as zip_ref:
        zip_ref.extractall(python_dir)
        
    os.remove(python_zip)
    
    
def install_packages():
    import requests
    url = 'https://bootstrap.pypa.io/get-pip.py'
    get_pip = os.path.join(file_dir, r'get-pip.py')
    with open(get_pip, 'wb') as f:
        content = requests.get(url, stream=True).content
        f.write(content)
        
    p = subprocess.Popen([python, get_pip], shell=True)
    p.communicate()
    
    os.remove(get_pip)
    
    python310_pth = os.path.join(file_dir, r'python\python310._pth')
    pth = ''
    pth += 'python310.zip\n'
    pth += '.\n'
    pth += 'Lib\n'
    pth += 'Lib\site-packages\n'
    with open(python310_pth, 'w') as f:
        f.write(pth)
    
    requirements = os.path.join(file_dir, r'requirements.txt')
    p = subprocess.Popen([python, '-m', 'pip', 'install', '-r', requirements], shell=True)
    p.communicate()
    
    
def setup():
    print('Installing python embeddable package...')
    download_python()
    install_packages()
    print('Done.')
    

def check_setup():
    if not check():
        setup()
        

if __name__ == '__main__':
    check_setup()
        