from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import boto3
import json

router = APIRouter()

class BedrockModelRequest(BaseModel):
    prompt: str
    max_tokens_to_sample: Optional[int] = 300
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9

@router.get("/list-foundation-models")
async def list_foundation_models(region: Optional[str] = None):
    try:
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        bedrock_client = boto3.client('bedrock', region_name=region)
        response = bedrock_client.list_foundation_models()
        models = response['modelSummaries']
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invoke-model")
async def invoke_model(model_request: BedrockModelRequest, model_id: str, region: Optional[str] = None):
    try:
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=region)
        body = json.dumps({
            "prompt": model_request.prompt,
            "max_tokens_to_sample": model_request.max_tokens_to_sample,
            "temperature": model_request.temperature,
            "top_p": model_request.top_p
        })
        response = bedrock_runtime_client.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        return response_body
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
