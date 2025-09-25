# Fantasy Football Metrics Weekly Report Deployment

1. *(Optional)* Clear virtual machine of old requirements:
    ```shell
    uv pip uninstall -r <(uv pip freeze)
    ```

2. *(Optional)* Check the `dependencies` and `dev-dependencies` sections of `pyproject.toml` for latest dependency versions.

3. *(Optional)* Update virtual machine with the latest dependencies:
    ```shell
    make update
    ```
   
4. *(Optional)* Run *all* `pytest` tests:
    ```shell
    make test_code
    ```
   
5. *(Optional)* Run *all* `pytest` tests *verbosely*:
    ```shell
    python -m pytest -v -s
    ```

6. *(Optional)* Test Python support using [act](https://github.com/nektos/act) for GitHub Actions:

    ```shell
    make test_actions
    ```

    ***Note***: If `act` is unable to locate Docker, make sure that the required `/var/run/docker.sock` symlink exists. If it does not, you can fix it by running:
    
    ```shell
    sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock`
    ```

7. *(Optional)* Create a new git branch if creating a release:
    ```shell
    git checkout -b release/vX.X.X
    ```

8. Create a git commit:
    ```shell
    git add .
    git commit -m 'commit message'
    ```
    
9. Update the git tag (format: `git tag -a [tag_name/version] -m [message]`):
    ```shell
    git tag -a v1.0.0 -m 'first release'
    git push origin --tags
    ```

10. *(Optional)* View git tags:
    ```shell
    git tag -l --sort=v:refname -n99
    ```

11. Update the `pyproject.toml` and `compose.yaml` files with the latest version of the app from the above git tag.
     ```shell
     make pre_deploy
     ```
   
     * The above script will *also* update the `compose.build.yaml` file with the latest supported Python version configured in the `pyproject.toml`.

12. Create a second git commit with the updated project version.
    ```shell
    make git_post_deploy
    ```

13. The Fantasy Football Metrics Weekly Report can be used within Docker for a more seamless, platform-agnostic experience.

    1. Build the Docker image:
        ```shell
        docker compose -f compose.yaml -f compose.build.yaml build
        ``` 

        ***Note***: If you need to rebuild the Docker image with updated dependencies, run `docker compose -f compose.yaml -f compose.build.yaml build --no-cache`.

    2. Authenticate with GitHub Personal Access Token (PAT):
        ```shell
        jq -r .github_personal_access_token.value private-github.json | docker login ghcr.io -u uberfastman --password-stdin
        ```

    3. Deploy the newly-built Docker image with respective major, minor, and patch version numbers to the GitHub Container Registry:
        ```shell
        docker push ghcr.io/uberfastman/fantasy-football-metrics-weekly-report:X.X.X
        ```

    4. Run the Docker container:
        ```shell
        docker compose up
        ```

        The above image will be pulled automatically from the [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) if it has not already been built locally.

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
