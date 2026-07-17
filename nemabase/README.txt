it is needed to be in the "blast environment" for all python scripts referenced, to make sure all packages are installed etc, in the easiest way possible

when you have never installed WSL:
wsl --install

open BASH in folder:
right click in this folder, open terminal here, type: bash

if not yet installed install full python3:
sudo apt install python3-full -y

create virtual environment:
python3 -m venv ~/blast_env

activate new environment:
source ~/blast_env/bin/activate

install packages:
pip install biopython pandas openpyxl requests
if any errors because of missing packages, add them


run script:
"script name".py

every time you want to run the script or other scripts, you need to be in the environment so type: source ~/blast_env/bin/activate