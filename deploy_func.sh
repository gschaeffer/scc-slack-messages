#!/bin/bash

# SCC Notifications resources must already be setup (e.g. Topic).

NAME=scc_slack_handler
ENTRY_POINT=scc_slack_handler
LABELS="app=scc_slack_alerts"
MEMORY=256MB
REGION=us-central1
SOURCE_DIR="app/"
TOPIC="scc-notifications"

gcloud functions deploy $NAME \
    --entry-point $ENTRY_POINT \
    --memory $MEMORY \
    --region $REGION \
    --runtime python38 \
    --set-env-vars "project_id=PROJECT_ID" \
    --source $SOURCE_DIR \
    --trigger-topic $TOPIC \
    --update-labels $LABELS \
    --retry 
    