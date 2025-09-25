from pathlib import Path
from re import findall
from subprocess import CalledProcessError, DEVNULL, check_output
from typing import Optional

from ruamel.yaml import YAML
from semver import Version
from tomlkit import (
    TOMLDocument,
    dumps as write_toml,
    parse as read_toml,
)

# configure inline comment indicating all automatically updated versions across project files
EDIT_MESSAGE = "# DO NOT EDIT - VERSIONING SET AUTOMATICALLY"

project_root_dir = Path(__file__).parent.parent
pyproject_toml_file_path = project_root_dir / "pyproject.toml"


def get_pyproject_toml() -> TOMLDocument:
    """Read the pyproject.toml file and return a TOMLDocument.
    """
    with open(pyproject_toml_file_path, "r") as pyproject_toml_file_in:
        pyproject_toml = read_toml(pyproject_toml_file_in.read())
    return pyproject_toml


def get_project_and_python_versions() -> tuple[Version, Version]:
    """Extract the semantic version of the project and supported Python semantic versions from the pyproject.toml file.
    """
    pyproject_toml_document = get_pyproject_toml()

    project_version = Version.parse(pyproject_toml_document["project"]["version"])
    python_version = sorted([
        Version.parse(py_ver, optional_minor_and_patch=True)
        for py_ver in findall(r"[\d.]+", pyproject_toml_document["project"]["requires-python"])
    ])[-1]
    # reduce minor version by one to handle exclusive Python version constraint
    python_version._minor = python_version.minor - 1

    return project_version, python_version


def get_git_version() -> Optional[Version]:
    """Extract the last set semantic version of project from git tags.
    """
    try:
        git_version = check_output(
            ["git", "describe", "--tag", "--abbrev=0"],
            stderr=DEVNULL
        ).decode("utf-8").strip()[1:]
    except CalledProcessError:
        git_version = None

    return git_version


project_semantic_version, python_semantic_version = get_project_and_python_versions()
git_tag_version = get_git_version()

# write the latest git tag project version to pyproject.toml
if git_tag_version:
    print("Setting project.version value in pyproject.toml with project version from git tag...")

    pyproject_toml_doc = get_pyproject_toml()

    with open(pyproject_toml_file_path, "w") as pyproject_toml_file_out:
        pyproject_toml_doc["project"]["version"] = git_tag_version
        pyproject_toml_doc["project"]["version"].comment(EDIT_MESSAGE)

        pyproject_toml_file_out.write(write_toml(pyproject_toml_doc))
    print("...updated pyproject.toml with latest project version.")
else:
    print(
        f"...no git tag found. Defaulting to existing project.version value in pyproject.toml: "
        f"v{project_semantic_version}"
    )

# write the latest git tag project version to compose.yaml
docker_compose_yaml_file = project_root_dir / "compose.yaml"
if docker_compose_yaml_file.exists():

    project_sem_version = git_tag_version if git_tag_version else project_semantic_version
    print(
        f"Updating \"compose.yaml\" with project version from "
        f"{'git tag' if git_tag_version else 'pyproject.toml'} to v{project_semantic_version}..."
    )

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    docker_compose_yaml = yaml.load(docker_compose_yaml_file)
    docker_compose_yaml["services"]["app"]["image"] = (
        f"{docker_compose_yaml['services']['app']['image'].split(':')[0]}"
        f":{str(project_semantic_version).replace('v', '')}"
    )
    docker_compose_yaml["services"]["app"].yaml_add_eol_comment(EDIT_MESSAGE, key="image")

    yaml.default_flow_style = False
    yaml.dump(docker_compose_yaml, docker_compose_yaml_file)
    print("...updated \"compose.yaml\" with latest project version.")

# write the latest supported Python version configured in pyproject.toml to compose.build.yaml
docker_compose_build_yaml_file = project_root_dir / "compose.build.yaml"
if docker_compose_build_yaml_file.exists():
    print("Updating \"compose.build.yaml\" with Python version from pyproject.toml...")

    yaml = YAML(typ="rt")
    docker_compose_build_yaml = yaml.load(docker_compose_build_yaml_file)

    updated_build_args = []
    for build_arg in docker_compose_build_yaml["services"]["app"]["build"]["args"]:
        build_arg_key, build_arg_value = build_arg.split("=")
        if build_arg_key == "PYTHON_VERSION_MAJOR":
            build_arg_value = python_semantic_version.major
        elif build_arg_key == "PYTHON_VERSION_MINOR":
            build_arg_value = python_semantic_version.minor
        updated_build_args.append(f"{build_arg_key}={build_arg_value}")
    docker_compose_build_yaml["services"]["app"]["build"]["args"] = updated_build_args

    app_build_dict = docker_compose_build_yaml["services"]["app"]["build"]
    if app_build_dict.ca.items.get("args") and app_build_dict.ca.items["args"][2]:
        app_build_dict_eol_comment = app_build_dict.ca.items["args"][2]
        app_build_dict_eol_comment.value = EDIT_MESSAGE
    else:
        app_build_dict.yaml_add_eol_comment(EDIT_MESSAGE, key="args")

    yaml.default_flow_style = False
    yaml.dump(docker_compose_build_yaml, docker_compose_build_yaml_file)
    print("...updated \"compose.build.yaml\" with latest supported Python version.")
