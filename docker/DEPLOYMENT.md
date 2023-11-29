
# Docker

The Fantasy Football Metrics Weekly Report can be used within Docker for a more seamless, platform-agnostic experience.

## Build

1. Build the Docker image:
    ```shell
    docker compose -f compose.yaml -f compose.build.yaml build
    ```

## Deploy

1. Authenticate with GitHub Personal Access Token (PAT):
    ```shell
    jq -r .github_personal_access_token.value auth/github/private.json | docker login ghcr.io -u uberfastman --password-stdin
    ```

2. Deploy the newly-built Docker image with respective major, minor, and patch version numbers to the GitHub Container Registry:
    ```shell
    docker push ghcr.io/uberfastman/fantasy-football-metrics-weekly-report:X.X.X
    ```

## Run

1. Run the Docker container:
    ```shell
    docker compose up
    ```
   
   The above image will be pulled automatically from the [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) if it has not already been built locally.
