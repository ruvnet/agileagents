from pydantic import BaseModel
from typing import Optional, List

class DeployRequest(BaseModel):
    repository_name: str
    image_tag: str
    python_script: str
    requirements: str
    function_name: str
    region: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None

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

class InvokeConfig(BaseModel):
    function_name_prefix: str
    number_of_functions: int
    payload: dict
    region: Optional[str] = None

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
    environment_variables: Optional[dict] = None
    region: Optional[str] = None

class BedrockModelRequest(BaseModel):
    prompt: str
    max_tokens_to_sample: Optional[int] = 300
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9

class IAMUserRequest(BaseModel):
    user_name: str

class IAMRoleRequest(BaseModel):
    role_name: str
    assume_role_policy_document: dict

class IAMPolicyRequest(BaseModel):
    policy_name: str
    policy_document: dict

class AssumeRoleRequest(BaseModel):
    role_arn: str
    role_session_name: str

class AccessKeyRequest(BaseModel):
    user_name: str
