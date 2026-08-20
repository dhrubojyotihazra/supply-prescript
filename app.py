import gradio as gr
from api.main import app as fastapi_app

# Gradio Interface for Hugging Face container health checks
demo = gr.Interface(
    fn=lambda prompt: "SupplyPrescript API Backend is Online!",
    inputs="text",
    outputs="text",
    title="SupplyPrescript API",
    description="Closed-Loop Prescriptive Analytics Engine"
)

# Mount FastAPI onto Gradio app so all REST API endpoints (/warehouses, /predict, /prescribe, etc.) work 24/7
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
