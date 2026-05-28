#!/bin/bash
# AWS Lambda にデプロイパッケージをアップロードする最小スクリプト
#
# 前提:
# - AWS CLI がセットアップ済み (aws configure or AWS_PROFILE)
# - 環境変数 FUNCTION_NAME, REGION を必要に応じて上書き
# - Lambda 関数本体は別途作成済み

set -euo pipefail

FUNCTION_NAME="${FUNCTION_NAME:-janken-line-bot}"
REGION="${REGION:-ap-northeast-1}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
BUILD_DIR="$PROJECT_ROOT/build"
ZIP_FILE="$PROJECT_ROOT/lambda_function.zip"

echo "Building deploy package for $FUNCTION_NAME ($REGION)..."

rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

cp "$LAMBDA_DIR"/*.py "$BUILD_DIR/"
pip install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR" --quiet

( cd "$BUILD_DIR" && zip -rq "$ZIP_FILE" . )

echo "Uploading to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" \
    --output json > /dev/null

rm -rf "$BUILD_DIR" "$ZIP_FILE"

echo "Done."
