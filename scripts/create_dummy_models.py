#!/usr/bin/env python3
"""
ML Orchestrator Dummy Model API Creator

This script creates mock/dummy model API endpoints that can be attached to the ML Orchestrator 
for development and testing purposes. Each model API follows a consistent pattern but can be 
customized with different behaviors, latencies, and response structures.

Usage:
  python create_dummy_models.py --model-name apple_model orange_model --port 8001 8002
  
You can also run it without arguments to use the default settings:
  python create_dummy_models.py
"""

import argparse
import asyncio
import json
import logging
import os
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dummy_model_api")

# Project root directory
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Config directory for model configurations
CONFIG_DIR = PROJECT_ROOT / "config" / "models"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Model API definitions

class ModelInput(BaseModel):
    """Base model input class. Can be customized per model."""
    inputs: Any = Field(..., description="Model inputs (any format supported)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters")


class ModelOutput(BaseModel):
    """Base model output class. Can be customized per model."""
    outputs: Any = Field(..., description="Model outputs")
    model_id: str = Field(..., description="ID of the model that processed the request")
    request_id: str = Field(..., description="Unique request ID")
    processing_time: float = Field(..., description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DummyModelConfig(BaseModel):
    """Configuration for a dummy model API."""
    model_id: str = Field(..., description="Unique model identifier")
    version: str = Field(..., description="Model version")
    display_name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    input_type: str = Field("json", description="Input type (json, text, image, etc.)")
    output_type: str = Field("json", description="Output type (json, text, etc.)")
    latency_mean: float = Field(0.1, description="Mean latency in seconds")
    latency_stddev: float = Field(0.05, description="Standard deviation of latency")
    error_rate: float = Field(0.0, description="Probability of returning an error")
    port: int = Field(..., description="Port to run the API on")
    host: str = Field("127.0.0.1", description="Host to run the API on")


def create_model_app(config: DummyModelConfig) -> FastAPI:
    """Create a FastAPI application for a dummy model."""
    app = FastAPI(
        title=f"{config.display_name} API",
        description=f"Dummy API for {config.model_id} ({config.description})",
        version=config.version
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Latency simulation middleware
    @app.middleware("http")
    async def add_simulated_latency(request: Request, call_next):
        # Simulate processing time
        latency = random.normalvariate(config.latency_mean, config.latency_stddev)
        latency = max(0.01, latency)  # Ensure positive latency
        
        # Store for later use
        request.state.latency = latency
        request.state.start_time = time.time()
        
        # Sleep to simulate processing
        await asyncio.sleep(latency)
        
        return await call_next(request)
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "model_id": config.model_id, "version": config.version}
    
    @app.get("/info")
    async def info():
        """Model information endpoint."""
        return {
            "model_id": config.model_id,
            "version": config.version,
            "display_name": config.display_name,
            "description": config.description,
            "input_type": config.input_type,
            "output_type": config.output_type,
        }
    
    @app.post("/predict", response_model=ModelOutput, status_code=status.HTTP_200_OK)
    async def predict(request: Request, data: ModelInput):
        """
        Main prediction endpoint.
        
        Returns a simulated response based on the model configuration.
        Randomly generates an error based on the error_rate.
        """
        # Extract request information
        request_id = request.state.request_id
        latency = request.state.latency
        
        # Randomly generate an error based on error_rate
        if random.random() < config.error_rate:
            error_types = [
                ("Internal Server Error", status.HTTP_500_INTERNAL_SERVER_ERROR),
                ("Bad Gateway", status.HTTP_502_BAD_GATEWAY),
                ("Service Unavailable", status.HTTP_503_SERVICE_UNAVAILABLE),
                ("Gateway Timeout", status.HTTP_504_GATEWAY_TIMEOUT)
            ]
            error, status_code = random.choice(error_types)
            raise HTTPException(status_code=status_code, detail=f"Simulated error: {error}")
        
        # Generate dummy output based on input format
        if isinstance(data.inputs, dict):
            # For dictionary inputs, echo back with some modifications
            outputs = {k: f"processed_{v}" if isinstance(v, str) else v * 2 for k, v in data.inputs.items()}
        elif isinstance(data.inputs, list):
            # For list inputs, transform each item
            outputs = [f"processed_{item}" if isinstance(item, str) else item * 2 for item in data.inputs]
        elif isinstance(data.inputs, str):
            # For string inputs, echo back with model identifier
            outputs = f"[{config.model_id}] Processed: {data.inputs}"
        else:
            # For other inputs, return a dummy response
            outputs = {"result": f"Processed by {config.model_id}", "confidence": random.random()}
        
        # Create response
        return ModelOutput(
            outputs=outputs,
            model_id=config.model_id,
            request_id=request_id,
            processing_time=latency,
            metadata={
                "version": config.version,
                "timestamp": time.time(),
                "parameters": data.parameters
            }
        )
    
    # Register error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "model_id": config.model_id,
                "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception in {config.model_id}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": f"Internal server error: {str(exc)}",
                "model_id": config.model_id,
                "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
                "status_code": 500
            }
        )
    
    return app


def generate_orchestrator_config(model_configs: List[DummyModelConfig]) -> Dict[str, Any]:
    """Generate ML Orchestrator configuration for the dummy models."""
    models_config = {}
    
    for config in model_configs:
        models_config[config.model_id] = {
            "version": config.version,
            "endpoint": f"http://{config.host}:{config.port}/predict",
            "timeout_ms": int((config.latency_mean + 3 * config.latency_stddev) * 1000),
            "max_retries": 3,
            "circuit_breaker": {
                "max_failures": 5,
                "reset_timeout_ms": 30000
            },
            "auth": {
                "enabled": False
            }
        }
    
    return models_config


def write_model_config(model_id: str, config: Dict[str, Any]):
    """Write model configuration to a YAML file."""
    config_path = CONFIG_DIR / f"{model_id}.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    logger.info(f"Created configuration file: {config_path}")
    return config_path


def write_model_registry(models_config: Dict[str, Any]):
    """Write model registry configuration."""
    registry_path = PROJECT_ROOT / "config" / "models" / "registry.yaml"
    
    # Create a registry entry for each model
    registry_config = {
        "version": "1.0.0",
        "name": "Model Registry",
        "description": "Registry of model configurations",
        "models": {}
    }
    for model_id, config in models_config.items():
        registry_config["models"][model_id] = {
            "id": model_id,
            "name": f"Model {model_id}",
            "description": f"Configuration for {model_id}",
            "version": config["version"],
            "endpoint": config["endpoint"],
            "config_file": f"models/{model_id}.yaml",
            "enabled": True
        }
    
    # Ensure directory exists
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(registry_path, "w") as f:
        yaml.dump(registry_config, f, default_flow_style=False)
    
    logger.info(f"Created registry file: {registry_path}")
    return registry_path


def generate_startup_script(model_configs: List[DummyModelConfig]):
    """Generate a startup script for all dummy models."""
    script_path = PROJECT_ROOT / "scripts" / "start_dummy_models.sh"
    
    script_content = "#!/bin/bash\n\n"
    script_content += "# Start dummy model APIs\n"
    script_content += "# This script is auto-generated by create_dummy_models.py\n\n"
    
    # Add startup commands for each model
    for i, config in enumerate(model_configs):
        script_content += f"# Start {config.model_id}\n"
        script_content += f"python -m scripts.create_dummy_models --run-server --model-index {i} &\n"
        script_content += f"echo \"Started {config.model_id} on port {config.port}\"\n\n"
    
    script_content += "# Wait for any key to terminate all processes\n"
    script_content += "read -p \"Press any key to terminate all dummy models...\"\n\n"
    script_content += "# Kill all background processes\n"
    script_content += "kill $(jobs -p)\n"
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    logger.info(f"Created startup script: {script_path}")
    return script_path


def save_model_configs(model_configs: List[DummyModelConfig]):
    """Save model configurations to a JSON file for later use."""
    config_path = PROJECT_ROOT / "config" / "dummy_models.json"
    
    # Convert to dictionaries
    configs_dict = [config.dict() for config in model_configs]
    
    with open(config_path, "w") as f:
        json.dump(configs_dict, f, indent=2)
    
    logger.info(f"Saved model configurations to: {config_path}")
    return config_path


def load_model_configs() -> List[DummyModelConfig]:
    """Load model configurations from a JSON file."""
    config_path = PROJECT_ROOT / "config" / "dummy_models.json"
    
    if not config_path.exists():
        logger.error(f"Model configuration file not found: {config_path}")
        return []
    
    with open(config_path, "r") as f:
        configs_dict = json.load(f)
    
    model_configs = [DummyModelConfig(**config) for config in configs_dict]
    logger.info(f"Loaded {len(model_configs)} model configurations from: {config_path}")
    return model_configs


def create_dummy_models(model_names: List[str], start_port: int = 8001) -> List[DummyModelConfig]:
    """Create dummy model configurations."""
    model_configs = []
    
    for i, model_name in enumerate(model_names):
        # Create a configuration for this model with varying characteristics
        config = DummyModelConfig(
            model_id=model_name,
            version=f"1.{i}.0",  # Different versions for each model
            display_name=f"Model {i+1}",  # More generic display name
            description=f"Dummy model API for {model_name} with varying characteristics",
            port=start_port + i,
            host="127.0.0.1",  # Default host
            latency_mean=random.uniform(0.05, 0.3),  # Random latency between 50-300ms
            latency_stddev=random.uniform(0.01, 0.1),  # Random jitter
            error_rate=random.uniform(0, 0.05),  # 0-5% error rate
            input_type="json",
            output_type="json"
        )
        model_configs.append(config)
    
    return model_configs


def run_server(model_configs: List[DummyModelConfig], model_index: int):
    """Run a specific model server."""
    if model_index >= len(model_configs):
        logger.error(f"Invalid model index: {model_index}. Only {len(model_configs)} models available.")
        return
    
    config = model_configs[model_index]
    logger.info(f"Starting {config.model_id} on port {config.port}...")
    
    app = create_model_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create and run dummy model APIs for ML Orchestrator")
    parser.add_argument("--model-name", nargs="+", default=["model_1", "model_2", "model_3", "model_4", "model_5"],
                        help="Names of the dummy models to create")
    parser.add_argument("--port", type=int, nargs="+", help="Ports for the model APIs (must match number of models)")
    parser.add_argument("--run-server", action="store_true", help="Run a model server")
    parser.add_argument("--model-index", type=int, default=0, help="Index of the model to run (with --run-server)")
    parser.add_argument("--num-models", type=int, help="Number of models to create (overrides --model-name)")
    
    args = parser.parse_args()
    
    # If num_models is specified, generate that many model names
    if args.num_models:
        args.model_name = [f"model_{i+1}" for i in range(args.num_models)]
    
    # Check if port list matches model list
    if args.port and len(args.port) != len(args.model_name):
        logger.error("Number of ports must match number of models")
        return 1
    
    # If we're just running a server, load existing configs
    if args.run_server:
        model_configs = load_model_configs()
        if not model_configs:
            logger.error("No model configurations found. Create models first.")
            return 1
        
        run_server(model_configs, args.model_index)
        return 0
    
    # Create dummy model configurations
    model_configs = create_dummy_models(
        args.model_name,
        start_port=args.port[0] if args.port else 8001
    )
    
    # If ports were provided, update the configs
    if args.port:
        for i, port in enumerate(args.port):
            model_configs[i].port = port
    
    # Save model configurations for later use
    save_model_configs(model_configs)
    
    # Generate orchestrator configuration
    models_config = generate_orchestrator_config(model_configs)
    
    # Write individual model configs
    for model_id, config in models_config.items():
        write_model_config(model_id, {model_id: config})
    
    # Write model registry
    write_model_registry(models_config)
    
    # Generate startup script
    startup_script = generate_startup_script(model_configs)
    
    logger.info(f"Created {len(model_configs)} dummy model configurations")
    logger.info(f"Run all dummy models with: {startup_script}")
    
    # Print summary
    print("\nDummy Model APIs created:")
    for config in model_configs:
        print(f"  - {config.model_id}: http://{config.host}:{config.port}")
        print(f"    Version: {config.version}")
        print(f"    Latency: {config.latency_mean:.3f}s ± {config.latency_stddev:.3f}s")
        print(f"    Error Rate: {config.error_rate:.1%}")
    
    print("\nTo start all dummy models:")
    print(f"  bash {startup_script}")
    
    print("\nTo use with ML Orchestrator:")
    print("  1. Make sure the orchestrator is configured to use the model registry")
    print("  2. Start the dummy models")
    print("  3. Start the orchestrator with hot-reloading enabled")
    
    return 0


if __name__ == "__main__":
    exit(main())