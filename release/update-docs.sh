#!/usr/bin/env bash
set -e
# TODO update this
if [ "$#" -ne 1 ]; then
    echo "Usage: update-docs.sh [release-version]"
    exit 1
fi
MLFLOW_RELEASE_VERSION=$1
echo "Updating docs for MLflow version $MLFLOW_RELEASE_VERSION"


# TODO: set up ~/.aws/credentials in Jenkins
# These are credentials for pushing to ECR, MLflow website
DOCS_TEMPDIR=$(python -c "import tempfile; print(tempfile.mkdtemp())")
MLFLOW_DIR="$DOCS_TEMPDIR/mlflow"
MLFLOW_WEBSITE_DIR="$DOCS_TEMPDIR/mlflow-website"

# Clone repos
pushd "$DOCS_TEMPDIR"
git clone "https://github.com/databricks/mlflow-website"
git clone "https://github.com/mlflow/mlflow"
popd

# Build MLflow docs from source. TODO: Maybe don't copy the R docs, unless we're doing a CRAN release?
pushd $MLFLOW_DIR
# Rename remote for changelog automation script
git remote rename origin upstream
pip install -r dev-requirements.txt
pip install -e .
# TODO: are test reqs necessary?
# pip install -r test-requirements-txt
pushd docs
# Install Maven & R
# sudo apt install maven
# echo "deb https://cloud.r-project.org/bin/linux/ubuntu xenial-cran35/" | sudo tee -a /etc/apt/sources.list
# sudo apt-get update
# sudo apt-get install r-base r-base-dev curl libcurl4-openssl-dev texlive-latex-base libxml2-dev --yes --allow-unauthenticated
# # Install a recent version of pandoc
# TEMP_DEB="$(mktemp)" &&
# wget -O "$TEMP_DEB" 'https://github.com/jgm/pandoc/releases/download/2.7.2/pandoc-2.7.2-1-amd64.deb' &&
# sudo dpkg -i "$TEMP_DEB"
# rm -f "$TEMP_DEB"
make html
popd
popd

# Copy over docs
cp -r $MLFLOW_DIR/docs/build/html/ $MLFLOW_WEBSITE_DIR/docs/$MLFLOW_RELEASE_VERSION
rm -r $MLFLOW_WEBSITE_DIR/docs/latest
cp -r $MLFLOW_DIR/docs/build/html/ $MLFLOW_WEBSITE_DIR/docs/latest

# Install dependencies & build mlflow.org
# Install Ruby
# sudo snap install ruby --classic
pushd $MLFLOW_WEBSITE_DIR
sudo gem install bundler
sudo bundle install
sudo gem install s3_website
JEKYLL_ENV=production bundle exec jekyll build
s3_website push --dry-run
popd
