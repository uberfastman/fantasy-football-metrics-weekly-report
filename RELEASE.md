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
   
4. Lint code with `flake8`:
    ```shell
    flake8 . --count --show-source --statistics
    ```

5. Check code security with `bandit`:
    ```shell
    bandit -r .
    ```

6. Run *all* `pytest` tests:
    ```shell
    python -m pytest
    ```

7. Run *all* `pytest` tests *verbosely*:
    ```shell
    python -m pytest -v -s
    ```

8. Create a git commit:
   ```shell
   git add .
   git commit -m 'commit message'
   ```

9. *(Optional)* View git tags:
   ```shell
   git tag -l --sort=v:refname -n99
   ```

10. Update the git tag:

   `git tag -a [tag_name/version] -m [message]`

   ```shell
   git tag -a v1.0.0 -m 'first release'
   git push origin --tags
   ```

11. Update `fantasy-football-metrics-weekly-report` GitHub repository:
   ```shell
   git push
   ```
