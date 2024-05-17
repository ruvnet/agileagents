from fastapi import APIRouter, HTTPException
import boto3

router = APIRouter()

@router.get("/regions")
async def list_regions():
    try:
        ec2_client = boto3.client('ec2')
        response = ec2_client.describe_regions()
        regions = response['Regions']
        region_names = [region['RegionName'] for region in regions]
        return {"regions": region_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
