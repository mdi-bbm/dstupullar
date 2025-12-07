# DigitalAssistantMonorepo

This repo contains research code for Digital assistant service.

## Glossary

- **Mono-repository**: A single repository containing multiple projects, often sharing common tools and libraries. [wiki](https://en.wikipedia.org/wiki/Monorepo)
- **Branch**: A version of the repository, allowing for parallel development. [Git Branches](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell)
- **Merge Request (MR)**: A request to merge changes from one branch into another. [Git Merge Request](https://docs.gitlab.com/ee/user/project/merge_requests/)
- **Module**: A file or collection of files in Python that define functions, classes, and variables. [Python Modules](https://docs.python.org/3/tutorial/modules.html)
- **Package**: A collection of Python modules that are grouped together, typically to provide a specific functionality or set of functionalities. Packages can be installed using `pip` and are listed in the `requirements.txt` file. [Python Packages](https://packaging.python.org/tutorials/packaging-projects/)
- **Virtual Environment (venv)**: A tool to create isolated Python environments. [Python venv](https://docs.python.org/3/library/venv.html)


## Rules and Guidelines

### General Guidelines

+ **Python Version**: Use Python 3.10, the same as in Google Colab at the start of the project.
+ **Language**: All code and documentation must be in English.
+ **Git flow**:
    1. Create a new branch for your task from `develop`.
    2. Commit your changes to the new branch.
    3. Create a Merge Request (MR).
    4. Process feedback from team members.
    5. Merge your branch into `develop` and then delete the branch.
+ **Branching**: 
   - Branch names should follow the format `feature/branch-name`, using hyphens as separators.
   - Branches must be deleted automatically after merging into the `develop` branch. When creating MR check:
     - on the top of the page switch branch to `develop`;
     - [x] Delete source branch when merge request is accepted;
     - [ ] Squash commits when merge request is accepted.

### Code style

- The names of your objects should be understandable to everyone.
- Do not use your local path in code. Instead, use one of the following:
    - [argparse](https://docs.python.org/3.10/library/argparse.html) to parse command line arguments. In PyCharm's configuration, you can pass such parameters in `Parameters` field;
    - [os.getenv](https://www.geeksforgeeks.org/python-os-getenv-method/) to get a value of environment variable. In PyCharm's configuration, you can pass such parameters in `Environment variables` field;
    - use a **relative path** if it is not going to change.


### Project Structure

1. **Modules in `studies` folder**:
   - Must include one or several **script** files that contain a code to run module functionality. It could by a single `script.py` file OR it could be a `scripts` sub-folder with several script files.
   - Each script file should follow the template:
     ```python
     import your_module
     ...
     
     # utility functions that can be needed in this script only
     
     def main():
         # load data if needed 
         # run code from your_module
         # print or visualize results if needed
         
     if __name__ == '__main__':
         main()
     ```
     
2. **Binary and large files** of 1 Mb and larger:
    - We don't have [LFS](https://www.atlassian.com/git/tutorials/git-lfs) for now, so try to avoid large files in repo ([why](https://stackoverflow.com/questions/29393447/why-cant-git-handle-large-files-and-large-repos)).
    - If such files are necessary to run your scripts, commit some minimal bunch of them (not full dataset).
    - Use `data` folder in appropriate module to keep them.

### Merge Requests

- **Readme Requirement**: Every merge request must add or update at least one `README.md` file with descriptions of the module content and instructions on how to run it.

## Cloning the Repository

To clone the repository, use the following command:

```bash
git clone https://git.wizn.tech/digitalassistant/digitalassistantmonorepo
```

## Git flow
```bash
git checkout develop
git pull origin develop
git merge feature/your-branch-name
git add .
git commit -m "Commit message"
git push origin feature/branch-name
```

## Setting Up a Virtual Environment

### Windows

1. Open Command Prompt or PowerShell.
2. Navigate to the repository directory.
3. Create a virtual environment:
```shell
python -m venv venv
```
4. Activate the virtual environment:
```shell
venv/Scripts/activate
```

### Linux

1. Open a terminal.
2. Navigate to the repository directory.
3. Create a virtual environment:
```shell
python3 -m venv venv
```
4. Activate the virtual environment:
```shell
source venv/bin/activate
```

### Installing Packages
With the virtual environment activated, install the necessary packages using:

```shell
pip install -r requirements.txt
```

## Use repo from Colab
To run code of this repo from Colab, you should create a token and use it in the notebook.

On the https://git.wizn.tech/-/user_settings/personal_access_tokens page:
1. Click `Add new token`.
2. Set `Token name` (for example, Colab).
3. Set `Expiration data`.
4. In `Select scopes`, set `read_repository`.
5. Push `Create personal access token`.
6. Copy text from `Your new personal access token`.

In Colab notebook:
1. On the left panel, click on the key icon.
2. Specify the `Name` of the token as `assistant_token`.
3. Specify `Value` - insert the token from the clipboard.
4. Enable `Access from notepads`.
5. Repeat steps 2--4 for `Name`=`assistant_username`, `Value`=your_gitlab_username_without_@
6. Create a cell and fill the arguments with the `clone_digital_assistant_repo` function call:
```
import os
import sys
from google.colab import userdata

def clone_digital_assistant_repo(username: str, token: str, branch_name: str | None  = None):
    repo_name = 'digitalassistantmonorepo'
    repo_url = f'git.wizn.tech/digitalassistant/{repo_name}.git'
    branch_str = ''
    if branch_name is not None:
        branch_str = f'--branch {branch_name}'
    !git clone {branch_str} https://{username}:{token}@{repo_url}
    repo_dir = os.path.join(os.getcwd(), repo_name)
    sys.path.append(repo_dir)
	
clone_digital_assistant_repo(
    username=userdata.get('assistant_username'),
    token=userdata.get('assistant_token'),
    branch_name='develop'
)
```
6. Import required modules in Colab notebook cells like this:
```
from digitalassistantmonorepo.dataset.colab.process_dataset import process_dataset
```

The token bound to a Colab notebook is visible only to you. You can use the token in any Colab notebook by switching it on in `Access from notepads`. 

## Contributing
When contributing to this repository, please ensure your code adheres to the guidelines above. If you have any questions, refer to the official documentation linked in the glossary or contact the project maintainers.

Happy Coding!

