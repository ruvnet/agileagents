# base_models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class DeployRequest(BaseModel):
    repository_name: str
    image_tag: str
    python_script: str
    requirements: str
    function_name: str
    memory_size: Optional[int] = 128
    storage_size: Optional[int] = 512
    region: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None
    environment_variables: Optional[Dict[str, str]] = None 

class AdvancedDeployRequest(BaseModel):
    repository_name: str
    image_tag: str
    base_image: str
    build_commands: List[str]
    function_name: str
    region: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None


class VpcConfig(BaseModel):
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]

class FunctionConfig(BaseModel):
    repository_name: str
    image_tag: str
    function_name_prefix: str
    number_of_functions: int
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]
    region: Optional[str] = None
    log_retention_days: Optional[int] = 7

class SingleInvokeConfig(BaseModel):
    function_name: str
    payload: Dict[str, str] = Field(..., example={
        "OPENAI_API_KEY": "your-openai-api-key",
        "OTHER_ENV_VAR": "value",
        "name": "World"
    })
    region: Optional[str] = None

class MultipleInvokeConfig(BaseModel):
    function_name_prefix: str
    payload: Dict[str, str] = Field(..., example={
        "OPENAI_API_KEY": "your-openai-api-key",
        "OTHER_ENV_VAR": "value",
        "name": "World"
    })
    number_of_functions: int = Field(..., example=2)
    region: Optional[str] = None
    
class InvokeConfig(BaseModel):
    function_name_prefix: str
    payload: Dict[str, str] = Field(..., example={
        "OPENAI_API_KEY": "your-openai-api-key",
        "OTHER_ENV_VAR": "value",
        "name": "World"
    })
    number_of_functions: int = Field(..., example=2)
    region: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "function_name_prefix": "env-1",
                "payload": {
                    "OPENAI_API_KEY": "your-openai-api-key",
                    "OTHER_ENV_VAR": "value",
                    "name": "World"
                },
                "number_of_functions": 2,
                "region": "us-west-2"
            }
        }

class AccessKeyRequest(BaseModel):
    user_name: str

class BedrockModelRequest(BaseModel):
    prompt: str
    max_tokens_to_sample: Optional[int] = 300
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9

class TimePeriod(BaseModel):
    Start: str
    End: str

class BudgetRequest(BaseModel):
    AccountId: str
    BudgetName: str

class UpdateFunctionConfig(BaseModel):
    function_name: str
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    environment_variables: Optional[Dict] = None
    region: Optional[str] = None

class IAMUserRequest(BaseModel):
    user_name: str

class IAMRoleRequest(BaseModel):
    role_name: str
    assume_role_policy_document: Dict

class IAMPolicyRequest(BaseModel):
    policy_name: str
    policy_document: Dict

class AssumeRoleRequest(BaseModel):
    role_arn: str
    role_session_name: str

class AccessKeyRequest(BaseModel):
    user_name: str
