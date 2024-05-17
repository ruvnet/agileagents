from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles  # Import StaticFiles to serve static files
from routers import costs_router, iam_router, management_router, misc_router, bedrock_router
from deployment.aws.deploy import deploy_router

# Create an instance of the FastAPI application with custom metadata
app = FastAPI(
    title="Agile Agents",  # Set the title for the Swagger UI
    description="This is the Agile Agents API documentation.",  # Set the description for the Swagger UI
    version="0.1.0",  # Set the version of the API
    contact={
        "name": "Support Team",  # Contact name
        "url": "https://github.com/ruvnet/agileagents",  # Contact URL
        "email": "support@agileagents.ai",  # Contact email
    },
    license_info={
        "name": "MIT License",  # License name
        "url": "https://opensource.org/licenses/MIT",  # License URL
    },
    openapi_url="/api/v1/openapi.json",  # Custom OpenAPI documentation path
    docs_url=None,  # Disable the default Swagger UI
    redoc_url=None,  # Disable the default ReDoc UI
)

# Redirect the root URL to the custom Swagger UI documentation
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/documentation")

# Custom Swagger UI endpoint with additional parameters
@app.get("/documentation", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,  # URL for the OpenAPI spec
        title="Agile Agents Documentation",  # Title for the Swagger UI
        # swagger_css_url="/static/custom-swagger-ui.css",  # Uncomment to use custom CSS
        swagger_ui_parameters={"defaultModelsExpandDepth": -1}  # Collapse models by default
    )

# Include the routers for different parts of the application with tags
app.include_router(costs_router, prefix="/costs", tags=["Costs"])  # Router for cost-related endpoints
app.include_router(iam_router, prefix="/iam", tags=["IAM"])  # Router for IAM-related endpoints
app.include_router(management_router, prefix="/management", tags=["Management"])  # Router for management-related endpoints
app.include_router(misc_router, prefix="/misc", tags=["Misc"])  # Router for miscellaneous endpoints
app.include_router(bedrock_router, prefix="/bedrock", tags=["Bedrock"])  # Router for Bedrock-related endpoints
app.include_router(deploy_router, prefix="/deployment", tags=["Deployment"])  # Router for deployment-related endpoints

# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Run the application with Uvicorn if this script is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
