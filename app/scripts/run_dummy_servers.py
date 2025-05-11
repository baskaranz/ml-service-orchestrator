import multiprocessing
from fastapi import FastAPI, Request
import uvicorn
import sys


def create_app(model_id: int):
    app = FastAPI()

    @app.post("/predict")
    async def predict(request: Request):
        data = await request.json()
        return {
            "result": f"dummy response from model {model_id}",
            "input": data,
            "model_id": f"dummy-model-{model_id}"
        }

    return app

def run_server(model_id: int, port: int):
    app = create_app(model_id)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")


def main():
    processes = []
    for i in range(1, 11):
        port = 8000 + i
        p = multiprocessing.Process(target=run_server, args=(i, port))
        p.start()
        processes.append(p)
        print(f"Started dummy model server {i} on port {port}")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("Shutting down dummy servers...")
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    main() 