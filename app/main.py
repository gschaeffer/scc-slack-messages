import json
import os
import requests
# import pprint

from google.cloud import logging
from google.cloud import secretmanager


def message_post(data):
    # pprint.pprint(payload)
    token = get_secret("slack-handler-token")
    channel_id = get_secret("slack-handler-channel")
    payload = data if type(data) is dict else json.loads(data)

    url = 'https://slack.com/api/chat.postMessage'
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json; charset=utf-8'
    }
    try:
        with open("block_templates/finding-detail.json", "rt") as block_f:
            block_template = json.load(block_f)
        # template_content
        merge_template(block_template, payload)

        params = {
            "channel": channel_id,
            "blocks": block_template,
            "text": "Alternate content from block content",
            "unfurl_links": "false"
        }
        r = requests.post(url, data=json.dumps(params), headers=headers)
        if r.status_code != 200:
            raise ValueError(f"Request to Slack returned error \
                {r.status_code}. Response is: {r.text}")
        # print(r.text)

    except Exception as e:
        print(f"Error occurred attempting to post message. Error is: {e}")


def merge_template(list_data, payload):
    finding = payload.get("finding")
    resource = payload.get("resource")
    props = finding.get("sourceProperties")

    org_id = finding.get("name").split("/")[1]
    finding_id = finding.get("name").split("/")[-1]
    source_id = finding.get("name").split("/")[3]
    severity = finding.get("severity")
    sev_emo = ":warning:" if "HIGH" in severity else ""

    url = "https://console.cloud.google.com/security/command-center/findings"
    url += f"?organizations/{org_id}/sources/{source_id}/"
    url += f"findings/{finding_id}=,true&orgonly=true"
    url += f"&organizationId={org_id}&supportedpurview=organizationId"
    url += "&view_type=vt_finding_type&vt_finding_type=All"
    url += f"&resourceId=organizations/{org_id}/sources/{source_id}/"
    url += f"findings/{finding_id}"
    # pprint.pprint(url)

    list_data[0]["text"]["text"] = list_data[0]["text"]["text"] \
        .replace("<SUBJECT>", finding.get("category")) \
        .replace("<WEB_LINK>", url)

    list_data[1]["text"]["text"] = list_data[1]["text"]["text"] \
        .replace("<PROJECT_ID>", str(resource.get("projectDisplayName"))) \
        .replace("<SEVERITY>", severity) \
        .replace("<SEV_EMO>", sev_emo) \
        .replace("<STATE>", finding.get("state")) \
        .replace("<TIMESTAMP>", finding.get("createTime"))

    list_data[1]["accessory"]["url"] = list_data[1]["accessory"]["url"] \
        .replace("<WEB_LINK>", url)

    explain = format_text(json.dumps(props.get("Explanation")), False)
    list_data[2]["text"]["text"] = list_data[2]["text"]["text"] \
        .replace("<EXPLANATION>", explain)

    recommend = format_text(json.dumps(props.get("Recommendation")), False)
    list_data[3]["text"]["text"] = list_data[3]["text"]["text"] \
        .replace("<RECOMMENDATION>", recommend)

    # instruct = format_text(json.dumps())
    instr = format_text(json.dumps(props.get("ExceptionInstructions")), True)
    list_data[4]["text"]["text"] = list_data[4]["text"]["text"] \
        .replace("<INSTRUCT>", instr)


def format_text(val, text2CodeBlocks: bool = False):
    val = val.replace("\\", "")
    val = val[1:] if val.startswith('"') else val
    val = val[:-1] if val.endswith('"') else val
    if text2CodeBlocks is True:
        val = val.replace('"', '`')
    return val


def get_secret(secret_id, version_id="latest"):
    gcp_project = get_project()
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{gcp_project}/secrets/{secret_id}/versions/{version_id}"
    return client.access_secret_version(name=name).payload.data.decode("utf-8")


def get_project():
    return os.environ.get('project_id', 'project_id env var not set.')


def scc_slack_handler(event, context):
    """Cloud Function to be triggered by PubSub subscription.
       This function receives messages containing SCC Findings data.
       It creates a log entry within the project allowing Cloud
       Monitoring to be used for alerting on the SCC findings.

    Args:
        event (dict): The PubSub message payload.
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Cloud Logging.
    """
    import base64

    CUSTOM_LOG_NAME = "scc_notifications_log"
    logging_client = logging.Client()
    logger = logging_client.logger(CUSTOM_LOG_NAME)
    # logger = logging_client.logger()

    try:
        # PubSub messages come in encrypted
        payload = base64.b64decode(event['data']).decode('utf-8')
        message_post(payload)
    except Exception as e:
        logger.log(f"Oops! {e}")


if __name__ == "__main__":
    with open("app/payload_test.json", "rt") as testdata_f:
        testdata = json.load(testdata_f)
    message_post(testdata)
