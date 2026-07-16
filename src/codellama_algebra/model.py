"""Explicit, side-effect-free model configuration and loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BASE_MODEL_ID = "codellama/CodeLlama-7b-Instruct-hf"
BASE_MODEL_REVISION = "22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed"
ADAPTER_REPO_ID = "ADAPTER_REPO_ID"


class ModelDependencyError(RuntimeError):
    """Raised when optional model-loading dependencies are unavailable."""


class ModelDeviceError(RuntimeError):
    """Raised when the requested quantization/device combination is unavailable."""


@dataclass(frozen=True)
class QuantizationConfig:
    """Quantization settings for the base model."""

    enabled: bool = True
    quant_type: str = "nf4"
    double_quant: bool = True


@dataclass(frozen=True)
class ModelLoadConfig:
    """All model sources and load behavior; no checkpoint discovery is performed."""

    adapter_id_or_path: str | None = None
    base_model_id: str = BASE_MODEL_ID
    base_model_revision: str = BASE_MODEL_REVISION
    quantization: QuantizationConfig = QuantizationConfig()
    device_map: str | dict[str, int | str] = "auto"
    attention_implementation: str = "sdpa"
    local_files_only: bool = False
    seed: int = 42

    def __post_init__(self) -> None:
        if self.adapter_id_or_path == ADAPTER_REPO_ID:
            raise ValueError("Provide an explicit local adapter path or confirmed Hugging Face ID.")
        if not self.base_model_id:
            raise ValueError("base_model_id must be explicit and nonempty.")
        if not self.base_model_revision:
            raise ValueError("base_model_revision must be explicit and nonempty.")


@dataclass(frozen=True)
class ModelMetadata:
    """Sources and effective load settings for a loaded model."""

    base_model_id: str
    base_model_revision: str
    adapter_id_or_path: str | None
    quantized_4bit: bool
    quant_type: str | None
    dtype: str
    device_map: str
    deterministic_seed: int
    local_files_only: bool


@dataclass
class LoadedModel:
    """Tokenizer/model pair returned by :func:`load_model`."""

    tokenizer: Any
    model: Any
    metadata: ModelMetadata


def _dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise ModelDependencyError(
            "Model loading requires torch, transformers, peft, accelerate, and safetensors. "
            "Install a platform-appropriate PyTorch build separately when CUDA is required."
        ) from exc
    return torch, PeftModel, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def _select_dtype(torch: Any) -> Any:
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def load_model(config: ModelLoadConfig) -> LoadedModel:
    """Load one explicitly named base model and adapter without generating text."""

    torch, peft_model, auto_model, auto_tokenizer, bnb_config = _dependencies()
    if config.quantization.enabled and not torch.cuda.is_available():
        raise ModelDeviceError(
            "4-bit BitsAndBytes loading requires a compatible CUDA environment in this project. "
            "Disable quantization explicitly for CPU loading."
        )

    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    dtype = _select_dtype(torch)
    common = {
        "device_map": config.device_map,
        "attn_implementation": config.attention_implementation,
        "local_files_only": config.local_files_only,
    }
    if config.quantization.enabled:
        quantization = bnb_config(
            load_in_4bit=True,
            bnb_4bit_quant_type=config.quantization.quant_type,
            bnb_4bit_use_double_quant=config.quantization.double_quant,
            bnb_4bit_compute_dtype=torch.bfloat16 if dtype == torch.bfloat16 else torch.float16,
        )
        common["quantization_config"] = quantization
    else:
        common["torch_dtype"] = dtype

    try:
        tokenizer = auto_tokenizer.from_pretrained(
            config.base_model_id,
            revision=config.base_model_revision,
            use_fast=True,
            local_files_only=config.local_files_only,
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left"
        base = auto_model.from_pretrained(
            config.base_model_id,
            revision=config.base_model_revision,
            **common,
        )
        model = base
        if config.adapter_id_or_path is not None:
            model = peft_model.from_pretrained(
                base,
                config.adapter_id_or_path,
                local_files_only=config.local_files_only,
            )
    except OSError as exc:
        raise RuntimeError(
            "Model or adapter loading failed. Verify the explicit identifiers, local files, "
            "credentials, network policy, and base-model license access."
        ) from exc

    model.eval()
    metadata = ModelMetadata(
        base_model_id=config.base_model_id,
        base_model_revision=config.base_model_revision,
        adapter_id_or_path=config.adapter_id_or_path,
        quantized_4bit=config.quantization.enabled,
        quant_type=config.quantization.quant_type if config.quantization.enabled else None,
        dtype=str(dtype),
        device_map=str(config.device_map),
        deterministic_seed=config.seed,
        local_files_only=config.local_files_only,
    )
    return LoadedModel(tokenizer=tokenizer, model=model, metadata=metadata)
