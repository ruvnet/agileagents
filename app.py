#          ____ ___       
#  _______|    |   ___  __
#  \_  __ |    |   \  \/ /
#   |  | \|    |  / \   / 
#   |__|  |______/   \_/  
#                         
#     Agile Agents API
#     Version: 0.1.0
#     Created by rUv
# /app.py

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from routers.costs_router import router as costs_router
from routers.iam_router import router as iam_router
from routers.misc_router import router as misc_router
from routers.bedrock_router import router as bedrock_router
from routers.management_router import management_router
from routers.users import router as users_router   
from deployment.aws.deploy import deploy_router
import subprocess

app = FastAPI(
    title="Agile Agents",
    description="This is the Agile Agents API documentation.",
    version="0.1.0",
    contact={
        "name": "Support Team",
        "url": "https://github.com/ruvnet/agileagents",
        "email": "support@agileagents.ai",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_url="/api/v1/openapi.json",
    docs_url=None,
    redoc_url=None,
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/documentation")

@app.get("/documentation", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Agile Agents Documentation",
        swagger_ui_parameters={"defaultModelsExpandDepth": -1}
    )

app.include_router(costs_router, prefix="/costs", tags=["Costs"])
app.include_router(iam_router, prefix="/iam", tags=["IAM"])
app.include_router(management_router, prefix="/management", tags=["Management"])
app.include_router(misc_router, prefix="/misc", tags=["Misc"])
app.include_router(bedrock_router, prefix="/bedrock", tags=["Bedrock"])
app.include_router(deploy_router, prefix="/deployment", tags=["Deployment"])
app.include_router(users_router, prefix="/users", tags=["Users"])  # Include the users router

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Start Gradio app in a separate process
    subprocess.Popen(["python", "./frontend/gradio_ui.py"])
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
