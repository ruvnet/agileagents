from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import boto3

router = APIRouter()

class TimePeriod(BaseModel):
    Start: str
    End: str

class BudgetRequest(BaseModel):
    AccountId: str
    BudgetName: str

@router.post("/get-cost-and-usage")
async def get_cost_and_usage(time_period: TimePeriod, metrics: List[str] = ["UnblendedCost"], granularity: str = "MONTHLY"):
    try:
        client = boto3.client('ce')
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': time_period.Start,
                'End': time_period.End
            },
            Granularity=granularity,
            Metrics=metrics
        )
        return response['ResultsByTime']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/describe-budget")
async def describe_budget(budget_request: BudgetRequest):
    try:
        client = boto3.client('budgets')
        response = client.describe_budget(
            AccountId=budget_request.AccountId,
            BudgetName=budget_request.BudgetName
        )
        return response['Budget']['CalculatedSpend']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/describe-report-definitions")
async def describe_report_definitions():
    try:
        client = boto3.client('cur')
        response = client.describe_report_definitions()
        return response['ReportDefinitions']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get-products")
async def get_products(service_code: str, filters: List[dict]):
    try:
        client = boto3.client('pricing')
        response = client.get_products(
            ServiceCode=service_code,
            Filters=filters
        )
        return response['PriceList']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
