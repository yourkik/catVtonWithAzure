#!/bin/bash

# Azure ML 워크스페이스 및 리소스 그룹 이름 변수 설정
export RESOURCE_GROUP="3dt-1st-team3"
export WORKSPACE_NAME="catvtonAML"
export LOCATION="koreacentral"
export ENDPOINT_NAME="catvton-aml-endpoint"

echo "1. Azure ML 워크스페이스 확인 및 생성..."
# az ml workspace show 가 실패하면(없으면) create 실행
az ml workspace show --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP || \
az ml workspace create --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP --location $LOCATION

echo "2. 기본 워크스페이스 설정..."
az configure --defaults group=$RESOURCE_GROUP workspace=$WORKSPACE_NAME

echo "3. 온라인 엔드포인트 생성 (약 5-10분 소요)..."
az ml online-endpoint create --file endpoint.yml

echo "4. 모델 배포 생성 및 트래픽 100% 라우팅 (약 15-20분 소요)..."
# Storage 연결 문자열을 파라미터로 받아 환경 변수에 오버라이드합니다.
# 사용: ./deploy_aml.sh "DefaultEndpointsProtocol=https;AccountName=..."
az ml online-deployment create --file deployment.yml --set environment_variables.AZURE_STORAGE_CONNECTION_STRING="${1:-}" --all-traffic

echo "배포 완료!"
echo "엔드포인트 상태 확인:"
az ml online-endpoint show -n $ENDPOINT_NAME
