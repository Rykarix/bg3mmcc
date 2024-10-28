# Modded Multiplayer BG3 vortex conflict checker

## Installation instructions

1. Extract the zip file to a folder / clone as required
2. Open your terminal / powershell and cd to the folder
   - for example if you extracted bg3mpcc to this folder: `C:\BG3\bg3mpcc` run `cd C:\BG3\bg3mpcc`
3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) by:
   - macOS/linux -> Open your terminal and type -> `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows -> Open a **Powershell** (not cmd) -> `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. Install python by running `uv --install python 3.11` if you don't have it
5. Initialise a virtual env: `uv venv`
6. Install dependancies -> `uv sync`

## Usage

1. Each player should upload their startup.json file from `%userprofile%\AppData\Roaming\Vortex\temp\state_backups_full\`. Just throw it in a discord chat or something
2. Place all of them into the `/data/settings_json` folder
   - I would recommend renaming each file to a sensible and recognisable name, for eg `plsnomoar.json`, `bear.json`, `secks.json` etc. Only use strings for the name, no spaces or special characters.
3. Run the script with the expected arguments: `uv run bg3mmcc.py --hosts-file="HOSTS_FILENAME.json"

Each file that conflicts with the host will have a list of conflicting mods saved in `data/conflict_analysis`

![](./.assets/image.png)
