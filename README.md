# Modded Multiplayer BG3 vortex conflict checker

## Installation instructions

1. Extract the zip file to a folder
2. Open your terminal / powershell and cd to the folder

   1. for example if you extracted bg3mpcc to this folder: `C:\BG3\bg3mpcc` run `cd C:\BG3\bg3mpcc`
3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) by:

   1. macOS/linux -> Open your terminal and type -> `curl -LsSf https://astral.sh/uv/install.sh | sh`
   2. Windows -> Open a **Powershell** (not cmd) -> `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. Install python by running `uv --install python 3.11`
5. Initialise a virtual env: `uv venv`
6. Install dependancies -> `uv sync`

## Usage

1. Each player should upload their startup.json file from `%userprofile%\AppData\Roaming\Vortex\temp\state_backups_full\`

   1. I would recommend renaming each file to a sensible and recognisable name, for eg `foo.json`, `bar.json` etc. Only use strings for the name, no spaces or special characters.
2. Place all of them into the `/data` folder
3. Run the script with the expected arguments
