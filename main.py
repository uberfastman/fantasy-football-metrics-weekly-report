import sys

if not sys.warnoptions:
    import warnings

    # suppress SyntaxWarning due to "invalid escape sequence" messages in transitive dependencies: rauth, stringcase
    warnings.filterwarnings("ignore", category=SyntaxWarning)

from datetime import datetime
from importlib.metadata import distributions
from pathlib import Path

from ffmwr.report.builder import FantasyFootballReport
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import get_app_settings_from_yaml_file
from ffmwr.utilities.utils import normalize_dependency_package_name

logger = get_logger()


def create_report(settings):
    """Create and return a FantasyFootballReport with hardcoded sensible defaults."""
    return FantasyFootballReport(
        settings=settings,
        platform="espn",
        break_ties=True,  # Always break ties
        refresh_feature_web_data=settings.refresh_feature_web_data,  # Use config setting
    )


def main() -> None:
    """Generate ESPN Fantasy Football report using config.yaml settings."""
    # Check if we're in a uv managed project by looking for pyproject.toml
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    if not pyproject_path.exists():
        logger.error(
            "No pyproject.toml found. Please run `uv sync` to install dependencies and retry the report generation."
        )
        sys.exit(1)

    # Import tomllib for Python 3.11+ or tomli for older versions
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            logger.warning(
                "Cannot check dependencies without tomllib/tomli. Continuing..."
            )
            return

    # Read dependencies from pyproject.toml
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        dependencies = pyproject_data.get("project", {}).get("dependencies", [])

        installed_dependencies = sorted(
            [
                f"{normalize_dependency_package_name(x.name)}=={x.version}"
                for x in distributions()
            ]
        )

        missing_dependency_count = 0
        for dep_spec in dependencies:
            # Parse dependency specification (e.g., "colorama==0.4.6")
            if "==" in dep_spec:
                dep_name, dep_version = dep_spec.split("==")
                normalized_dep = (
                    f"{normalize_dependency_package_name(dep_name)}=={dep_version}"
                )
                if normalized_dep not in installed_dependencies:
                    missing_dependency_count += 1
                    logger.error(
                        f"MISSING DEPENDENCY: {normalized_dep}. Please run `uv sync` and retry the report generation."
                    )

        if missing_dependency_count > 0:
            logger.error(
                f"MISSING {missing_dependency_count} "
                + ("DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES")
            )
            logger.info("Run `uv sync` to install all required dependencies.")
            sys.exit(1)

    except Exception as e:
        logger.warning(f"Could not check dependencies: {e}. Continuing...")

    # Load configuration
    root_directory = Path(__file__).parent
    app_settings = get_app_settings_from_yaml_file(root_directory / "config.yaml")

    # Generate report
    logger.info(
        f"Generating ESPN Fantasy Football report on {datetime.now():%b %-d, %Y at %-I:%M%p}"
    )

    report = create_report(app_settings)
    report.create_pdf_report()


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == "__main__":
    main()
