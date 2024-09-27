# Fantasy Football Metrics Weekly Report Deployment

1. *(Optional)* Clear virtual machine of old requirements:
    ```shell
    pip uninstall -y -r <(pip freeze)
    ```
   
2. *(Optional)* Check `requirements.txt` and `requirement-dev.txt` for latest dependency versions.

3. *(Optional)* Update virtual machine with the latest dependencies:
    ```shell
    pip install -r requirements.txt -r requirements-dev.txt
    ```
   
4. *(Optional)* Lint code with `flake8`:
    ```shell
    flake8 . --count --show-source --statistics
    ```
   
5. *(Optional)* Check code security with `bandit`:
    ```shell
    bandit -r .
    ```
   
6. *(Optional)* Run *all* `pytest` tests:
    ```shell
    python -m pytest
    ```
   
7. *(Optional)* Run *all* `pytest` tests *verbosely*:
    ```shell
    python -m pytest -v -s
    ```

8. *(Optional)* Test Python support using [act](https://github.com/nektos/act) for GitHub Actions:

    ```shell
    act -j build
    ```

    ***Note***: If `act` is unable to locate Docker, make sure that the required `/var/run/docker.sock` symlink exists. If it does not, you can fix it by running:
    
    ```shell
    sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock`
    ```

9. Update the Docker `compose.yaml` file with the latest version of the app.

10. Build and push a new Docker image for the app (see [DEPLOYMENT.md](./docker/DEPLOYMENT.md)).

11. Create a new git branch:
    ```shell
    git checkout -b release/vX.X.X
    ```

12. Create a git commit:
    ```shell
    git add .
    git commit -m 'commit message'
    ```
   
13. *(Optional)* View git tags:
    ```shell
    git tag -l --sort=v:refname -n99
    ```
    
14. Update the git tag (format: `git tag -a [tag_name/version] -m [message]`):
   ```shell
   git tag -a v1.0.0 -m 'first release'
   git push origin --tags
   ```

15. Update `fantasy-football-metrics-weekly-report` GitHub repository:
   ```shell
   git push
   ```

16. Go to the [FFMWR Releases page](https://github.com/uberfastman/fantasy-football-metrics-weekly-report/releases) and draft a new release using the above git tag.
