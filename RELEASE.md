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
   
4. *(Optional)* Run *all* `pytest` tests:
    ```shell
    python -m pytest
    ```
   
5. *(Optional)* Run *all* `pytest` tests *verbosely*:
    ```shell
    python -m pytest -v -s
    ```

6. *(Optional)* Test Python support using [act](https://github.com/nektos/act) for GitHub Actions:

    ```shell
    act -j build
    ```

    ***Note***: If `act` is unable to locate Docker, make sure that the required `/var/run/docker.sock` symlink exists. If it does not, you can fix it by running:
    
    ```shell
    sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock`
    ```

7. Update the Docker `compose.yaml` file with the latest version of the app.

8. Build and push a new Docker image for the app (see [DEPLOYMENT.md](./docker/DEPLOYMENT.md)).

9. *(Optional)* Create a new git branch if creating a release:
   ```shell
   git checkout -b release/vX.X.X
   ```

10. Create a git commit:
    ```shell
    git add .
    git commit -m 'commit message'
    ```
    
11. Update the git tag (format: `git tag -a [tag_name/version] -m [message]`):
    ```shell
    git tag -a v1.0.0 -m 'first release'
    git push origin --tags
    ```

12. *(Optional)* View git tags:
    ```shell
    git tag -l --sort=v:refname -n99
    ```

13. Update `fantasy-football-metrics-weekly-report` GitHub repository:

    * *(Optional)* If creating a release:    
        ```shell
        git push -u origin release/vX.X.X
        ```
    
    * If updating `main`:
        ```shell
        git push
        ```

14. Open a pull request (PR) with the `release/vX.X.X` branch, allow GitHub actions to complete successfully, draft release notes, and merge it.

15. Go to the [FFMWR Releases page](https://github.com/uberfastman/fantasy-football-metrics-weekly-report/releases) and draft a new release using the above git tag.
