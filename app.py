from fastapi import FastAPI
from routers import costs_router, iam_router, management_router, misc_router, bedrock_router
from deployment.aws.deploy import deploy_router  # Correctly import deploy_router

app = FastAPI()

app.include_router(costs_router, prefix="/costs", tags=["Costs"])
app.include_router(iam_router, prefix="/iam", tags=["IAM"])
app.include_router(management_router, prefix="/management", tags=["Management"])
app.include_router(misc_router, prefix="/misc", tags=["Misc"])
app.include_router(bedrock_router, prefix="/bedrock", tags=["Bedrock"])
app.include_router(deploy_router, prefix="/deployment", tags=["Deployment"])  # Add the deployment router

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
