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

install conda:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

create environment:
conda create -n NGSpeciesID python=3.8 -y

activate: 
conda activate NGSpeciesID

install ngs speciesid:
pip install NGSpeciesID

deactivate conda: 
conda deactivate

run script in the folder the script is in:
"script name".py

every time you want to run the script or other scripts, you need to be in the environment so type: source ~/blast_env/bin/activate