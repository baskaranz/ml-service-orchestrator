"""
Unit tests for the create_dummy_models.py script.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from scripts.create_dummy_models import (
    DummyModelConfig,
    create_dummy_models,
    generate_orchestrator_config,
    write_model_config,
    write_model_registry,
)


class TestCreateDummyModels:
    """Tests for the create_dummy_models.py script."""

    def test_create_dummy_models(self):
        """Test creating dummy model configurations."""
        model_names = ["test_model1", "test_model2"]
        start_port = 9001
        
        model_configs = create_dummy_models(model_names, start_port)
        
        assert len(model_configs) == 2
        assert model_configs[0].model_id == "test_model1"
        assert model_configs[1].model_id == "test_model2"
        assert model_configs[0].port == 9001
        assert model_configs[1].port == 9002
        assert model_configs[0].version == "1.0.0"
        assert "test_model1" in model_configs[0].display_name
        assert isinstance(model_configs[0].latency_mean, float)
    
    def test_generate_orchestrator_config(self):
        """Test generating orchestrator configuration."""
        model_configs = [
            DummyModelConfig(
                model_id="test_model",
                version="1.0.0",
                display_name="Test Model",
                description="Test Description",
                port=9001,
                latency_mean=0.1,
                latency_stddev=0.05,
                error_rate=0.01,
                host="127.0.0.1"
            )
        ]
        
        config = generate_orchestrator_config(model_configs)
        
        assert "test_model" in config
        assert config["test_model"]["version"] == "1.0.0"
        assert config["test_model"]["endpoint"] == "http://127.0.0.1:9001/predict"
        assert config["test_model"]["timeout_ms"] == 250  # 0.1 + 3 * 0.05 * 1000
        assert config["test_model"]["max_retries"] == 3
        assert config["test_model"]["circuit_breaker"]["max_failures"] == 5
        assert config["test_model"]["circuit_breaker"]["reset_timeout_ms"] == 30000
        assert not config["test_model"]["auth"]["enabled"]
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory."""
        config_dir = tmp_path / "config" / "models"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def test_write_model_config(self, temp_config_dir, monkeypatch):
        """Test writing model configuration to file."""
        # Patch the CONFIG_DIR to use our temporary directory
        monkeypatch.setattr("scripts.create_dummy_models.CONFIG_DIR", temp_config_dir)
        
        model_id = "test_model"
        config = {"test_model": {"version": "1.0.0", "endpoint": "http://localhost:9001"}}
        
        config_path = write_model_config(model_id, config)
        
        assert os.path.exists(config_path)
        
        # Read the file and check its contents
        with open(config_path, "r") as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config == config
    
    def test_write_model_registry(self, temp_config_dir, monkeypatch, tmp_path):
        """Test writing model registry configuration."""
        # Patch the PROJECT_ROOT to use our temporary directory
        project_root = tmp_path
        monkeypatch.setattr("scripts.create_dummy_models.PROJECT_ROOT", project_root)
        
        # Create the config directory structure
        config_dir = project_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        models_config = {
            "test_model1": {"version": "1.0.0"},
            "test_model2": {"version": "1.0.0"}
        }
        
        registry_path = write_model_registry(models_config)
        
        assert os.path.exists(registry_path)
        
        # Read the file and check its contents
        with open(registry_path, "r") as f:
            registry = yaml.safe_load(f)
        
        assert "models" in registry
        assert "test_model1" in registry["models"]
        assert "test_model2" in registry["models"]
        assert registry["models"]["test_model1"]["config_file"] == "models/test_model1.yaml"
        assert registry["models"]["test_model1"]["enabled"] is True